from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from typing import Any

from .models import ContentSnapshot

LIVE_TEXT_HINTS = (
    "直播",
    "直播中",
    "正在直播",
    "福袋",
    "礼物",
    "音浪",
    "进入直播间",
)

SHORT_VIDEO_TEXT_HINTS = (
    "点赞",
    "评论",
    "收藏",
    "转发",
    "作品",
)

AUTH_COOKIE_CANDIDATES = (
    "sessionid",
    "sessionid_ss",
    "sid_tt",
    "uid_tt",
    "passport_csrf_token",
)

LOGIN_UI_SELECTORS = (
    "button:has-text('登录')",
    "text=立即登录",
    "text=扫码登录",
    "text=去登录",
    "text=登录",
)

RECOMMEND_SELECTORS = (
    "aside a:has-text('推荐')",
    "nav a:has-text('推荐')",
    "a[href*='recommend']",
    "[data-e2e*='recommend']",
)

COMMENT_PANEL_STRONG_SELECTORS = (
    "textarea[placeholder*='说点什么']",
    "textarea[placeholder*='善语结善缘']",
    "button:has-text('发送')",
    "[data-e2e*='comment-input']",
)

COMMENT_PANEL_HEADER_SELECTORS = (
    "text=全部评论",
    "text=最新评论",
)

COMMENT_TEXT_SELECTORS = (
    "[data-e2e*='comment-item']",
    "[data-e2e*='comment-content']",
    "[class*='comment'][class*='item']",
    "[class*='CommentItem']",
    "[class*='comment'][class*='content']",
)

COMMENT_PANEL_ITEM_SELECTORS = (
    "[data-e2e*='comment-item']",
    "[data-e2e*='comment-content']",
)

COMMENT_OPEN_BUTTON_SELECTORS = (
    "button:has-text('评论')",
    "[role='button']:has-text('评论')",
    "[aria-label*='评论']",
    "[data-e2e*='comment']",
)

COMMENT_INPUT_SELECTORS = (
    "textarea[placeholder*='说点什么']",
    "textarea[placeholder*='善语结善缘']",
    "textarea[placeholder*='评论']",
    "input[placeholder*='说点什么']",
    "input[placeholder*='写评论']",
    "input[placeholder*='评论']",
    "[data-e2e*='comment-input'] textarea",
    "[data-e2e*='comment-input'] input",
    "[data-e2e*='comment-input'] [contenteditable]",
    "[contenteditable='true']",
    "[contenteditable='plaintext-only']",
    "[contenteditable='']",
    "[role='textbox']",
)

COMMENT_COMPOSER_TRIGGER_SELECTORS = (
    "text=说点什么",
    "text=善语结善缘",
    "text=写评论",
    "text=发布评论",
    "[data-e2e*='comment-input']",
    "[class*='comment'][class*='input']",
    "[class*='Comment'][class*='Input']",
    "[class*='input'][class*='comment']",
)

MENTION_WAIT_BEFORE_SELECT_MS = 900
MENTION_WAIT_AFTER_SELECT_MS = 700
MENTION_WAIT_BEFORE_SEND_MS = 550
MENTION_WAIT_AFTER_SEND_MS = 1300

SHARE_BUTTON_SELECTORS = (
    "[data-e2e*='share']",
    "button:has-text('转发')",
    "text=转发",
    "button:has-text('分享')",
    "text=分享",
    "[class*='share']",
)

SHARE_COPY_SELECTORS = (
    "button:has-text('复制链接')",
    "text=复制链接",
    "button:has-text('复制到剪贴板')",
    "text=复制到剪贴板",
    "button:has-text('复制口令')",
    "text=复制口令",
    "button:has-text('复制')",
    "text=复制",
)

SHARE_PANEL_HINT_SELECTORS = (
    "text=分享到",
    "text=转发到",
    "text=复制链接",
    "text=复制口令",
)

SHARE_DIRECT_SELECTORS = (
    "button:has-text('私信好友')",
    "text=私信好友",
    "button:has-text('发送给朋友')",
    "text=发送给朋友",
    "text=好友",
)

SHARE_SEARCH_INPUT_SELECTORS = (
    "input[placeholder*='搜索']",
    "input[placeholder*='输入']",
    "input[placeholder*='昵称']",
    "input[type='search']",
    "[data-e2e*='search'] input",
)

SHARE_MESSAGE_INPUT_SELECTORS = (
    "input[placeholder*='发送消息']",
    "textarea[placeholder*='发送消息']",
    "textarea[placeholder*='捎句话']",
    "input[placeholder*='捎句话']",
    "textarea[placeholder*='说点什么']",
    "textarea[placeholder*='留言']",
    "textarea[placeholder*='发条消息']",
    "input[placeholder*='说点什么']",
    "input[placeholder*='发条消息']",
    "[contenteditable='true']",
)

SHARE_WHISPER_SELECTORS = (
    "button:has-text('捎句话')",
    "text=捎句话",
)

SHARE_MESSAGE_SEND_SELECTORS = (
    "button:has-text('发送')",
    "[aria-label*='发送']",
    "[class*='send'][role='button']",
    "[class*='Send'][role='button']",
    "[class*='send']",
    "[class*='Send']",
)

PRIVATE_CHAT_HINT_SELECTORS = (
    "text=关闭会话",
    "text=私信",
)

PRIVATE_CHAT_CLOSE_SELECTORS = (
    "button:has-text('关闭会话')",
    "text=关闭会话",
    "[aria-label*='关闭']",
    "[class*='close']",
)

SHARE_SEND_SELECTORS = (
    "button:has-text('发送')",
    "button:has-text('分享')",
    "text=发送",
    "text=分享",
)


@dataclass
class PlaywrightBrowserAdapter:
    """
    Playwright browser adapter used by the state machine.

    Defaults are safe:
    - `dry_run_post=True`: does not send real comments.
    - `require_login=False`: allows running read-only checks without login.
    """

    start_url: str = "https://www.douyin.com/"
    headless: bool = False
    user_data_dir: str = ".playwright_profile"
    screenshot_dir: str = "artifacts/screenshots"
    frame_capture_count: int = 3
    frame_interval_ms: int = 1000
    navigation_timeout_ms: int = 20000
    dry_run_post: bool = True
    require_login: bool = False
    manual_login_prompt: bool = True
    login_timeout_seconds: int = 180
    login_poll_interval_seconds: float = 2.0
    snapshot_on_scan: bool = False
    ensure_recommend_on_open: bool = True
    wait_scale: float = 3.0
    post_next_settle_seconds: float = 8.0
    snapshot_settle_seconds: float = 2.0

    _pw: Any = field(init=False, default=None, repr=False)
    _context: Any = field(init=False, default=None, repr=False)
    _page: Any = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Playwright is not installed. Install with `python3 -m pip install playwright` "
                "and then run `python3 -m playwright install chromium`."
            ) from exc

        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)

    def _ensure_started(self) -> None:
        try:
            if self._page is not None and not self._page.is_closed():
                return
        except Exception:
            # Detached/invalid page handle: force a clean restart below.
            pass

        # If old Playwright handles still exist, close them first to avoid
        # nested sync_playwright loops when recreating browser sessions.
        if self._context is not None or self._pw is not None or self._page is not None:
            self.close()

        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(Path(self.user_data_dir).resolve()),
            headless=self.headless,
            viewport={"width": 1320, "height": 860},
        )
        self._context.set_default_timeout(self.navigation_timeout_ms)
        pages = self._context.pages
        self._page = pages[0] if pages else self._context.new_page()

    def open_home(self) -> None:
        self._ensure_started()
        self._page.goto(self.start_url, wait_until="domcontentloaded")
        self._wait_for_page_stable()
        self._sleep(1800)
        if self.ensure_recommend_on_open:
            self._ensure_recommend_feed()
        self._sleep(1000)

    def ensure_login(self) -> bool:
        self._ensure_started()
        if not self.require_login:
            return True

        if self._likely_logged_in():
            return True

        if self.headless:
            print("[login] 当前为 headless 模式，无法完成手动登录。")
            return False

        self._open_login_panel_if_possible()
        print("\n[login] 当前看起来未登录，请在浏览器中完成登录。")
        if self.manual_login_prompt:
            print(f"[login] 系统将自动等待最多 {self.login_timeout_seconds} 秒检测登录态。")

        deadline = time.monotonic() + self.login_timeout_seconds
        announce_deadline = time.monotonic()
        while time.monotonic() < deadline:
            if self._likely_logged_in():
                print("[login] 已检测到登录成功。")
                return True

            if self.manual_login_prompt and time.monotonic() >= announce_deadline:
                remaining = int(max(0, deadline - time.monotonic()))
                print(f"[login] 等待登录中，剩余约 {remaining} 秒...")
                announce_deadline = time.monotonic() + 20

            self._sleep(int(self.login_poll_interval_seconds * 1000))
            try:
                self._page.wait_for_load_state("domcontentloaded", timeout=1200)
            except Exception:
                pass

        print("[login] 登录等待超时，请确认已完成登录或切换非 headless 运行。")
        return self._likely_logged_in()

    def _likely_logged_in(self) -> bool:
        if self._visible_any(LOGIN_UI_SELECTORS):
            return False

        if self._has_auth_cookie():
            return True

        # Fallback UI-based hints for logged-in states.
        authed_selectors = (
            "text=我的",
            "text=消息",
            "a[href*='/user/']",
            "[data-e2e='user-avatar']",
        )
        return self._visible_any(authed_selectors)

    def _has_auth_cookie(self) -> bool:
        try:
            cookies = self._context.cookies()
        except Exception:
            return False
        for cookie in cookies:
            if cookie.get("name", "").lower() in AUTH_COOKIE_CANDIDATES:
                return True
        return False

    def _open_login_panel_if_possible(self) -> None:
        if self._likely_logged_in():
            return
        locator = self._first_visible(LOGIN_UI_SELECTORS)
        if locator is None:
            return
        try:
            locator.click()
            self._sleep(1000)
        except Exception:
            pass

    def current_snapshot(self) -> ContentSnapshot:
        self._ensure_started()
        self._sleep_raw_seconds(self.snapshot_settle_seconds)
        url = self._page.url
        video_id = self._extract_video_id(url)
        if self.snapshot_on_scan:
            self._save_screenshot(f"{video_id}_scan")
        dom_text = self._safe_body_text(max_len=3200)
        dom_markers = self._collect_dom_markers(dom_text)
        return ContentSnapshot(
            video_id=video_id,
            url=url,
            dom_text=dom_text,
            dom_markers=tuple(dom_markers),
        )

    def next_item(self, reason: str) -> None:
        self._ensure_started()
        before = self._feed_signature()
        moved = "unknown"
        try:
            self._advance_once()
            self._sleep_raw_seconds(self.post_next_settle_seconds)
            after = self._feed_signature()
            if before and after and after != before:
                moved = "true"
        except Exception as exc:
            if self._is_closed_error(exc):
                self._recover_feed_context()
            else:
                raise
        print(f"[next] reason={reason} moved={moved}")

    def open_comment_panel(self) -> bool:
        self._ensure_started()
        if self._is_comment_panel_open():
            return True
        for _attempt in range(2):
            self._open_comment_panel()
            if self._is_comment_panel_open():
                return True
            self._sleep(500)
        return False

    def is_comment_panel_open(self) -> bool:
        self._ensure_started()
        return self._is_comment_panel_open()

    def close_comment_panel_if_open(self) -> bool:
        self._ensure_started()
        if not self._is_comment_panel_open():
            return True

        for _attempt in range(4):
            for key in ("x", "X"):
                self._blur_active_editor()
                try:
                    self._page.keyboard.press(key)
                except Exception:
                    continue
                self._sleep(700)
                if not self._is_comment_panel_open():
                    return True
        return not self._is_comment_panel_open()

    def get_visible_comment_texts(
        self,
        limit: int = 8,
        scroll_rounds: int = 0,
        scroll_pause_ms: int = 420,
    ) -> tuple[str, ...]:
        self._ensure_started()
        if not self._is_comment_panel_open():
            return ()

        texts: list[str] = []
        seen: set[str] = set()

        def _collect_once() -> None:
            for selector in COMMENT_TEXT_SELECTORS:
                try:
                    loc = self._page.locator(selector)
                    count = min(loc.count(), max(12, limit * 3))
                except Exception:
                    continue

                for idx in range(count):
                    try:
                        item = loc.nth(idx)
                        if not item.is_visible():
                            continue
                        raw = item.inner_text(timeout=800)
                    except Exception:
                        continue

                    text = " ".join(raw.split())
                    if len(text) < 3:
                        continue
                    if text in seen:
                        continue
                    # Filter obvious UI noise from copied panel controls.
                    if "发布评论" in text or "全部评论" in text:
                        continue
                    seen.add(text)
                    texts.append(text)
                    if len(texts) >= limit:
                        return

        _collect_once()
        rounds = max(0, scroll_rounds)
        for _ in range(rounds):
            if len(texts) >= limit:
                break
            moved = self._scroll_comment_panel_once()
            if not moved:
                break
            self._sleep(max(180, int(scroll_pause_ms)))
            _collect_once()

        return tuple(texts)

    def _scroll_comment_panel_once(self) -> bool:
        try:
            moved = self._page.evaluate(
                """
                () => {
                  const vw = window.innerWidth || document.documentElement.clientWidth || 1320;
                  const vh = window.innerHeight || document.documentElement.clientHeight || 860;
                  const nodes = Array.from(document.querySelectorAll('div, section, aside, ul, main'));

                  let target = null;
                  let bestScore = -1;
                  for (const el of nodes) {
                    if (!el || !(el instanceof HTMLElement)) continue;
                    const style = window.getComputedStyle(el);
                    if (!style) continue;
                    const overflowY = style.overflowY || '';
                    if (overflowY !== 'auto' && overflowY !== 'scroll') continue;

                    const rect = el.getBoundingClientRect();
                    if (!rect || rect.width < 160 || rect.height < 180) continue;
                    const cx = rect.left + rect.width * 0.5;
                    const cy = rect.top + rect.height * 0.5;
                    if (cx < vw * 0.54 || cx > vw * 0.99) continue;
                    if (cy < vh * 0.08 || cy > vh * 0.95) continue;
                    if (el.scrollHeight <= el.clientHeight + 8) continue;

                    const score = rect.width * rect.height;
                    if (score > bestScore) {
                      bestScore = score;
                      target = el;
                    }
                  }

                  if (!target) return false;
                  const before = target.scrollTop;
                  const delta = Math.max(target.clientHeight * 0.72, 220);
                  target.scrollTop = Math.min(before + delta, target.scrollHeight);
                  const after = target.scrollTop;
                  return Math.abs(after - before) > 1;
                }
                """
            )
            return bool(moved)
        except Exception:
            return False

    def get_current_video_context_texts(self, limit: int = 18) -> tuple[str, ...]:
        self._ensure_started()
        max_items = max(8, min(limit * 5, 120))
        try:
            raw = self._page.evaluate(
                """
                (maxItems) => {
                  const maxCount = Math.max(8, Number(maxItems) || 60);
                  const vw = window.innerWidth || document.documentElement.clientWidth || 1320;
                  const vh = window.innerHeight || document.documentElement.clientHeight || 860;
                  const out = [];
                  const seen = new Set();

                  const inMainRegion = (rect) => {
                    if (!rect) return false;
                    const cx = rect.left + rect.width / 2;
                    const cy = rect.top + rect.height / 2;
                    return cx >= vw * 0.03 && cx <= vw * 0.58 && cy >= vh * 0.34 && cy <= vh * 0.97;
                  };

                  const addFromSelector = (selector, nodeCap) => {
                    let nodes;
                    try {
                      nodes = document.querySelectorAll(selector);
                    } catch (_err) {
                      return;
                    }
                    const total = Math.min(nodes.length, nodeCap);
                    for (let i = 0; i < total; i += 1) {
                      if (out.length >= maxCount) return;
                      const el = nodes[i];
                      if (!el) continue;
                      const style = window.getComputedStyle(el);
                      if (!style || style.display === "none" || style.visibility === "hidden") continue;
                      if (Number(style.opacity || "1") <= 0.01) continue;
                      const rect = el.getBoundingClientRect();
                      if (!rect || rect.width < 2 || rect.height < 2) continue;
                      if (!inMainRegion(rect)) continue;
                      const text = String(el.innerText || "").replace(/\\s+/g, " ").trim();
                      if (!text || text.length < 2 || text.length > 120) continue;
                      if (seen.has(text)) continue;
                      seen.add(text);
                      out.push(text);
                    }
                  };

                  const preferredSelectors = [
                    "[data-e2e*='desc']",
                    "[data-e2e*='title']",
                    "[data-e2e*='caption']",
                    "[data-e2e*='video-info']",
                    "[class*='desc']",
                    "[class*='title']",
                    "[class*='caption']",
                    "[class*='author']",
                    "[data-e2e*='user']"
                  ];
                  for (const selector of preferredSelectors) {
                    if (out.length >= maxCount) break;
                    addFromSelector(selector, 100);
                  }

                  if (out.length < Math.min(14, maxCount)) {
                    const genericSelectors = ["h1", "h2", "h3", "p", "a", "span"];
                    for (const selector of genericSelectors) {
                      if (out.length >= maxCount) break;
                      addFromSelector(selector, 220);
                    }
                  }

                  return out.slice(0, maxCount);
                }
                """,
                max_items,
            )
        except Exception:
            return ()

        if not isinstance(raw, list):
            return ()

        texts: list[str] = []
        seen: set[str] = set()
        for item in raw:
            text = " ".join(str(item).split()).strip()
            if len(text) < 2:
                continue
            if text in seen:
                continue
            seen.add(text)
            texts.append(text)
            if len(texts) >= limit:
                break
        return tuple(texts)

    def get_right_action_metric_texts(self, limit: int = 8) -> tuple[str, ...]:
        self._ensure_started()
        cap = max(4, min(limit, 12))
        try:
            raw = self._page.evaluate(
                """
                (maxCount) => {
                  const cap = Math.max(4, Math.min(Number(maxCount) || 8, 12));
                  const vw = window.innerWidth || document.documentElement.clientWidth || 1320;
                  const vh = window.innerHeight || document.documentElement.clientHeight || 860;
                  const pat = /^\\d+(?:\\.\\d+)?(?:万|亿|[wWkKmM千])?$/;
                  const nodes = Array.from(document.querySelectorAll("span, p, div, strong, b, a"));
                  const items = [];

                  for (const el of nodes) {
                    if (!el || !(el instanceof HTMLElement)) continue;
                    const style = window.getComputedStyle(el);
                    if (!style || style.display === "none" || style.visibility === "hidden") continue;
                    if (Number(style.opacity || "1") <= 0.01) continue;

                    const rawText = String(el.innerText || "").replace(/\\s+/g, "").trim();
                    if (!rawText || rawText.length > 10) continue;
                    if (!pat.test(rawText)) continue;

                    const rect = el.getBoundingClientRect();
                    if (!rect || rect.width < 6 || rect.height < 6) continue;
                    const cx = rect.left + rect.width * 0.5;
                    const cy = rect.top + rect.height * 0.5;

                    // Right vertical action bar region.
                    if (cx < vw * 0.90 || cx > vw * 0.995) continue;
                    if (cy < vh * 0.20 || cy > vh * 0.97) continue;

                    items.push({
                      text: rawText,
                      cy,
                      cx,
                      area: rect.width * rect.height,
                    });
                  }

                  items.sort((a, b) => {
                    if (Math.abs(a.cy - b.cy) > 6) return a.cy - b.cy;
                    if (Math.abs(a.cx - b.cx) > 4) return a.cx - b.cx;
                    return b.area - a.area;
                  });

                  // Group by vertical row first to suppress duplicated DOM wrappers
                  // that often expose the same metric twice (text + nested text node).
                  const byRow = [];
                  for (const item of items) {
                    let matched = null;
                    for (const kept of byRow) {
                      if (Math.abs(kept.cy - item.cy) < 20) {
                        matched = kept;
                        break;
                      }
                    }
                    if (!matched) {
                      byRow.push({ ...item });
                      continue;
                    }
                    // Prefer the larger visible node in the same row.
                    if (item.area > matched.area) {
                      matched.text = item.text;
                      matched.cx = item.cx;
                      matched.area = item.area;
                    }
                    matched.cy = Math.min(matched.cy, item.cy);
                  }

                  byRow.sort((a, b) => a.cy - b.cy);
                  return byRow.map((x) => x.text).slice(0, cap);
                }
                """,
                cap,
            )
        except Exception:
            return ()

        if not isinstance(raw, list):
            return ()
        out: list[str] = []
        for item in raw:
            text = "".join(str(item).split()).strip()
            if not text:
                continue
            out.append(text)
            if len(out) >= cap:
                break
        return tuple(out)

    def wait_seconds(self, seconds: float) -> None:
        ms = max(50, int(seconds * 1000))
        self._sleep(ms)

    def has_live_room_hint(self) -> bool:
        self._ensure_started()
        viewport = self._page.viewport_size or {"width": 1320, "height": 860}
        width = float(viewport["width"])
        height = float(viewport["height"])

        def _in_region(box: dict[str, float], x1: float, x2: float, y1: float, y2: float) -> bool:
            cx = box["x"] + box["width"] * 0.5
            cy = box["y"] + box["height"] * 0.5
            return (x1 * width) <= cx <= (x2 * width) and (y1 * height) <= cy <= (y2 * height)

        # Live prompt usually appears near lower-middle of the video canvas.
        enter_selectors = (
            "text=点击或按 F 进入直播间",
            "text=按 F 进入直播间",
            "text=进入直播间",
        )
        has_enter_overlay = False
        for selector in enter_selectors:
            try:
                loc = self._page.locator(selector)
                count = min(loc.count(), 6)
                for idx in range(count):
                    item = loc.nth(idx)
                    if not item.is_visible():
                        continue
                    box = item.bounding_box()
                    if box is None:
                        continue
                    if _in_region(box, 0.18, 0.86, 0.42, 0.96):
                        has_enter_overlay = True
                        break
                if has_enter_overlay:
                    break
            except Exception:
                continue

        # Live badge usually appears at lower-left side.
        has_live_badge = False
        try:
            loc = self._page.locator("text=直播中")
            count = min(loc.count(), 6)
            for idx in range(count):
                item = loc.nth(idx)
                if not item.is_visible():
                    continue
                box = item.bounding_box()
                if box is None:
                    continue
                if _in_region(box, 0.0, 0.42, 0.45, 0.98):
                    has_live_badge = True
                    break
        except Exception:
            pass

        return has_live_badge and has_enter_overlay

    def has_ad_badge(self) -> bool:
        self._ensure_started()
        viewport = self._page.viewport_size or {"width": 1320, "height": 860}
        width = float(viewport["width"])
        height = float(viewport["height"])

        def _in_region(box: dict[str, float], x1: float, x2: float, y1: float, y2: float) -> bool:
            cx = box["x"] + box["width"] * 0.5
            cy = box["y"] + box["height"] * 0.5
            return (x1 * width) <= cx <= (x2 * width) and (y1 * height) <= cy <= (y2 * height)

        selectors = (
            "text=/@[^\\s]{1,40}\\s*广告/",
            "text=广告",
            "[data-e2e*='ad']",
            "[class*='ad']",
            "[class*='Ad']",
        )
        for selector in selectors:
            try:
                loc = self._page.locator(selector)
                count = min(loc.count(), 24)
            except Exception:
                continue
            for idx in range(count):
                try:
                    item = loc.nth(idx)
                    if not item.is_visible():
                        continue
                    text = " ".join((item.inner_text(timeout=300) or "").split())
                    if "广告" not in text:
                        continue
                    box = item.bounding_box()
                    if box is None:
                        continue
                except Exception:
                    continue

                # User rule: ad is valid only when author area shows the "广告" tag.
                # We therefore only accept ad-text in lower-left metadata region.
                if _in_region(box, 0.02, 0.50, 0.52, 0.99):
                    return True
        return False

    def capture_frames(self, snapshot: ContentSnapshot) -> tuple[str, ...]:
        self._ensure_started()
        frame_texts: list[str] = []

        for idx in range(self.frame_capture_count):
            tag = f"{snapshot.video_id}_f{idx + 1}"
            self._save_screenshot(tag)
            text = self._safe_body_text(max_len=260)
            if text:
                frame_texts.append(text)
            if idx < self.frame_capture_count - 1:
                self._sleep(self.frame_interval_ms)

        unique: list[str] = []
        seen: set[str] = set()
        for text in frame_texts:
            if text not in seen:
                seen.add(text)
                unique.append(text)
        return tuple(unique)

    def post_comment(self, comment: str) -> bool:
        self._ensure_started()
        if self.dry_run_post:
            print(f"[dry-run] comment would be posted: {comment}")
            return True
        mention_targets = self._extract_mention_targets(comment)
        has_mention = bool(mention_targets)
        mention_suffix = self._extract_mention_suffix(comment, mention_targets)

        if not self._is_comment_panel_open():
            self._open_comment_panel()
        if not self._is_comment_panel_open():
            print("[post] comment panel not open after X")
            return False

        send_selectors = (
            "button:has-text('发送')",
            "text=发送",
        )

        locator = self._first_visible_in_region(
            COMMENT_INPUT_SELECTORS,
            x1=0.54,
            x2=1.0,
            y1=0.56,
            y2=0.995,
            max_scan_per_selector=10,
        )
        if locator is None:
            locator = self._first_visible(COMMENT_INPUT_SELECTORS)
        if locator is None:
            composer_top = self._activate_comment_input_area()
            if composer_top > 0:
                posted = self._post_comment_with_keyboard_focus(
                    comment=comment,
                    mention_targets=mention_targets,
                    mention_suffix=mention_suffix,
                    input_top=composer_top,
                    send_selectors=send_selectors,
                )
                if posted:
                    return True
            try:
                debug_inputs = self._page.evaluate(
                    """
                    () => {
                      const nodes = Array.from(document.querySelectorAll(
                        "textarea,input,[contenteditable],[role='textbox']"
                      ));
                      const visible = [];
                      for (const el of nodes) {
                        const rect = el.getBoundingClientRect();
                        if (!rect || rect.width < 10 || rect.height < 10) continue;
                        const style = window.getComputedStyle(el);
                        if (!style || style.display === "none" || style.visibility === "hidden") continue;
                        if (Number(style.opacity || "1") < 0.2) continue;
                        if (rect.right < window.innerWidth * 0.50) continue;
                        const tag = (el.tagName || "").toLowerCase();
                        const role = el.getAttribute("role") || "";
                        const ce = el.getAttribute("contenteditable") || "";
                        const ph = el.getAttribute("placeholder") || "";
                        const cls = (el.className || "").toString().replace(/\\s+/g, " ").slice(0, 80);
                        visible.push(
                          `${tag}|role=${role}|ce=${ce}|ph=${ph}|x=${Math.round(rect.left)},y=${Math.round(rect.top)},w=${Math.round(rect.width)},h=${Math.round(rect.height)}|cls=${cls}`
                        );
                      }
                      return visible.slice(0, 12);
                    }
                    """
                )
                if debug_inputs:
                    print("[post] input debug:", " || ".join(str(item) for item in debug_inputs))
            except Exception:
                pass
            print("[post] comment input not found")
            return False

        input_top = 0.0
        tag_name = ""
        try:
            locator.click()
            tag_name = str(locator.evaluate("el => (el.tagName || '').toLowerCase()")).strip()
            box = locator.bounding_box()
            if box is not None:
                input_top = float(box["y"])
            if has_mention:
                if tag_name in {"textarea", "input"}:
                    locator.fill("")
                    mention_ok = self._type_mentions_and_select_candidates(
                        mention_targets=mention_targets,
                        input_top=input_top,
                        type_fn=lambda text: locator.type(text, delay=20),
                    )
                else:
                    self._page.keyboard.press("Meta+A")
                    self._page.keyboard.press("Backspace")
                    mention_ok = self._type_mentions_and_select_candidates(
                        mention_targets=mention_targets,
                        input_top=input_top,
                        type_fn=lambda text: self._page.keyboard.type(text, delay=20),
                    )
                if not mention_ok:
                    return False
            else:
                if tag_name in {"textarea", "input"}:
                    locator.fill(comment)
                else:
                    self._page.keyboard.press("Meta+A")
                    self._page.keyboard.type(comment, delay=20)
        except Exception:
            print("[post] failed to type comment")
            return False

        if has_mention:
            if mention_suffix:
                try:
                    if tag_name in {"textarea", "input"}:
                        locator.click()
                        locator.type(f" {mention_suffix}", delay=20)
                    else:
                        self._page.keyboard.type(f" {mention_suffix}", delay=20)
                except Exception:
                    print("[post] failed to append mention suffix")
                    return False
            self._sleep(MENTION_WAIT_BEFORE_SEND_MS)

        if has_mention:
            try:
                self._page.keyboard.press("Enter")
            except Exception:
                send_btn = self._first_visible(send_selectors)
                try:
                    if send_btn is not None:
                        send_btn.click()
                    else:
                        self._page.keyboard.press("Enter")
                except Exception:
                    print("[post] failed to trigger send action")
                    return False
            self._sleep(MENTION_WAIT_AFTER_SEND_MS)
            return True

        send_btn = self._first_visible(send_selectors)
        try:
            if send_btn is not None:
                send_btn.click()
            else:
                self._page.keyboard.press("Enter")
        except Exception:
            print("[post] failed to trigger send action")
            return False

        self._sleep(1800)
        body_text = self._safe_body_text(max_len=4500)
        return comment[:8] in body_text

    def _activate_comment_input_area(self) -> float:
        locator = self._first_visible_in_region(
            COMMENT_COMPOSER_TRIGGER_SELECTORS,
            x1=0.66,
            x2=1.0,
            y1=0.82,
            y2=0.998,
            max_scan_per_selector=14,
        )
        if locator is None:
            locator = self._first_visible(COMMENT_COMPOSER_TRIGGER_SELECTORS)
        if locator is not None and self._click_locator_safe(locator, timeout=1600):
            self._sleep(200)
            try:
                box = locator.bounding_box()
                if box is not None:
                    return float(box["y"])
            except Exception:
                pass
            return 0.0

        try:
            clicked_top = self._page.evaluate(
                """
                () => {
                  const vw = window.innerWidth || document.documentElement.clientWidth || 0;
                  const vh = window.innerHeight || document.documentElement.clientHeight || 0;
                  const minX = vw * 0.66;
                  const minY = vh * 0.82;
                  const maxY = vh * 0.998;
                  const pats = [/说点什么/, /善语结善缘/, /写评论/, /发布评论/];
                  const norm = (v) => String(v || "").replace(/\\s+/g, " ").trim();
                  const items = [];
                  for (const node of Array.from(document.querySelectorAll("div,button,span,p"))) {
                    if (!node || typeof node.getBoundingClientRect !== "function") continue;
                    const rect = node.getBoundingClientRect();
                    if (!rect || rect.width < 24 || rect.height < 12) continue;
                    if (rect.right < minX || rect.top < minY || rect.bottom > maxY) continue;
                    const style = window.getComputedStyle(node);
                    if (!style || style.display === "none" || style.visibility === "hidden") continue;
                    if (Number(style.opacity || "1") < 0.2) continue;
                    const text = norm(node.innerText || node.textContent || "");
                    if (!text || text.length > 28) continue;
                    if (!pats.some((pat) => pat.test(text))) continue;
                    const clickable = node.closest("button,[role='button'],[onclick]") || node;
                    const cRect = clickable.getBoundingClientRect();
                    items.push({ el: clickable, top: cRect.top, left: cRect.left });
                  }
                  items.sort((a, b) => (Math.abs(a.top - b.top) > 6 ? a.top - b.top : a.left - b.left));
                  if (!items.length) return 0;
                  items[0].el.click();
                  return Number(items[0].top || 0);
                }
                """
            )
            if float(clicked_top or 0) > 0:
                self._sleep(200)
                return float(clicked_top)
        except Exception:
            pass
        return 0.0

    def _post_comment_with_keyboard_focus(
        self,
        comment: str,
        mention_targets: tuple[str, ...],
        mention_suffix: str,
        input_top: float,
        send_selectors: tuple[str, ...],
    ) -> bool:
        has_mention = bool(mention_targets)
        if input_top <= 0:
            return False
        viewport = self._page.viewport_size or {"width": 1320, "height": 860}
        width = float(viewport["width"])
        height = float(viewport["height"])
        click_x = width * 0.84
        click_y = min(height * 0.992, max(input_top + 18.0, height * 0.82))

        try:
            self._page.mouse.click(click_x, click_y, button="left")
            self._sleep(120)
            self._page.keyboard.press("Meta+A")
            self._page.keyboard.press("Backspace")
            if has_mention:
                mention_ok = self._type_mentions_and_select_candidates(
                    mention_targets=mention_targets,
                    input_top=input_top,
                    type_fn=lambda text: self._page.keyboard.type(text, delay=20),
                )
                if not mention_ok:
                    return False
                if mention_suffix:
                    self._page.keyboard.type(f" {mention_suffix}", delay=20)
                self._sleep(MENTION_WAIT_BEFORE_SEND_MS)
            else:
                self._page.keyboard.type(comment, delay=20)
                self._sleep(220)
        except Exception:
            return False

        if has_mention:
            try:
                self._page.keyboard.press("Enter")
            except Exception:
                send_btn = self._first_visible(send_selectors)
                if send_btn is not None:
                    try:
                        send_btn.click()
                    except Exception:
                        return False
                else:
                    return False
            self._sleep(MENTION_WAIT_AFTER_SEND_MS)
            return True

        send_btn = self._first_visible(send_selectors)
        try:
            if send_btn is not None:
                send_btn.click()
            else:
                self._page.keyboard.press("Enter")
        except Exception:
            return False
        self._sleep(1800)
        body_text = self._safe_body_text(max_len=4500)
        return comment[:8] in body_text

    def _extract_mention_targets(self, comment: str) -> tuple[str, ...]:
        text = " ".join(comment.split()).strip()
        if "@" not in text:
            return ()
        raw_targets = [
            item.strip()
            for item in re.findall(r"@([A-Za-z0-9_\u4e00-\u9fff·・-]{1,32})", text)
            if item.strip()
        ]
        targets: list[str] = []
        seen: set[str] = set()
        for raw in raw_targets:
            target = " ".join(raw.split()).strip().lstrip("@")
            if not target:
                continue
            if target in seen:
                continue
            seen.add(target)
            targets.append(target)
        return tuple(targets)

    def _extract_mention_suffix(self, comment: str, mention_targets: tuple[str, ...]) -> str:
        text = " ".join(comment.split()).strip()
        if not text:
            return ""
        if not mention_targets:
            return text
        stripped = text
        for target in mention_targets:
            target_text = " ".join(target.split()).strip().lstrip("@")
            if not target_text:
                continue
            stripped = re.sub(rf"@{re.escape(target_text)}", "", stripped, count=1)
        return " ".join(stripped.split()).strip()

    def _type_mentions_and_select_candidates(
        self,
        mention_targets: tuple[str, ...],
        input_top: float,
        type_fn: Any,
    ) -> bool:
        if input_top <= 0:
            return False
        for idx, target in enumerate(mention_targets):
            token = f"@{target}" if idx == 0 else f" @{target}"
            try:
                type_fn(token)
            except Exception:
                return False
            self._sleep(MENTION_WAIT_BEFORE_SELECT_MS)
            selected = self._select_first_mention_candidate(
                mention_target=target,
                input_top=input_top,
            )
            if not selected:
                self._sleep(320)
                selected = self._select_first_mention_candidate(
                    mention_target=target,
                    input_top=input_top,
                )
            if not selected:
                print(f"[post] mention candidate not selected for @{target}")
                return False
            print(f"[post] mention candidate clicked for @{target}")
            self._sleep(MENTION_WAIT_AFTER_SELECT_MS)
        return True

    def _select_first_mention_candidate(self, mention_target: str, input_top: float = 0.0) -> bool:
        target = " ".join(mention_target.split()).strip().lstrip("@")
        if not target:
            return True
        if input_top <= 0:
            return False
        try:
            return bool(
                self._page.evaluate(
                    """
                    (args) => {
                      const mention = String(args.mention || "").trim().replace(/^@+/, "");
                      if (!mention) return false;
                      const inputTop = Number(args.inputTop || 0);
                      if (!(inputTop > 0)) return false;
                      const vw = window.innerWidth || document.documentElement.clientWidth || 0;
                      const minX = vw * 0.68;
                      const maxX = vw * 0.995;
                      const minY = Math.max(0, inputTop - 185);
                      const maxY = Math.max(0, inputTop - 10);

                      const norm = (v) => String(v || "").replace(/\\s+/g, " ").trim();
                      const isVisible = (el) => {
                        if (!el || typeof el.getBoundingClientRect !== "function") return false;
                        const rect = el.getBoundingClientRect();
                        if (!rect || rect.width < 18 || rect.height < 14) return false;
                        const style = window.getComputedStyle(el);
                        if (!style || style.display === "none" || style.visibility === "hidden") return false;
                        if (Number(style.opacity || "1") < 0.2) return false;
                        if (rect.right < minX || rect.left > maxX) return false;
                        if (rect.top < minY || rect.bottom > maxY) return false;
                        return true;
                      };

                      const isBadLabel = (text) => {
                        if (!text) return true;
                        return (
                          text === "发送" ||
                          text === "评论" ||
                          text.includes("发送给") ||
                          text.includes("回复")
                        );
                      };

                      const uniqueSort = (items) => {
                        const seen = new Set();
                        const out = [];
                        for (const item of items) {
                          if (seen.has(item.el)) continue;
                          seen.add(item.el);
                          out.push(item);
                        }
                        out.sort((a, b) => {
                          if (Math.abs(a.top - b.top) > 6) return a.top - b.top;
                          return a.left - b.left;
                        });
                        return out;
                      };

                      const tokens = [];
                      tokens.push(mention);
                      const prefix3 = mention.slice(0, Math.min(3, mention.length));
                      const prefix2 = mention.slice(0, Math.min(2, mention.length));
                      if (prefix3 && !tokens.includes(prefix3)) tokens.push(prefix3);
                      if (prefix2 && !tokens.includes(prefix2)) tokens.push(prefix2);

                      const pool = Array.from(document.querySelectorAll("button,[role='button'],li,a,div"));
                      const matches = [];
                      for (const node of pool) {
                        const clickable = node.closest("button,[role='button'],li,a,[onclick]") || node;
                        if (!isVisible(clickable)) continue;
                        const text = norm(clickable.innerText || clickable.textContent || "");
                        if (isBadLabel(text)) continue;
                        if (!tokens.some((tk) => tk && text.includes(tk))) continue;
                        const rect = clickable.getBoundingClientRect();
                        const hasAvatar = !!clickable.querySelector("img,[class*='avatar'],[class*='Avatar']");
                        if (!hasAvatar && text.length > 24) continue;
                        matches.push({ el: clickable, top: rect.top, left: rect.left, text });
                      }
                      const sortedMatches = uniqueSort(matches);
                      if (sortedMatches.length > 0) {
                        sortedMatches[0].el.click();
                        return true;
                      }

                      // Fallback: click the first avatar-like candidate in mention area.
                      const fallback = [];
                      for (const node of pool) {
                        const clickable = node.closest("button,[role='button'],li,a,[onclick]") || node;
                        if (!isVisible(clickable)) continue;
                        const rect = clickable.getBoundingClientRect();
                        if (rect.width < 34 || rect.height < 34) continue;
                        const text = norm(clickable.innerText || clickable.textContent || "");
                        if (isBadLabel(text)) continue;
                        const hasAvatar = !!clickable.querySelector("img,[class*='avatar'],[class*='Avatar']");
                        if (!hasAvatar) continue;
                        fallback.push({ el: clickable, top: rect.top, left: rect.left });
                      }
                      const sortedFallback = uniqueSort(fallback);
                      if (sortedFallback.length > 0) {
                        sortedFallback[0].el.click();
                        return true;
                      }
                      return false;
                    }
                    """,
                    {"mention": target, "inputTop": input_top},
                )
            )
        except Exception:
            return False

    def share_current_video(self) -> tuple[bool, str, str]:
        self._ensure_started()
        current_url = self._page.url

        share_btn = self._first_visible_in_region(
            SHARE_BUTTON_SELECTORS,
            x1=0.74,
            x2=1.0,
            y1=0.18,
            y2=0.98,
            max_scan_per_selector=10,
        )
        if share_btn is None:
            share_btn = self._first_visible(SHARE_BUTTON_SELECTORS)
        if share_btn is None:
            return False, "share_button_not_found", current_url

        if not self._click_locator_safe(share_btn, timeout=1800):
            return False, "share_click_failed", current_url
        self._sleep(900)

        copied_mode = ""
        for selector in SHARE_COPY_SELECTORS:
            locator = self._first_visible_in_region(
                (selector,),
                x1=0.1,
                x2=1.0,
                y1=0.08,
                y2=0.98,
                max_scan_per_selector=10,
            )
            if locator is None:
                locator = self._first_visible((selector,))
            if locator is None:
                continue
            if self._click_locator_safe(locator, timeout=1800):
                self._sleep(650)
                copied_mode = selector
                break

        if copied_mode:
            self._close_share_panel_if_open()
            return True, f"copied:{copied_mode}", self._page.url

        # Could not copy link, but share panel may still be opened.
        panel_opened = self._visible_any(SHARE_PANEL_HINT_SELECTORS)
        self._close_share_panel_if_open()
        if panel_opened:
            return False, "share_panel_opened_copy_not_found", self._page.url
        return False, "share_unknown", current_url

    def share_current_video_to_target(
        self,
        target_name: str,
        message: str = "",
    ) -> tuple[bool, str, str]:
        self._ensure_started()
        target = " ".join(target_name.split()).strip()
        if not target:
            return False, "target_empty", self._page.url

        ok, detail = self._open_share_panel()
        if not ok:
            return False, detail, self._page.url

        self._fill_share_search(target)
        target_share_btn = self._find_share_target(target)
        if target_share_btn is None:
            # Retry once for slow search-result rendering.
            self._sleep(650)
            self._fill_share_search(target)
            target_share_btn = self._find_share_target(target)
        if target_share_btn is None:
            self._close_post_share_views()
            return False, "target_not_found", self._page.url

        if not self._click_locator_safe(target_share_btn, timeout=1800):
            self._close_post_share_views()
            return False, "target_share_click_failed", self._page.url
        self._sleep(800)

        msg = message.strip()
        if msg:
            # Some UIs expose "捎句话", while others enter chat input directly.
            self._click_share_whisper_if_present()
            if not self._fill_share_message(msg):
                self._close_post_share_views()
                return False, "share_message_input_not_found", self._page.url
            if not self._send_share_message():
                self._close_post_share_views()
                return False, "share_message_send_failed", self._page.url
            self._sleep(650)
            self._close_post_share_views()
            return True, "sent_with_message", self._page.url

        # Without message: click row-right "分享" button to send.
        panel_opened = self._visible_any(SHARE_PANEL_HINT_SELECTORS)
        self._close_post_share_views()
        if panel_opened:
            return True, "sent_via_row_share_button", self._page.url
        return True, "sent_auto", self._page.url

    def close(self) -> None:
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None
        self._page = None

    def __del__(self) -> None:  # pragma: no cover
        self.close()

    def _visible_any(self, selectors: tuple[str, ...]) -> bool:
        for selector in selectors:
            if self._first_visible((selector,)) is not None:
                return True
        return False

    def _click_locator_safe(self, locator: Any, timeout: int = 1600) -> bool:
        try:
            locator.click(timeout=timeout)
            return True
        except Exception:
            pass
        try:
            locator.click(timeout=timeout, force=True)
            return True
        except Exception:
            pass
        try:
            locator.evaluate("el => el.click()")
            return True
        except Exception:
            return False

    def _first_visible_in_region(
        self,
        selectors: tuple[str, ...],
        x1: float,
        x2: float,
        y1: float,
        y2: float,
        max_scan_per_selector: int = 6,
    ) -> Any | None:
        viewport = self._page.viewport_size or {"width": 1320, "height": 860}
        width = float(viewport["width"])
        height = float(viewport["height"])

        for selector in selectors:
            try:
                loc = self._page.locator(selector)
                count = min(loc.count(), max_scan_per_selector)
            except Exception:
                continue

            for idx in range(count):
                try:
                    item = loc.nth(idx)
                    if not item.is_visible():
                        continue
                    box = item.bounding_box()
                    if box is None:
                        continue
                except Exception:
                    continue

                cx = box["x"] + box["width"] * 0.5
                cy = box["y"] + box["height"] * 0.5
                if (x1 * width) <= cx <= (x2 * width) and (y1 * height) <= cy <= (y2 * height):
                    return item
        return None

    def _visible_any_in_region(
        self,
        selectors: tuple[str, ...],
        x1: float,
        x2: float,
        y1: float,
        y2: float,
        max_scan_per_selector: int = 6,
    ) -> bool:
        viewport = self._page.viewport_size or {"width": 1320, "height": 860}
        width = float(viewport["width"])
        height = float(viewport["height"])

        for selector in selectors:
            try:
                loc = self._page.locator(selector)
                count = min(loc.count(), max_scan_per_selector)
            except Exception:
                continue

            for idx in range(count):
                try:
                    item = loc.nth(idx)
                    if not item.is_visible():
                        continue
                    box = item.bounding_box()
                    if box is None:
                        continue
                except Exception:
                    continue

                cx = box["x"] + box["width"] * 0.5
                cy = box["y"] + box["height"] * 0.5
                if (x1 * width) <= cx <= (x2 * width) and (y1 * height) <= cy <= (y2 * height):
                    return True
        return False

    def _ensure_recommend_feed(self) -> bool:
        for selector in RECOMMEND_SELECTORS:
            try:
                locator = self._page.locator(selector).first
                if not locator.is_visible():
                    continue
                locator.click(timeout=2200)
                self._sleep(1600)
                return True
            except Exception:
                continue
        return False

    def _focus_feed_surface(self) -> None:
        try:
            self._page.evaluate(
                """
                () => {
                  const body = document.body;
                  if (body && typeof body.focus === 'function') {
                    body.focus();
                  }
                }
                """
            )
        except Exception:
            pass

    def _open_share_panel(self) -> tuple[bool, str]:
        share_btn = self._first_visible_in_region(
            SHARE_BUTTON_SELECTORS,
            x1=0.74,
            x2=1.0,
            y1=0.18,
            y2=0.98,
            max_scan_per_selector=10,
        )
        if share_btn is None:
            share_btn = self._first_visible(SHARE_BUTTON_SELECTORS)
        if share_btn is None:
            return False, "share_button_not_found"

        if not self._click_locator_safe(share_btn, timeout=1800):
            return False, "share_click_failed"
        self._sleep(800)
        return True, "share_panel_opened"

    def _click_first_visible(self, selectors: tuple[str, ...], timeout: int = 1600) -> bool:
        locator = self._first_visible(selectors)
        if locator is None:
            return False
        return self._click_locator_safe(locator, timeout=timeout)

    def _fill_share_search(self, target: str) -> None:
        locator = self._first_visible_in_region(
            SHARE_SEARCH_INPUT_SELECTORS,
            x1=0.62,
            x2=1.0,
            y1=0.10,
            y2=0.90,
            max_scan_per_selector=8,
        )
        if locator is None:
            return
        try:
            locator.click(timeout=1200)
            locator.fill("")
            locator.type(target, delay=18)
            try:
                self._page.keyboard.press("Enter")
            except Exception:
                pass
            self._sleep(550)
        except Exception:
            pass

    def _find_share_target(self, target: str) -> Any | None:
        # Real-site interaction (user confirmed): after searching, the first
        # visible "分享" button in the result list is the correct target.
        del target
        viewport = self._page.viewport_size or {"width": 1320, "height": 860}
        width = float(viewport["width"])
        height = float(viewport["height"])
        min_x = 0.55 * width
        max_x = 0.98 * width
        min_y = 0.18 * height
        max_y = 0.95 * height

        def _collect(
            selector: str,
            max_scan: int,
            min_width: float,
            min_height: float,
        ) -> list[tuple[float, float, Any]]:
            items: list[tuple[float, float, Any]] = []
            try:
                loc = self._page.locator(selector)
                count = min(loc.count(), max_scan)
            except Exception:
                return items
            for idx in range(count):
                try:
                    node = loc.nth(idx)
                    if not node.is_visible():
                        continue
                    box = node.bounding_box()
                    if box is None:
                        continue
                    cx = box["x"] + box["width"] * 0.5
                    cy = box["y"] + box["height"] * 0.5
                    if cx < min_x or cx > max_x or cy < min_y or cy > max_y:
                        continue
                    if box["width"] < min_width or box["height"] < min_height:
                        continue
                    items.append((cy, cx, node))
                except Exception:
                    continue
            return items

        candidates = _collect("button:has-text('分享')", 80, 40.0, 20.0)
        if not candidates:
            candidates = _collect("[role='button']:has-text('分享')", 80, 40.0, 20.0)
        if not candidates:
            candidates = _collect("text=分享", 120, 6.0, 6.0)
        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]
        return None

    def _click_share_whisper_if_present(self) -> bool:
        locator = self._first_visible_in_region(
            SHARE_WHISPER_SELECTORS,
            x1=0.55,
            x2=1.0,
            y1=0.16,
            y2=0.96,
            max_scan_per_selector=12,
        )
        if locator is None:
            locator = self._first_visible(SHARE_WHISPER_SELECTORS)
        if locator is None:
            return False
        clicked = self._click_locator_safe(locator, timeout=1800)
        if clicked:
            self._sleep(450)
        return clicked

    def _close_private_chat_if_open(self) -> None:
        if not self._visible_any(PRIVATE_CHAT_HINT_SELECTORS):
            return
        for _ in range(3):
            locator = self._first_visible_in_region(
                PRIVATE_CHAT_CLOSE_SELECTORS,
                x1=0.70,
                x2=1.0,
                y1=0.00,
                y2=0.20,
                max_scan_per_selector=18,
            )
            if locator is None:
                locator = self._first_visible(PRIVATE_CHAT_CLOSE_SELECTORS)
            if locator is not None and self._click_locator_safe(locator, timeout=1500):
                self._sleep(420)
            else:
                try:
                    self._page.keyboard.press("Escape")
                except Exception:
                    pass
                self._sleep(280)

            if not self._visible_any(PRIVATE_CHAT_HINT_SELECTORS):
                return

    def _close_post_share_views(self) -> None:
        self._close_share_panel_if_open()
        self._close_private_chat_if_open()
        # Ensure we are back on feed after closing message overlays.
        self._ensure_recommend_feed()

    def _fill_share_message(self, message: str) -> bool:
        if not message.strip():
            return False
        locator = self._first_visible_in_region(
            SHARE_MESSAGE_INPUT_SELECTORS,
            x1=0.20,
            x2=1.0,
            y1=0.60,
            y2=0.99,
            max_scan_per_selector=14,
        )
        if locator is None:
            locator = self._first_visible(SHARE_MESSAGE_INPUT_SELECTORS)
        if locator is None:
            return False
        try:
            locator.click(timeout=1200)
            tag_name = locator.evaluate("el => (el.tagName || '').toLowerCase()")
            if tag_name in {"textarea", "input"}:
                locator.fill(message)
            else:
                self._page.keyboard.press("Meta+A")
                self._page.keyboard.type(message, delay=20)
            return True
        except Exception:
            return False

    def _send_share_message(self) -> bool:
        sent = False
        try:
            self._page.keyboard.press("Enter")
            sent = True
        except Exception:
            sent = False

        send_btn = self._first_visible_in_region(
            SHARE_MESSAGE_SEND_SELECTORS,
            x1=0.68,
            x2=1.0,
            y1=0.66,
            y2=0.99,
            max_scan_per_selector=16,
        )
        if send_btn is not None and self._click_locator_safe(send_btn, timeout=1600):
            sent = True
        return sent

    def _close_share_panel_if_open(self) -> None:
        # Keep it lean: use Escape to dismiss overlays.
        if not self._visible_any(SHARE_PANEL_HINT_SELECTORS):
            return
        for _ in range(2):
            try:
                self._page.keyboard.press("Escape")
            except Exception:
                continue
            self._sleep(300)
            if not self._visible_any(SHARE_PANEL_HINT_SELECTORS):
                return

    def _feed_signature(self) -> str:
        text = self._safe_body_text(max_len=2400)
        if not text:
            return ""

        head = text[:260]
        tail = text[-260:] if len(text) > 260 else text
        mid_start = max(0, (len(text) // 2) - 130)
        mid = text[mid_start : mid_start + 260]
        return f"{head}|{mid}|{tail}"

    def _advance_once(self) -> None:
        # User-provided site behavior: next item uses ArrowDown.
        try:
            self._page.keyboard.press("ArrowDown")
        except Exception:
            pass

    def _open_comment_panel(self) -> None:
        # User-provided site behavior: X opens the comment drawer.
        for key in ("x", "X", "x"):
            self._blur_active_editor()
            self._focus_feed_surface()
            try:
                self._page.keyboard.press(key)
                self._sleep(780)
                if self._is_comment_panel_open():
                    return
            except Exception:
                continue

    def _open_comment_panel_via_button(self) -> bool:
        locator = self._first_visible_in_region(
            COMMENT_OPEN_BUTTON_SELECTORS,
            x1=0.70,
            x2=1.0,
            y1=0.12,
            y2=0.98,
            max_scan_per_selector=12,
        )
        if locator is None:
            locator = self._first_visible(COMMENT_OPEN_BUTTON_SELECTORS)
        if locator is None:
            return False
        if not self._click_locator_safe(locator, timeout=1700):
            return False
        self._sleep(650)
        return self._is_comment_panel_open()

    def _first_visible(self, selectors: tuple[str, ...]) -> Any | None:
        for selector in selectors:
            try:
                loc = self._page.locator(selector).first
                if loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    def _safe_body_text(self, max_len: int = 2000) -> str:
        try:
            text = self._page.locator("body").inner_text(timeout=2500)
        except Exception:
            try:
                text = self._page.content()
            except Exception:
                text = ""
        normalized = " ".join(text.split())
        return normalized[:max_len]

    def _blur_active_editor(self) -> None:
        try:
            self._page.evaluate(
                """
                () => {
                  const el = document.activeElement;
                  if (!el) return;
                  const tag = (el.tagName || '').toLowerCase();
                  const editable =
                    tag === 'textarea' ||
                    tag === 'input' ||
                    el.isContentEditable === true;
                  if (editable && typeof el.blur === 'function') {
                    el.blur();
                  }
                  if (document.body && typeof document.body.focus === 'function') {
                    document.body.focus();
                  }
                }
                """
            )
        except Exception:
            pass

    def _is_comment_panel_open(self) -> bool:
        has_strong = self._visible_any_in_region(
            COMMENT_PANEL_STRONG_SELECTORS,
            x1=0.54,
            x2=1.0,
            y1=0.04,
            y2=0.98,
            max_scan_per_selector=8,
        )
        if has_strong:
            return True

        has_items = self._visible_any_in_region(
            COMMENT_PANEL_ITEM_SELECTORS,
            x1=0.54,
            x2=1.0,
            y1=0.12,
            y2=0.98,
            max_scan_per_selector=10,
        )
        has_header = self._visible_any_in_region(
            COMMENT_PANEL_HEADER_SELECTORS,
            x1=0.54,
            x2=1.0,
            y1=0.02,
            y2=0.32,
            max_scan_per_selector=5,
        )
        if has_header and has_items:
            return True
        return False

    def _is_closed_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return "target page, context or browser has been closed" in text

    def _recover_feed_context(self) -> None:
        print("[recover] page closed, relaunching browser context...")
        self.close()
        self.open_home()

    def _ensure_not_in_live_room(self) -> None:
        return

    def _sleep(self, base_ms: int) -> None:
        scaled = max(80, int(base_ms * self.wait_scale))
        self._page.wait_for_timeout(scaled)

    def _wait_for_page_stable(self) -> None:
        states: tuple[tuple[str, int], ...] = (
            ("domcontentloaded", 4000),
            ("load", 6000),
            ("networkidle", 4500),
        )
        for state, base_timeout in states:
            try:
                self._page.wait_for_load_state(
                    state,
                    timeout=max(1200, int(base_timeout * self.wait_scale)),
                )
            except Exception:
                continue

    def _sleep_raw_seconds(self, seconds: float) -> None:
        ms = max(80, int(seconds * 1000))
        self._page.wait_for_timeout(ms)

    def _collect_dom_markers(self, dom_text: str) -> list[str]:
        markers: list[str] = []
        lowered = dom_text.lower()

        # Strong live-room hints from UI badge/text.
        if "直播中" in dom_text or "进入直播间" in dom_text:
            markers.append("live_badge")
        elif any(token in dom_text for token in LIVE_TEXT_HINTS):
            markers.append("live_room")
        if any(token in dom_text for token in SHORT_VIDEO_TEXT_HINTS):
            markers.append("comment_button")

        selector_map: tuple[tuple[str, str], ...] = (
            ("live_badge", "text=直播中"),
            ("gift_panel", "text=礼物"),
            ("online_count", "text=在线"),
            ("comment_button", "text=评论"),
            ("like_button", "text=点赞"),
            ("share_button", "text=转发"),
        )
        for marker, selector in selector_map:
            try:
                if self._page.locator(selector).first.is_visible():
                    markers.append(marker)
            except Exception:
                continue

        if "liveroom" in lowered or "live-room" in lowered:
            markers.append("live_room")

        # De-duplicate while keeping order.
        result: list[str] = []
        seen: set[str] = set()
        for marker in markers:
            if marker not in seen:
                seen.add(marker)
                result.append(marker)
        return result

    def _extract_video_id(self, url: str) -> str:
        for pattern in (r"/video/(\d+)", r"modal_id=(\d+)"):
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"unknown-{stamp}"

    def _save_screenshot(self, tag: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{stamp}_{tag}.jpg"
        out = Path(self.screenshot_dir) / filename
        self._page.screenshot(path=str(out), full_page=False, type="jpeg", quality=65)
        return out
