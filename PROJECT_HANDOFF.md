# 全网找‘屎’专家 - Project Handoff (2026-04-04)

Internal Python module compatibility name remains `douyin_agent`.

## 1) Current status
- Project is in **usable** state for real-site scan/share workflow.
- Main runner: `examples/run_real_site_once.py` (`--mode scan`).
- Browser adapter: `src/douyin_agent/browser_playwright.py`.
- Runtime GUI log window is enabled by default (disable only with `--no-log-window`).

## 2) What this project currently does
For each feed item, in scan mode:
1. Detects live-vs-non-live.
2. Reads right-rail engagement metrics (like/share).
3. Applies share gating rules.
4. Only if share candidate: opens comment panel, runs AI profile analysis + AI comment generation.
5. If share candidate passes and share is enabled: shares to target group/user, optionally with AI message.
6. Writes runtime log window line (CSV output is disabled by policy).

## 3) Active business rules (IMPORTANT)

### 3.1 Ad rule
- **Only** `author-area ad badge` (`广告`) means ad.
- Share/comment decision uses `ad_badge` as a hard block.
- Current share detail for ad skip: `ad_badge=True;rule=author_badge_only`.
- Additional safety fallback:
  - if text or AI profile shows clear promo / commerce signals, skip with `share_result=skip_promo`

### 3.1.1 Live hard rule
- Live content is a hard block:
  - do **not** comment
  - do **not** mention friends
  - do **not** share
- Hard block follows the original live decision path already used in scan mode.
- Code:
  - `src/douyin_agent/browser_playwright.py` -> `has_ad_badge` (lower-left author metadata region)
  - `src/douyin_agent/promo_filter.py`
  - `examples/run_real_site_once.py` around share decision (`elif ad_badge:`)

### 3.2 Share rule
- Engagement decision is now configurable via `configs/share_rules.toml`.
- Default rule:
  - If `like_count < 1000` => **never share**
  - Else share when: `share_count > 200000` OR `(share_count / like_count) > 0.5`
- CLI overrides:
  - `--share-min-like-count`
  - `--share-min-share-count`
  - `--share-min-share-like-ratio`
  - `--share-threshold-mode`
- Code:
  - `src/douyin_agent/share_rules.py`
  - `examples/run_real_site_once.py` -> `_should_share_by_engagement`

### 3.3 AI trigger rule
- Non-live videos that do **not** pass share gating:
  - do **not** open comment panel
  - do **not** run AI analyze/generate
- Only share candidates go through comment-panel + AI path.
- Code: `examples/run_real_site_once.py` around
  - `if short_video_confirmed and should_share and comment_by_content:`

## 4) Key implementation points

### 4.1 Runtime log window
- Implemented as separate Tk child process (not main-thread Tk), avoids startup blocking on macOS.
- Code: `RuntimeLogWindow` class in `examples/run_real_site_once.py`.

### 4.2 Engagement extraction
- Right-rail metric extractor dedups duplicated DOM wrappers by vertical row.
- Parsing supports duplicated sequences (`a,a,b,b,c,c,d,d`) and picks robust candidate.
- Mapping rule remains user-confirmed:
  - 1st number = like
  - 4th number = share
- Code:
  - `src/douyin_agent/browser_playwright.py` -> `get_right_action_metric_texts`
  - `examples/run_real_site_once.py` -> `_extract_ranked_engagement_counts`

### 4.3 Playwright reconnect fix
- Fixed a crash case: sync_playwright nested-loop error during session re-init.
- `_ensure_started()` now closes stale handles before re-starting Playwright.
- Code: `src/douyin_agent/browser_playwright.py` -> `_ensure_started`

## 5) Run commands (copy-paste)

## 5.1 Standard real-site scan (100 rounds)
```bash
cd /Users/elewave/Desktop/CLI_Folder/quanwang_zhao_shi_zhuanjia
OPENAI_API_KEY='<YOUR_KEY>' PYTHONUNBUFFERED=1 python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 100 \
  --require-login \
  --login-timeout 120 \
  --profile-dir .playwright_profile_main \
  --wait-scale 1.6 \
  --live-wait-seconds 3 \
  --video-wait-seconds 10 \
  --post-next-settle-seconds 8 \
  --snapshot-settle-seconds 2 \
  --comment-by-content \
  --use-ai-comment \
  --comment-style humorous \
  --llm-api-base https://api.deepseek.com/v1 \
  --llm-model deepseek-chat \
  --llm-api-key-env OPENAI_API_KEY \
  --llm-insecure-skip-verify \
  --enable-share \
  --share-target '3214抖音群'
```

## 5.2 Long smoke (1000 rounds)
```bash
cd /Users/elewave/Desktop/CLI_Folder/quanwang_zhao_shi_zhuanjia
OPENAI_API_KEY='<YOUR_KEY>' PYTHONUNBUFFERED=1 python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 1000 \
  --require-login \
  --login-timeout 120 \
  --profile-dir .playwright_profile_main \
  --wait-scale 1.6 \
  --live-wait-seconds 3 \
  --video-wait-seconds 10 \
  --post-next-settle-seconds 8 \
  --snapshot-settle-seconds 2 \
  --comment-by-content \
  --use-ai-comment \
  --comment-style humorous \
  --llm-api-base https://api.deepseek.com/v1 \
  --llm-model deepseek-chat \
  --llm-api-key-env OPENAI_API_KEY \
  --llm-insecure-skip-verify \
  --enable-share \
  --share-target '3214抖音群'
```

## 6) Where to edit when requirements change
- Share threshold / floor:
  - `configs/share_rules.toml`
  - `src/douyin_agent/share_rules.py`
  - `examples/run_real_site_once.py` -> `_should_share_by_engagement`
- Ad filtering:
  - `src/douyin_agent/browser_playwright.py` -> `has_ad_badge`
  - `examples/run_real_site_once.py` -> share-decision branch (`elif ad_badge:`)
- "Only share-candidate runs AI" behavior:
  - `examples/run_real_site_once.py` around `if short_video_confirmed and should_share and comment_by_content:`
- Right-rail metric extraction:
  - `src/douyin_agent/browser_playwright.py` -> `get_right_action_metric_texts`
  - `examples/run_real_site_once.py` -> `_extract_ranked_engagement_counts`
- Runtime log format:
  - `examples/run_real_site_once.py` -> `_emit_runtime_round_log`

## 7) Known caveats
- Scan loop may appear "stuck" during long waits or slow UI rendering; verify progress from runtime log window / terminal logs.
- `--scan-report-csv` is deprecated and ignored (no file will be created).
- `--llm-insecure-skip-verify` is currently used by default in operations due to observed TLS environment issues.
- `_detect_ad_video(...)` function still exists but is no longer the active share gate (active gate is `ad_badge` branch).

## 8) Quick health checks

### 8.0 M3 regression acceptance

Run the complete offline suite from the repository root:

```bash
python3 -m pytest -q
```

This must pass before handing off a change. The suite is intentionally side-effect free: it does not open a real browser, call an LLM, post comments, or share content. It protects the critical safety contracts below:

- Live and author-area ad-badge content are hard-blocked before comment, mention, or share actions.
- Promo detections and failed engagement thresholds surface an explicit `share_result` and reason in runtime logs.
- Default GUI command generation omits `--enable-share` and `--enable-post`; real side effects require explicit opt-in.
- Share thresholds remain configurable through `configs/share_rules.toml` and documented CLI overrides.
- README and this handoff retain the user-facing safe-default and offline-test guidance.

### 8.1 Is run still progressing?
- Check runtime log window keeps appending new rounds.
- Check terminal keeps printing `[round N]` and `[next]`.

### 8.2 Verify current rules from logs
- `like < 1000` should not be shared.
- non-share-candidate rounds should show:
  - `pressed_x=False`
  - `comment_result=skip_not_share_candidate`


## 10) New conversation bootstrap
When opening a new Codex conversation, first say:

```text
请先读取 /Users/elewave/Desktop/CLI_Folder/quanwang_zhao_shi_zhuanjia/PROJECT_HANDOFF.md，
按其中“Active business rules”执行，不要改动规则，先跑 10 轮真站回归并汇报关键日志结果。
```
