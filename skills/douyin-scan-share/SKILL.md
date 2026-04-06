---
name: douyin-scan-share
description: Use this skill when the user wants to run, validate, or hand off “全网找‘屎’专家” in scan/share mode with safe defaults, including login bootstrap, regression rounds, and optional share enablement.
---

# 全网找‘屎’专家 Skill

## When To Use

Use this skill when the user asks to:
- run real-site scan loops for this project
- hand off the project with stable run commands
- enable or disable share behavior safely
- troubleshoot scan-mode execution without changing business rules

Project root expected:
- `/Users/elewave/Desktop/CLI_Folder/douyin_computer_use_poc`

If root differs, detect it first and adapt all commands.

## Required Context

Before execution, read:
- `PROJECT_HANDOFF.md`
- `README.md`

Follow the active business rules in `PROJECT_HANDOFF.md` unless user explicitly requests rule changes.

## Standard Workflow

1. Environment checks
- Confirm Python >= 3.11.
- Confirm Playwright chromium is installed.
- Confirm API key env exists when AI comment is enabled.

2. Login bootstrap (first run or expired profile)
```bash
python3 examples/run_real_site_once.py --login-only --require-login --login-timeout 180 --profile-dir .playwright_profile_main
```

3. Safe regression run (no share)
```bash
OPENAI_API_KEY='<YOUR_KEY>' python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 10 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --wait-scale 1.6 \
  --live-wait-seconds 3 \
  --video-wait-seconds 10 \
  --post-next-settle-seconds 8 \
  --snapshot-settle-seconds 2 \
  --comment-by-content \
  --use-ai-comment \
  --comment-style humorous
```

4. Share-enabled run (only when user explicitly asks)
```bash
OPENAI_API_KEY='<YOUR_KEY>' python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 5 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --comment-by-content \
  --use-ai-comment \
  --enable-share \
  --share-target '3214抖音群'
```

## Output Template

After a run, report:
- command used
- rounds requested vs completed
- share decisions summary (`shared`, `skip_ad`, `skip_low_engagement`, `disabled`)
- any blocking errors
- next recommended run command

## Safety Defaults

- Default to `--mode scan`.
- Do not add `--enable-share` unless user explicitly requests real sharing.
- Keep `--require-login` on for real-site runs.
- Do not modify ad/share gating rules unless requested.
