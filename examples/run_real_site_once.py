from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
from urllib import error as urlerror
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from douyin_agent import (
    CommentGenerator,
    CommentPolicyEngine,
    ContentClassifier,
    DouyinWorkflowRunner,
    PolicyConfig,
    RunnerConfig,
    SemanticSummary,
)
from douyin_agent.browser_playwright import PlaywrightBrowserAdapter
from douyin_agent.models import ContentSnapshot


class RuntimeLogWindow:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = False
        self._proc: subprocess.Popen[str] | None = None
        if not enabled:
            return

        script = r"""
import queue
import sys
import threading
try:
    import tkinter as tk
    from tkinter.scrolledtext import ScrolledText
except Exception:
    sys.exit(1)

q = queue.Queue()
def _reader():
    for line in sys.stdin:
        q.put(line.rstrip("\n"))
    q.put(None)
threading.Thread(target=_reader, daemon=True).start()

root = tk.Tk()
root.title("Douyin Runtime Logs")
root.geometry("960x560")
text = ScrolledText(root, wrap=tk.WORD, font=("Menlo", 12))
text.pack(fill=tk.BOTH, expand=True)
text.insert(tk.END, "[log-window] 已启动\n")
text.see(tk.END)

def _poll():
    while True:
        try:
            item = q.get_nowait()
        except queue.Empty:
            break
        if item is None:
            root.destroy()
            return
        try:
            text.insert(tk.END, item + "\n")
            text.see(tk.END)
        except Exception:
            pass
    root.after(120, _poll)
_poll()
root.mainloop()
"""
        try:
            self._proc = subprocess.Popen(
                [sys.executable, "-u", "-c", script],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self.enabled = self._proc.poll() is None and self._proc.stdin is not None
        except Exception:
            self.enabled = False
            self._proc = None

    def append(self, line: str) -> None:
        if not self.enabled or self._proc is None or self._proc.stdin is None:
            return
        try:
            self._proc.stdin.write(line + "\n")
            self._proc.stdin.flush()
        except Exception:
            self.enabled = False

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin is not None:
                self._proc.stdin.close()
        except Exception:
            pass
        try:
            if self._proc.poll() is None:
                self._proc.terminate()
        except Exception:
            pass

TOPIC_HINTS = (
    ("美食", "美食分享"),
    ("探店", "探店体验"),
    ("旅行", "旅行记录"),
    ("健身", "健身训练"),
    ("穿搭", "穿搭分享"),
    ("数码", "数码测评"),
    ("汽车", "汽车内容"),
    ("宠物", "宠物日常"),
    ("教程", "实用教程"),
)

SENSITIVE_HINTS = (
    "医疗",
    "药",
    "投资",
    "彩票",
    "赌博",
    "返现",
)

UI_NOISE_TOKENS = {
    "直播中",
    "进入直播间",
    "点击或按",
    "评论",
    "点赞",
    "转发",
    "收藏",
    "关注",
    "首页",
    "推荐",
    "同城",
    "消息",
    "我",
    "发送",
    "登录",
    "抖音",
    "作品",
    "直播",
    "开启读屏标签",
    "读屏标签已关闭",
    "自动连播",
    "连播",
    "已关闭",
    "已开启",
    "开启",
    "关闭",
    "标签",
    "读屏",
    "设置",
    "反馈",
    "投诉",
    "分享",
    "精选",
    "搜索",
    "发现",
    "更多",
    "相关",
}

UI_NOISE_PARTS = (
    "读屏",
    "标签",
    "连播",
    "已关闭",
    "已开启",
    "点击",
    "进入",
    "直播间",
    "评论区",
    "发送",
    "关注",
    "登录",
    "抖音",
    "精选",
    "搜索",
    "发现",
    "推荐",
    "首页",
)

LIKE_COUNT_LABELS = ("点赞", "喜欢")
SHARE_COUNT_LABELS = ("分享", "转发")

AD_HINT_TERMS = (
    "广告",
    "推广",
    "促销",
    "优惠",
    "折扣",
    "低至",
    "仅需",
    "新客",
    "下单",
    "购买",
    "领券",
    "旗舰",
    "官网",
    "同款",
    "活动",
    "体验",
    "开工活动",
)

HANDLE_PATTERNS = (
    r"@([A-Za-z0-9_\u4e00-\u9fff]{2,20})",
    r"抖音号[:：]?\s*([A-Za-z0-9_]{4,24})",
    r"用户[0-9]{3,}",
)

STRONG_SENSITIVE_PATTERNS = (
    r"赌博",
    r"彩票",
    r"返现",
    r"刷单",
    r"稳赚",
    r"带你赚钱",
    r"私信.*赚钱",
    r"投资建议",
)

CONTENT_NOISE_PARTS = (
    "评论",
    "点赞",
    "收藏",
    "转发",
    "关注",
    "发送",
    "发布评论",
    "全部评论",
    "最新评论",
    "直播中",
    "进入直播间",
    "点击或按",
    "推荐",
    "首页",
    "同城",
    "消息",
    "搜索",
    "发现",
    "登录",
    "抖音",
    "福袋",
    "音浪",
    "在线",
)

def _clean_video_context_texts(raw_texts: tuple[str, ...], limit: int = 10) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in raw_texts:
        text = " ".join(raw.split()).strip()
        if len(text) < 2:
            continue
        if len(text) > 120:
            continue
        if text in UI_NOISE_TOKENS:
            continue
        if any(part in text for part in CONTENT_NOISE_PARTS):
            continue
        if re.fullmatch(r"@?[A-Za-z0-9_]{2,24}", text):
            continue
        if re.fullmatch(r"用户[0-9]{3,}", text):
            continue
        if text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return tuple(cleaned)


def _fallback_context_from_snapshot(dom_text: str, limit: int = 8) -> tuple[str, ...]:
    tags = [item.strip() for item in re.findall(r"#([^\s#]{2,20})", dom_text)]
    cleaned: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag in UI_NOISE_TOKENS:
            continue
        if any(part in tag for part in CONTENT_NOISE_PARTS):
            continue
        if tag in seen:
            continue
        seen.add(tag)
        cleaned.append(tag)
        if len(cleaned) >= limit:
            break
    return tuple(cleaned)


@dataclass(frozen=True)
class VideoProfileTriplet:
    themes: tuple[str, str, str]
    types: tuple[str, str, str]
    styles: tuple[str, str, str]
    source: str
    share_score: int
    humor_score: int
    funny_score: int
    parody_score: int
    nonsense_score: int
    abstract_score: int
    worth_share: bool
    share_level: str
    share_reason: str


def _empty_ai_profile() -> VideoProfileTriplet:
    return VideoProfileTriplet(
        themes=("AI未识别主题", "待补充", "待补充"),
        types=("AI未识别类型", "待补充", "待补充"),
        styles=("AI未识别风格", "待补充", "待补充"),
        source="ai_unavailable",
        share_score=0,
        humor_score=0,
        funny_score=0,
        parody_score=0,
        nonsense_score=0,
        abstract_score=0,
        worth_share=False,
        share_level="不建议分享",
        share_reason="AI分析不可用，默认不建议分享",
    )


def _normalize_top3(items: list[str], fallback: tuple[str, str, str]) -> tuple[str, str, str]:
    picked: list[str] = []
    seen: set[str] = set()
    for raw in items:
        token = " ".join(str(raw).split()).strip("，。！？、:：;；\"'“”‘’()（）[]【】")
        if len(token) < 2:
            continue
        if token in UI_NOISE_TOKENS:
            continue
        if any(part in token for part in CONTENT_NOISE_PARTS):
            continue
        if token in seen:
            continue
        seen.add(token)
        picked.append(token[:14])
        if len(picked) >= 3:
            return tuple(picked)  # type: ignore[return-value]
    for item in fallback:
        if item in seen:
            continue
        seen.add(item)
        picked.append(item)
        if len(picked) >= 3:
            break
    while len(picked) < 3:
        picked.append(fallback[min(len(picked), len(fallback) - 1)])
    return tuple(picked[:3])  # type: ignore[return-value]


def _to_int_in_range(value: object, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(float(str(value).strip()))
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


def _parse_human_count(token: str) -> int | None:
    cleaned = token.strip().replace(",", "").replace("，", "")
    match = re.match(r"^(\d+(?:\.\d+)?)(万|亿|[wWkKmM千])?$", cleaned)
    if match is None:
        return None
    num = float(match.group(1))
    unit = (match.group(2) or "").lower()
    multiplier = 1.0
    if unit in {"万", "w"}:
        multiplier = 10_000.0
    elif unit in {"亿"}:
        multiplier = 100_000_000.0
    elif unit in {"千", "k"}:
        multiplier = 1_000.0
    elif unit in {"m"}:
        multiplier = 1_000_000.0
    return int(num * multiplier)


def _extract_metric_count(text: str, labels: tuple[str, ...]) -> int:
    normalized = " ".join(text.split())
    candidates: list[int] = []
    number_pat = r"(\d+(?:\.\d+)?\s*(?:万|亿|[wWkKmM千])?)"

    for label in labels:
        patterns = (
            rf"{label}\s*[:：]?\s*{number_pat}",
            rf"{number_pat}\s*{label}",
            rf"{number_pat}\s*次\s*{label}",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, normalized):
                token = "".join(match.group(1).split())
                parsed = _parse_human_count(token)
                if parsed is not None:
                    candidates.append(parsed)

    return max(candidates) if candidates else 0


def _should_share_by_engagement(share_count: int, like_count: int) -> tuple[bool, float]:
    ratio = (share_count / like_count) if like_count > 0 else 0.0
    if like_count < 1_000:
        return False, ratio
    should_share = (share_count > 200_000) or (ratio > 0.5)
    return should_share, ratio


def _detect_ad_video(text: str, profile: VideoProfileTriplet) -> tuple[bool, str]:
    del profile  # Reserved for compatibility; ad decision now uses explicit badge-like text only.
    normalized = " ".join(text.split())
    handle_ad = re.search(r"@[^\s@]{1,40}\s*广告", normalized) is not None
    return handle_ad, f"handle_ad={handle_ad};rule=@name+广告"


def _extract_ranked_engagement_counts(metric_texts: tuple[str, ...]) -> tuple[int, int]:
    # User-confirmed UI mapping on right action rail:
    # 1st number -> like count; 4th number -> share count.
    # Some pages expose each metric twice in DOM (a,a,b,b,c,c,d,d), so we
    # evaluate a few candidate sequences and choose the first valid one.
    cleaned = tuple("".join(str(token).split()) for token in metric_texts if str(token).strip())
    if not cleaned:
        return 0, 0

    collapsed_adjacent: list[str] = []
    for token in cleaned:
        if collapsed_adjacent and collapsed_adjacent[-1] == token:
            continue
        collapsed_adjacent.append(token)

    even_picks = [cleaned[idx] for idx in range(0, len(cleaned), 2)]
    candidates = (
        tuple(collapsed_adjacent),
        tuple(even_picks),
        cleaned,
    )

    for seq in candidates:
        if len(seq) < 4:
            continue
        like_count = _parse_human_count(seq[0]) or 0
        share_count = _parse_human_count(seq[3]) or 0
        if like_count > 0 or share_count > 0:
            return like_count, share_count

    like_count = _parse_human_count(cleaned[0]) or 0
    share_count = _parse_human_count(cleaned[3]) or 0 if len(cleaned) >= 4 else 0
    return like_count, share_count


def _normalize_mention_target(raw: str) -> str:
    cleaned = " ".join(raw.split()).strip()
    cleaned = cleaned.lstrip("@").strip()
    return cleaned


def _parse_mention_targets(raw: str) -> tuple[str, ...]:
    text = " ".join(raw.split()).strip()
    if not text:
        return ()

    chunks: list[str]
    if "@" in text:
        chunks = [
            item.strip()
            for item in re.findall(r"@([A-Za-z0-9_\u4e00-\u9fff·・-]{1,32})", text)
            if item.strip()
        ]
    else:
        chunks = [item for item in re.split(r"[\s,，]+", text) if item]

    targets: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        target = _normalize_mention_target(chunk)
        if not target:
            continue
        if target in seen:
            continue
        seen.add(target)
        targets.append(target)
    return tuple(targets)


def _compose_mention_comment(base_comment: str, mention_targets: tuple[str, ...]) -> str:
    body = " ".join(base_comment.split()).strip()
    targets = tuple(
        target
        for target in (_normalize_mention_target(item) for item in mention_targets)
        if target
    )
    if not targets:
        return body
    prefix = " ".join(f"@{target}" for target in targets)
    if body:
        return f"{prefix} {body}"
    return f"{prefix} 这条值得看"


def _share_level_from_score(score: int) -> str:
    if score >= 85:
        return "强烈推荐分享"
    if score >= 72:
        return "值得分享"
    if score >= 60:
        return "可考虑分享"
    return "不建议分享"


def _worth_share_by_composite(
    humor_score: int,
    funny_score: int,
    parody_score: int,
    nonsense_score: int,
    abstract_score: int,
) -> bool:
    scores = (
        humor_score,
        funny_score,
        parody_score,
        nonsense_score,
        abstract_score,
    )
    avg_score = sum(scores) / 5.0
    high_dims = sum(1 for score in scores if score >= 14)
    core_fun = (humor_score + funny_score) / 2.0

    weighted = (
        humor_score * 0.26
        + funny_score * 0.24
        + parody_score * 0.20
        + nonsense_score * 0.15
        + abstract_score * 0.15
    )
    weighted_100 = (weighted / 20.0) * 100.0

    return (
        (weighted_100 >= 72 and high_dims >= 2)
        or (avg_score >= 12.5 and core_fun >= 12 and high_dims >= 1)
    )


class HeuristicVision:
    def understand(self, snapshot: ContentSnapshot) -> SemanticSummary:
        merged = " ".join([snapshot.dom_text, *snapshot.frame_texts])
        keywords = self._extract_keywords(merged)
        topic = self._guess_topic(merged, keywords)
        objects = self._guess_objects(merged, keywords)
        tone = self._guess_tone(merged)
        sensitive_flag = self._is_sensitive(merged)
        return SemanticSummary(
            topic=topic,
            objects=objects,
            tone=tone,
            sensitive_flag=sensitive_flag,
            ocr_snippets=snapshot.frame_texts,
        )

    def _guess_topic(self, text: str, keywords: tuple[str, ...]) -> str:
        for key, topic in TOPIC_HINTS:
            if key in text:
                return topic
        if keywords:
            if len(keywords) >= 2:
                return f"{keywords[0]}与{keywords[1]}"
            return keywords[0]
        normalized = " ".join(text.split())
        return normalized[:10] if normalized else "短视频内容"

    def _guess_objects(self, text: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for key, _topic in TOPIC_HINTS:
            if key in text and key not in result:
                result.append(key)
            if len(result) >= 2:
                break
        if len(result) < 2:
            for kw in keywords:
                if kw not in result:
                    result.append(kw)
                if len(result) >= 2:
                    break
        return tuple(result)

    def _guess_tone(self, text: str) -> str:
        positive = ("教程", "干货", "学到了", "推荐", "分享")
        critical = ("避雷", "别买", "翻车", "问题", "争议")
        if any(t in text for t in positive):
            return "positive"
        if any(t in text for t in critical):
            return "critical"
        return "neutral"

    def _extract_keywords(self, text: str) -> tuple[str, ...]:
        handle_names = self._extract_handle_names(text)

        # Prefer hashtag topics first (often closer to video content).
        raw: list[str] = []
        for tag in re.findall(r"#([^\s#]{2,20})", text):
            raw.append(tag.strip())

        # Then keep contiguous Chinese chunks and filter UI noise/generic words.
        raw.extend(re.findall(r"[\u4e00-\u9fff]{2,8}", text))
        filtered: list[str] = []
        seen: set[str] = set()
        for token in raw:
            token = token.strip("，。！？、:：;；\"'“”‘’()（）[]【】")
            if not token:
                continue
            if token in UI_NOISE_TOKENS:
                continue
            if any(part in token for part in UI_NOISE_PARTS):
                continue
            if self._looks_like_handle(token, handle_names):
                continue
            if token.startswith("点击或按") or token.endswith("直播间"):
                continue
            if token in seen:
                continue
            seen.add(token)
            filtered.append(token)
            if len(filtered) >= 6:
                break
        return tuple(filtered)

    def _is_sensitive(self, text: str) -> bool:
        # Use stronger phrases to reduce false positives.
        for pattern in STRONG_SENSITIVE_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    def _extract_handle_names(self, text: str) -> tuple[str, ...]:
        names: list[str] = []
        seen: set[str] = set()
        for pattern in HANDLE_PATTERNS:
            for match in re.findall(pattern, text):
                candidate = match.strip()
                if not candidate:
                    continue
                if candidate in seen:
                    continue
                seen.add(candidate)
                names.append(candidate)
        return tuple(names)

    def _looks_like_handle(self, token: str, handles: tuple[str, ...]) -> bool:
        if not handles:
            return False
        for name in handles:
            if token == name:
                return True
            if token in name:
                return True
        return False


@dataclass
class AICommentClient:
    enabled: bool = False
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini"
    api_key_env: str = "OPENAI_API_KEY"
    style: str = "humorous"
    timeout_seconds: float = 20.0
    temperature: float = 0.7
    max_len: int = 38
    insecure_skip_verify: bool = False
    debug: bool = False

    def generate(
        self,
        summary: SemanticSummary,
        content_excerpt: str,
        reference_comments: tuple[str, ...] = (),
        recent_generated_comments: tuple[str, ...] = (),
    ) -> str | None:
        if not self.enabled:
            return None

        api_key = os.getenv(self.api_key_env, "").strip()
        if not api_key:
            return None

        recent = tuple(comment for comment in recent_generated_comments if comment.strip())[:6]
        recent_block = "\n".join(f"- {comment}" for comment in recent) if recent else "无"
        comment_reference_hint = self._build_comment_reference_hint(
            reference_comments=reference_comments,
            content_excerpt=content_excerpt,
        )
        style_hint = (
            "风格要更颠、更毒舌：离谱比喻+一本正经胡说八道+轻微阴阳怪气。"
            "可以锐评吐槽，但不要人身攻击、低俗辱骂。"
            if self.style == "humorous"
            else "风格自然稳妥，简洁有礼。"
        )
        prompt = (
            "请生成一条中文短视频评论。\n"
            "要求：\n"
            "- 只输出评论正文，不要解释。\n"
            "- 语气自然，贴合内容，不要空话。\n"
            f"- 长度 8 到 {self.max_len} 字。\n"
            "- 必须避开近期评论的措辞和句式，换一个新角度。\n"
            "- 幽默模式下优先使用：反差梗、拟人、离谱比喻、一本正经胡说八道。\n"
            "- 允许毒舌吐槽，但只吐槽现象/情节/设定，不攻击真人身份、外貌、地域。\n"
            "- 评论区内容仅用于语气参考，禁止复述评论原句。\n"
            "- 评论必须和视频主题有关，至少点到一个主题或关键点。\n"
            "- 不要出现引流、私信、交易、赌博、投资建议。\n\n"
            f"{style_hint}\n"
            f"主题: {summary.topic}\n"
            f"关键点: {'、'.join(summary.objects) if summary.objects else '无'}\n"
            f"语气: {summary.tone}\n"
            f"内容片段: {content_excerpt[:260]}\n"
            f"评论区参考(弱约束): {comment_reference_hint}\n"
            f"近期已生成评论(避免复用):\n{recent_block}\n"
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是短视频评论助手。你擅长毒舌搞怪风：离谱但贴题，短句高梗密度。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": max(self.temperature, 1.08)
            if self.style == "humorous"
            else self.temperature,
        }

        url = self.api_base.rstrip("/") + "/chat/completions"
        req = urlrequest.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        context = None
        if self.insecure_skip_verify:
            context = ssl._create_unverified_context()

        try:
            with urlrequest.urlopen(req, timeout=self.timeout_seconds, context=context) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
        except (urlerror.URLError, TimeoutError) as exc:
            if self.debug:
                print(f"[ai] request failed: {type(exc).__name__}: {exc}")
            return None
        except Exception as exc:
            if self.debug:
                print(f"[ai] request failed: {type(exc).__name__}: {exc}")
            return None

        try:
            data = json.loads(body)
            text = data["choices"][0]["message"]["content"]
        except Exception:
            return None

        cleaned = " ".join(str(text).split()).strip().strip('"“”')
        if not cleaned:
            return None
        if len(cleaned) > self.max_len:
            cleaned = cleaned[: self.max_len]
        if self._too_similar_to_recent(cleaned, recent):
            if self.debug:
                print("[ai] generated comment too similar to recent ones, fallback")
            return None
        return cleaned

    def analyze_video_profile(
        self,
        content_excerpt: str,
        reference_comments: tuple[str, ...] = (),
    ) -> VideoProfileTriplet | None:
        if not self.enabled:
            return None
        api_key = os.getenv(self.api_key_env, "").strip()
        if not api_key:
            return None

        refs = "\n".join(reference_comments[:12]) if reference_comments else "无"
        prompt = (
            "你是短视频内容分析器。请结合视频标题/小标题/描述和评论区语境，输出最贴合的三元信息。\n"
            "返回 JSON，且必须是单个 JSON 对象，不要输出其他文字。\n"
            "字段格式：\n"
            '{"themes":["主题1","主题2","主题3"],'
            '"types":["类型1","类型2","类型3"],'
            '"styles":["风格1","风格2","风格3"],'
            '"share_score":88,'
            '"worth_share":true,'
            '"share_level":"值得分享",'
            '"share_reason":"一句简短理由",'
            '"style_scores":{"humor_score":16,"funny_score":15,"parody_score":14,"nonsense_score":13,"abstract_score":12}}\n'
            "规则：\n"
            "- 每个字段必须正好3项；词要短，2-10字。\n"
            "- 主题=内容话题；类型=内容品类；风格=表达方式/叙事气质。\n"
            "- 风格分五维(各0-20)：幽默(humor)、搞笑(funny)、恶搞(parody)、无厘头(nonsense)、抽象(abstract)。\n"
            "- share_score 为五维总分(0-100)。\n"
            "- worth_share 采用综合评判，不要求五维全部达标：看总分、亮点维度、整体传播感。\n"
            "- share_level 取值：强烈推荐分享/值得分享/可考虑分享/不建议分享。\n"
            "- share_reason 8-30字，说明推荐或不推荐分享的核心理由。\n"
            "- 评论区只做辅助，不要被评论带偏离视频内容。\n"
            f"视频文本:\n{content_excerpt[:900]}\n"
            f"评论区文本:\n{refs[:1200]}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你只输出合法JSON，不要输出解释。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
        }

        url = self.api_base.rstrip("/") + "/chat/completions"
        req = urlrequest.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        context = None
        if self.insecure_skip_verify:
            context = ssl._create_unverified_context()

        try:
            with urlrequest.urlopen(req, timeout=self.timeout_seconds, context=context) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
        except (urlerror.URLError, TimeoutError) as exc:
            if self.debug:
                print(f"[ai] profile analyze failed: {type(exc).__name__}: {exc}")
            return None
        except Exception as exc:
            if self.debug:
                print(f"[ai] profile analyze failed: {type(exc).__name__}: {exc}")
            return None

        try:
            data = json.loads(body)
            text = str(data["choices"][0]["message"]["content"])
        except Exception:
            return None

        parsed = self._parse_profile_json(text)
        if parsed is None:
            return None

        themes = _normalize_top3(
            list(parsed.get("themes", [])),
            ("内容主题", "视频主题", "热门话题"),
        )
        types = _normalize_top3(
            list(parsed.get("types", [])),
            ("短视频", "信息流内容", "泛娱乐"),
        )
        styles = _normalize_top3(
            list(parsed.get("styles", [])),
            ("口语化", "轻松", "节奏快"),
        )
        style_scores = parsed.get("style_scores", {})
        if not isinstance(style_scores, dict):
            style_scores = {}

        humor_score = _to_int_in_range(
            style_scores.get("humor_score", parsed.get("humor_score", 0)),
            0,
            20,
            0,
        )
        funny_score = _to_int_in_range(
            style_scores.get("funny_score", parsed.get("funny_score", 0)),
            0,
            20,
            0,
        )
        parody_score = _to_int_in_range(
            style_scores.get("parody_score", parsed.get("parody_score", 0)),
            0,
            20,
            0,
        )
        nonsense_score = _to_int_in_range(
            style_scores.get("nonsense_score", parsed.get("nonsense_score", 0)),
            0,
            20,
            0,
        )
        abstract_score = _to_int_in_range(
            style_scores.get("abstract_score", parsed.get("abstract_score", 0)),
            0,
            20,
            0,
        )
        score_sum = humor_score + funny_score + parody_score + nonsense_score + abstract_score
        # Keep scoring consistent and auditable:
        # share_score must always equal the sum of the 5 style dimensions.
        share_score = max(0, min(100, score_sum))

        worth_share = _worth_share_by_composite(
            humor_score=humor_score,
            funny_score=funny_score,
            parody_score=parody_score,
            nonsense_score=nonsense_score,
            abstract_score=abstract_score,
        )

        share_level = _share_level_from_score(share_score)
        if not worth_share and share_level in {"强烈推荐分享", "值得分享"}:
            share_level = "可考虑分享" if share_score >= 60 else "不建议分享"
        if worth_share and share_level == "不建议分享":
            share_level = "可考虑分享"

        share_reason = " ".join(str(parsed.get("share_reason", "")).split()).strip()
        if not share_reason:
            share_reason = (
                "综合评估笑点、抽象度和传播感较高，值得分享。"
                if worth_share
                else "综合评估传播性一般，建议先观望再决定分享。"
            )
        if len(share_reason) > 48:
            share_reason = share_reason[:48]

        return VideoProfileTriplet(
            themes=themes,
            types=types,
            styles=styles,
            source="ai",
            share_score=share_score,
            humor_score=humor_score,
            funny_score=funny_score,
            parody_score=parody_score,
            nonsense_score=nonsense_score,
            abstract_score=abstract_score,
            worth_share=worth_share,
            share_level=share_level,
            share_reason=share_reason,
        )

    def _parse_profile_json(self, text: str) -> dict[str, object] | None:
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
            candidate = re.sub(r"\s*```$", "", candidate)
            candidate = candidate.strip()

        parsed = None
        try:
            parsed = json.loads(candidate)
        except Exception:
            left = candidate.find("{")
            right = candidate.rfind("}")
            if left >= 0 and right > left:
                try:
                    parsed = json.loads(candidate[left : right + 1])
                except Exception:
                    parsed = None
        if not isinstance(parsed, dict):
            return None
        return parsed

    def _build_comment_reference_hint(
        self,
        reference_comments: tuple[str, ...],
        content_excerpt: str,
    ) -> str:
        if not reference_comments:
            return "无"

        merged = " ".join(reference_comments[:8])
        style_tags: list[str] = []
        if any(token in merged for token in ("哈哈", "笑死", "离谱", "绝了", "有梗")):
            style_tags.append("幽默")
        if any(token in merged for token in ("学到了", "收藏", "受教", "有用")):
            style_tags.append("干货向")
        if any(token in merged for token in ("同感", "真实", "共鸣", "太懂")):
            style_tags.append("共鸣向")
        if any(token in merged for token in ("？", "吗", "怎么", "为啥", "为什么")):
            style_tags.append("提问向")
        if not style_tags:
            style_tags.append("自然")

        excerpt_tokens = set(re.findall(r"[\u4e00-\u9fff]{2,6}", content_excerpt))
        related_tokens: list[str] = []
        seen_tokens: set[str] = set()
        for text in reference_comments[:8]:
            for token in re.findall(r"[\u4e00-\u9fff]{2,6}", text):
                if token in UI_NOISE_TOKENS:
                    continue
                if len(token) < 2:
                    continue
                if token not in excerpt_tokens:
                    continue
                if token in seen_tokens:
                    continue
                seen_tokens.add(token)
                related_tokens.append(token)
                if len(related_tokens) >= 4:
                    break
            if len(related_tokens) >= 4:
                break

        samples: list[str] = []
        for text in reference_comments[:2]:
            trimmed = " ".join(text.split()).strip()
            if not trimmed:
                continue
            samples.append(trimmed[:20])
        sample_text = " | ".join(samples) if samples else "无"
        token_text = "、".join(related_tokens) if related_tokens else "无"
        return f"语气={','.join(style_tags)}; 相关词={token_text}; 样本={sample_text}"

    def _too_similar_to_recent(
        self,
        comment: str,
        recent_generated_comments: tuple[str, ...],
        threshold: float = 0.84,
    ) -> bool:
        candidate = comment.strip()
        if not candidate:
            return False
        for old in recent_generated_comments:
            previous = old.strip()
            if not previous:
                continue
            if candidate == previous:
                return True
            ratio = SequenceMatcher(a=candidate, b=previous).ratio()
            if ratio >= threshold:
                return True
        return False


@dataclass
class ConsoleApprover:
    auto_yes: bool = False

    def approve(self, comment: str, snapshot: ContentSnapshot) -> bool:
        if self.auto_yes:
            print("[approve] auto_yes=true -> approved")
            return True

        print("\n[approve] 候选评论：", comment)
        print("[approve] URL:", snapshot.url)
        answer = input("[approve] 是否发送该评论？[y/N]: ").strip().lower()
        return answer in {"y", "yes"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one or more real-site workflow rounds.")
    parser.add_argument(
        "--mode",
        choices=("scan", "workflow"),
        default="scan",
        help="scan: classify+wait+next; workflow: full draft/policy workflow.",
    )
    parser.add_argument("--start-url", default="https://www.douyin.com/", help="Entry URL")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument(
        "--require-login",
        action="store_true",
        help="Require login state, otherwise run will return need_login",
    )
    parser.add_argument(
        "--enable-post",
        action="store_true",
        help="Actually send comment instead of dry-run",
    )
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Open page and only solve/check login state, then exit.",
    )
    parser.add_argument(
        "--login-timeout",
        type=int,
        default=180,
        help="Seconds to wait for manual login when --require-login is set.",
    )
    parser.add_argument(
        "--login-poll",
        type=float,
        default=2.0,
        help="Polling interval seconds while waiting for login.",
    )
    parser.add_argument(
        "--wait-scale",
        type=float,
        default=3.0,
        help="Global wait multiplier for slow networks (e.g., 2.5).",
    )
    parser.add_argument(
        "--live-wait-seconds",
        type=float,
        default=3.0,
        help="In scan mode, wait this long on live content before going next.",
    )
    parser.add_argument(
        "--video-wait-seconds",
        type=float,
        default=10.0,
        help="In scan mode, wait this long on non-live content after opening comments.",
    )
    parser.add_argument(
        "--post-next-settle-seconds",
        type=float,
        default=8.0,
        help="After ArrowDown, wait this many seconds before taking next snapshot.",
    )
    parser.add_argument(
        "--snapshot-settle-seconds",
        type=float,
        default=2.0,
        help="Wait before screenshot/snapshot capture.",
    )
    parser.add_argument(
        "--force-non-live",
        action="store_true",
        help="In scan mode, ignore live-hint and always test comment-open path.",
    )
    parser.add_argument(
        "--comment-by-content",
        action="store_true",
        help="In scan mode, generate content-based comment on non-live cards.",
    )
    parser.add_argument(
        "--comment-style",
        choices=("humorous", "neutral"),
        default="humorous",
        help="Comment style for AI generation.",
    )
    parser.add_argument(
        "--use-ai-comment",
        action="store_true",
        default=True,
        help="Use LLM API to generate comment text.",
    )
    parser.add_argument(
        "--no-ai-comment",
        action="store_false",
        dest="use_ai_comment",
        help="Disable AI comment generation (scan mode will skip comment generation).",
    )
    parser.add_argument(
        "--llm-api-base",
        default="https://api.openai.com/v1",
        help="LLM API base URL, OpenAI-compatible chat completions endpoint.",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4.1-mini",
        help="LLM model name used for AI comment generation.",
    )
    parser.add_argument(
        "--llm-api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable name containing API key.",
    )
    parser.add_argument(
        "--llm-insecure-skip-verify",
        action="store_true",
        default=True,
        help="Skip TLS certificate verification for LLM API requests (default: enabled).",
    )
    parser.add_argument(
        "--llm-verify",
        action="store_false",
        dest="llm_insecure_skip_verify",
        help="Enable TLS certificate verification for LLM API requests.",
    )
    parser.add_argument(
        "--llm-debug",
        action="store_true",
        help="Print AI request errors.",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Approve comment without prompt (still blocked by policy).",
    )
    parser.add_argument(
        "--auto-post",
        action="store_true",
        help="Skip manual approval state in workflow runner.",
    )
    parser.add_argument("--iterations", type=int, default=1, help="How many rounds to run")
    parser.add_argument("--profile-dir", default=".playwright_profile")
    parser.add_argument("--screenshots", default="artifacts/screenshots")
    parser.add_argument(
        "--scan-report-csv",
        default="",
        help="Deprecated and ignored: CSV report output is disabled.",
    )
    parser.add_argument(
        "--enable-share",
        action="store_true",
        help="In scan mode, perform real share action for videos that pass share-worth evaluation.",
    )
    parser.add_argument(
        "--share-all",
        action="store_true",
        help="In scan mode, share all non-live videos regardless of share-worth evaluation.",
    )
    parser.add_argument(
        "--share-target",
        default="",
        help="Share target name (friend or group), e.g. '3214抖音群'.",
    )
    parser.add_argument(
        "--comment-mention-friend",
        default="",
        help="When share condition is met, post comment mentioning friend(s), e.g. '@张三 @李四'.",
    )
    parser.add_argument(
        "--comment-without-share",
        action="store_true",
        help="Run comment workflow on share-qualified videos even when share action is disabled.",
    )
    parser.add_argument(
        "--share-strong-only",
        action="store_true",
        help="Deprecated: share decision now uses engagement metrics (share count / like count).",
    )
    parser.add_argument(
        "--no-log-window",
        action="store_true",
        help="Disable runtime GUI log window.",
    )
    return parser.parse_args()


def run_scan_mode(
    browser: PlaywrightBrowserAdapter,
    classifier: ContentClassifier,
    vision: HeuristicVision,
    iterations: int,
    live_wait_seconds: float,
    video_wait_seconds: float,
    force_non_live: bool,
    comment_by_content: bool,
    ai_client: AICommentClient,
    scan_report_csv: str = "",
    enable_share: bool = False,
    comment_without_share: bool = False,
    share_all: bool = False,
    share_target: str = "",
    comment_mention_friend: str = "",
    share_strong_only: bool = False,
    runtime_log: RuntimeLogWindow | None = None,
) -> int:
    if iterations <= 0:
        return 0

    browser.open_home()
    if not browser.ensure_login():
        print("[scan] login check failed")
        return 2

    if comment_by_content and not ai_client.enabled:
        print("[scan] AI comment generation disabled; local fallback removed, comments will be skipped.")

    mention_friend_values = _parse_mention_targets(comment_mention_friend)
    if mention_friend_values:
        mention_preview = " ".join(f"@{name}" for name in mention_friend_values)
        print(f"[scan] mention comment enabled for {mention_preview}")
        if not ai_client.enabled:
            print("[scan] mention mode requires AI comment; mention comment will be skipped when AI is disabled.")

    csv_file = None
    csv_writer: csv.DictWriter | None = None
    if scan_report_csv.strip():
        print("[scan] CSV output disabled by policy; ignoring --scan-report-csv")

    def _write_round_row(row: dict[str, object]) -> None:
        if csv_writer is None or csv_file is None:
            return
        csv_writer.writerow(row)
        csv_file.flush()

    def _emit_runtime_round_log(
        round_idx: int,
        profile: VideoProfileTriplet,
        ai_comment: str,
        share_result: str,
        share_detail: str,
        like_count: int,
        share_count: int,
        ratio: float,
        task_status: str,
    ) -> None:
        if runtime_log is None:
            return
        shared = share_result == "shared"
        if shared:
            reason = (
                f"满足规则(share>20w 或 share/like>0.5), "
                f"share={share_count}, like={like_count}, ratio={ratio:.3f}, detail={share_detail}"
            )
        else:
            if share_result == "skip_low_engagement":
                reason = f"未达规则: share={share_count}, like={like_count}, ratio={ratio:.3f}"
            elif task_status == "live_skipped":
                reason = "直播内容，跳过分享"
            elif share_result == "disabled":
                reason = "未启用分享"
            else:
                reason = share_detail if share_detail and share_detail != "-" else share_result

        line = (
            f"第{round_idx}轮 | AI评论: {ai_comment if ai_comment else '-'} | "
            f"是否分享: {'是' if shared else '否'} | 原因: {reason} | "
            f"主题: {' | '.join(profile.themes)} | "
            f"类型: {' | '.join(profile.types)} | "
            f"风格: {' | '.join(profile.styles)}"
        )
        runtime_log.append(line)

    recent_generated_comments: tuple[str, ...] = ()

    try:
        for idx in range(iterations):
            if idx == 0:
                # First-card guard: give the feed a little more time before first decision.
                browser.wait_seconds(1.2)

            round_start_panel_open = browser.is_comment_panel_open()
            round_start_panel_closed = True
            if round_start_panel_open:
                round_start_panel_closed = browser.close_comment_panel_if_open()
                if round_start_panel_closed:
                    # Let UI settle before extracting current card text.
                    browser.wait_seconds(0.2)

            snapshot = browser.current_snapshot()
            raw_context_texts = browser.get_current_video_context_texts(limit=20)
            focused_context_texts = _clean_video_context_texts(raw_context_texts, limit=10)
            if not focused_context_texts:
                focused_context_texts = _fallback_context_from_snapshot(snapshot.dom_text, limit=8)
            focused_excerpt = " ".join(focused_context_texts)

            classification = classifier.classify(snapshot)
            live_by_hint_raw = browser.has_live_room_hint()
            live_by_badge = "直播中" in snapshot.dom_text
            ad_badge = browser.has_ad_badge()
            live_by_hint = False if force_non_live else live_by_hint_raw

            profile = _empty_ai_profile()
            video_topic = profile.themes[0]
            video_objects = "、".join(profile.themes[1:3])
            comment_refs_count = 0

            print(
                "\n[round {}] classification={} confidence={:.2f} reasons={}".format(
                    idx + 1,
                    classification.kind,
                    classification.confidence,
                    classification.reasons,
                )
            )
            print(
                f"[round {idx + 1}] live_by_hint={live_by_hint}"
                f"{' (forced false)' if force_non_live else ''} raw={live_by_hint_raw} badge={live_by_badge}"
            )
            print(f"[round {idx + 1}] ad_badge={ad_badge}")
            print(
                f"[round {idx + 1}] start_panel_open={round_start_panel_open} "
                f"start_panel_closed={round_start_panel_closed}"
            )
            print(
                f"[round {idx + 1}] focused_context_count={len(focused_context_texts)} "
                f"context_preview={' / '.join(focused_context_texts[:2]) if focused_context_texts else '-'}"
            )
            print(
                f"[round {idx + 1}] profile_source={profile.source} "
                f"themes={' | '.join(profile.themes)} "
                f"types={' | '.join(profile.types)} "
                f"styles={' | '.join(profile.styles)} "
                f"share={profile.share_score}({profile.share_level}) "
                f"worth_share={profile.worth_share}"
            )

            panel_open_before = False
            pressed_x = False
            opened = False
            share_enabled_flag = enable_share
            share_triggered = False
            share_result = "disabled"
            share_detail = "-"
            shared_url = snapshot.url
            share_target_value = " ".join(share_target.split()).strip()
            share_message = ""
            share_message_seed = ""
            draft_comment = ""
            comment_result = "skip"
            comment_source = "-"
            reference_comments: tuple[str, ...] = ()
            engagement_metric_texts = browser.get_right_action_metric_texts(limit=8)
            engagement_like_count, engagement_share_count = _extract_ranked_engagement_counts(
                engagement_metric_texts
            )
            # Fallback when rail extraction misses due transient UI rendering.
            if engagement_like_count <= 0 and engagement_share_count <= 0:
                engagement_like_count = _extract_metric_count(snapshot.dom_text, LIKE_COUNT_LABELS)
                engagement_share_count = _extract_metric_count(snapshot.dom_text, SHARE_COUNT_LABELS)
            _, engagement_share_ratio = _should_share_by_engagement(
                share_count=engagement_share_count,
                like_count=engagement_like_count,
            )
            action = ""
            task_status = ""

            if live_by_hint:
                action = "wait_live_then_next"
                task_status = "live_skipped"
                print(f"[round {idx + 1}] action=wait_live {live_wait_seconds}s then next")
                browser.wait_seconds(live_wait_seconds)
                if idx < iterations - 1:
                    browser.next_item("live_wait_done")
                _emit_runtime_round_log(
                    round_idx=idx + 1,
                    profile=profile,
                    ai_comment=draft_comment,
                    share_result=share_result,
                    share_detail=share_detail,
                    like_count=engagement_like_count,
                    share_count=engagement_share_count,
                    ratio=engagement_share_ratio,
                    task_status=task_status,
                )
                _write_round_row(
                    {
                        "round": idx + 1,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "video_id": snapshot.video_id,
                        "url": snapshot.url,
                        "classification": classification.kind,
                        "confidence": f"{classification.confidence:.2f}",
                        "live_by_hint_raw": str(live_by_hint_raw),
                        "live_by_hint": str(live_by_hint),
                        "live_by_badge": str(live_by_badge),
                        "ad_badge": str(ad_badge),
                        "start_panel_open": str(round_start_panel_open),
                        "start_panel_closed": str(round_start_panel_closed),
                        "focused_context_count": len(focused_context_texts),
                        "profile_source": profile.source,
                        "top_themes": " | ".join(profile.themes),
                        "top_types": " | ".join(profile.types),
                        "top_styles": " | ".join(profile.styles),
                        "share_score": profile.share_score,
                        "share_level": profile.share_level,
                        "share_reason": profile.share_reason,
                        "share_worth_share": str(profile.worth_share),
                        "share_humor_score": profile.humor_score,
                        "share_funny_score": profile.funny_score,
                        "share_parody_score": profile.parody_score,
                        "share_nonsense_score": profile.nonsense_score,
                        "share_abstract_score": profile.abstract_score,
                        "engagement_like_count": engagement_like_count,
                        "engagement_share_count": engagement_share_count,
                        "engagement_share_like_ratio": f"{engagement_share_ratio:.6f}",
                        "engagement_metric_texts": " | ".join(engagement_metric_texts),
                        "video_topic": video_topic,
                        "video_objects": video_objects,
                        "action": action,
                        "task_status": task_status,
                        "panel_open_before": str(panel_open_before),
                        "pressed_x": str(pressed_x),
                        "panel_open_after": str(opened),
                        "share_enabled": str(share_enabled_flag),
                        "share_triggered": str(share_triggered),
                        "share_result": share_result,
                        "share_detail": share_detail,
                        "shared_url": shared_url,
                        "share_target": share_target_value,
                        "share_message": share_message,
                        "comment_refs_count": comment_refs_count,
                        "comment_result": comment_result,
                        "comment_source": comment_source,
                        "comment": draft_comment,
                    }
                )
                continue

            panel_open_before = browser.is_comment_panel_open()
            opened = panel_open_before

            short_video_confirmed = not live_by_hint
            action = "non_live_wait_then_next"
            should_share = False
            gate_enabled = enable_share or comment_without_share

            if short_video_confirmed:
                if not gate_enabled:
                    share_result = "disabled"
                    share_detail = "share_disabled"
                elif ad_badge:
                    share_result = "skip_ad"
                    share_detail = "ad_badge=True;rule=author_badge_only"
                elif share_all:
                    should_share = True
                else:
                    should_share, engagement_share_ratio = _should_share_by_engagement(
                        share_count=engagement_share_count,
                        like_count=engagement_like_count,
                    )
                    if not should_share:
                        share_result = "skip_low_engagement"
                        share_detail = (
                            f"share={engagement_share_count};"
                            f"like={engagement_like_count};"
                            f"ratio={engagement_share_ratio:.6f}"
                        )
                if should_share and not enable_share:
                    share_result = "disabled"
                    share_detail = "share_disabled_comment_only"

            if short_video_confirmed and should_share and comment_by_content and gate_enabled:
                if not panel_open_before:
                    opened = browser.open_comment_panel()
                    pressed_x = True
                    if not opened:
                        # Keep operation minimal: only retry X path once more.
                        browser.wait_seconds(0.3)
                        opened = browser.open_comment_panel()

                if opened:
                    reference_comments = browser.get_visible_comment_texts(
                        limit=18,
                        scroll_rounds=2,
                    )
                comment_refs_count = len(reference_comments)

                analyzed_profile = None
                if focused_excerpt:
                    analyzed_profile = ai_client.analyze_video_profile(
                        content_excerpt=focused_excerpt,
                        reference_comments=reference_comments,
                    )
                if analyzed_profile is not None:
                    profile = analyzed_profile
                    video_topic = profile.themes[0]
                    video_objects = "、".join(profile.themes[1:3])
                    print(
                        f"[round {idx + 1}] profile_refined_source={profile.source} "
                        f"themes={' | '.join(profile.themes)} "
                        f"types={' | '.join(profile.types)} "
                        f"styles={' | '.join(profile.styles)} "
                        f"share={profile.share_score}({profile.share_level}) "
                        f"worth_share={profile.worth_share}"
                    )

                if not focused_excerpt:
                    comment_source = "ai"
                    comment_result = "context_not_found"
                    task_status = "context_not_found"
                else:
                    summary_snapshot = ContentSnapshot(
                        video_id=snapshot.video_id,
                        url=snapshot.url,
                        dom_text=focused_excerpt if focused_excerpt else snapshot.dom_text[:220],
                        dom_markers=snapshot.dom_markers,
                        frame_texts=snapshot.frame_texts,
                        timestamp=snapshot.timestamp,
                    )
                    topic_summary = vision.understand(summary_snapshot)
                    tone = topic_summary.tone
                    if any("吐槽" in style or "毒舌" in style for style in profile.styles):
                        tone = "critical"
                    summary_objects = tuple(
                        obj
                        for obj in (
                            profile.themes[1],
                            profile.types[0],
                            profile.styles[0],
                        )
                        if obj
                    )[:2]
                    summary_for_comment = SemanticSummary(
                        topic=profile.themes[0],
                        objects=summary_objects,
                        tone=tone,
                        sensitive_flag=topic_summary.sensitive_flag,
                        ocr_snippets=topic_summary.ocr_snippets,
                    )
                    profile_hint = (
                        f"主题候选:{'、'.join(profile.themes)}；"
                        f"类型候选:{'、'.join(profile.types)}；"
                        f"风格候选:{'、'.join(profile.styles)}。"
                    )
                    ai_text = ai_client.generate(
                        summary=summary_for_comment,
                        reference_comments=reference_comments,
                        content_excerpt=f"{focused_excerpt} {profile_hint}",
                        recent_generated_comments=recent_generated_comments,
                    )
                    if ai_text:
                        draft_comment = ai_text
                        share_message_seed = ai_text
                        comment_source = "ai"
                        recent_generated_comments = (draft_comment, *recent_generated_comments)[:16]
                        if opened:
                            draft_comment = _compose_mention_comment(
                                base_comment=draft_comment,
                                mention_targets=mention_friend_values,
                            )
                            # Only send when explicitly enabled. Otherwise keep dry-run style trace.
                            if browser.dry_run_post:
                                comment_result = "generated_only"
                                task_status = "ok_generated"
                            else:
                                posted = browser.post_comment(draft_comment)
                                comment_result = "posted" if posted else "post_failed"
                                task_status = "ok_posted" if posted else "post_failed"
                        else:
                            comment_result = "panel_not_open"
                            task_status = "panel_not_open"
                    else:
                        comment_source = "ai"
                        comment_result = "ai_unavailable"
                        task_status = "ai_unavailable"
            elif short_video_confirmed and should_share:
                task_status = "share_candidate_no_comment_mode"
                comment_result = "skip_no_comment_mode"
            elif short_video_confirmed and share_result == "skip_ad":
                task_status = "skip_ad"
                comment_result = "skip_not_share_candidate"
            elif short_video_confirmed and share_result == "skip_low_engagement":
                task_status = "skip_low_engagement"
                comment_result = "skip_not_share_candidate"
            elif short_video_confirmed and share_result == "disabled":
                task_status = "share_disabled"
                comment_result = "skip_not_share_candidate"
            else:
                task_status = "non_live_no_comment_mode"

            if (
                short_video_confirmed
                and should_share
                and bool(mention_friend_values)
                and comment_result in {"skip", "skip_no_comment_mode", "context_not_found", "ai_unavailable"}
            ):
                comment_source = "mention"
                comment_result = "skip_need_ai_comment"
                task_status = "skip_need_ai_comment"

            if short_video_confirmed and should_share and enable_share:
                share_triggered = True
                # Sharing UI works better on feed canvas; close comment drawer first.
                if browser.is_comment_panel_open():
                    browser.close_comment_panel_if_open()
                    browser.wait_seconds(0.2)
                if share_target_value:
                    share_message = share_message_seed.strip()
                    ok, detail, shared_url = browser.share_current_video_to_target(
                        target_name=share_target_value,
                        message=share_message,
                    )
                    share_detail = detail
                    share_result = "shared" if ok else "share_failed"
                    print(
                        f"[round {idx + 1}] share_triggered={share_triggered} "
                        f"share_result={share_result} detail={share_detail} "
                        f"share_msg_len={len(share_message)}"
                    )
                else:
                    ok, detail, shared_url = browser.share_current_video()
                    share_detail = detail
                    share_result = "shared" if ok else "share_failed"
                    print(
                        f"[round {idx + 1}] share_triggered={share_triggered} "
                        f"share_result={share_result} detail={share_detail}"
                    )

            _emit_runtime_round_log(
                round_idx=idx + 1,
                profile=profile,
                ai_comment=draft_comment,
                share_result=share_result,
                share_detail=share_detail,
                like_count=engagement_like_count,
                share_count=engagement_share_count,
                ratio=engagement_share_ratio,
                task_status=task_status,
            )
            print(
                f"[round {idx + 1}] action=non_live "
                f"short_video={short_video_confirmed} "
                f"panel_open_before={panel_open_before} "
                f"pressed_x={pressed_x} "
                f"panel_open_after={opened}; "
                f"wait_non_live {video_wait_seconds}s then next"
            )
            if comment_by_content and short_video_confirmed:
                print(
                    f"[round {idx + 1}] comment_result={comment_result} "
                    f"source={comment_source} "
                    f"comment={draft_comment if draft_comment else '-'}"
                )
                if opened:
                    print(f"[round {idx + 1}] comment_refs={len(reference_comments)}")
            browser.wait_seconds(video_wait_seconds)
            if idx < iterations - 1:
                browser.next_item("non_live_wait_done")

            _write_round_row(
                {
                    "round": idx + 1,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "video_id": snapshot.video_id,
                    "url": snapshot.url,
                    "classification": classification.kind,
                    "confidence": f"{classification.confidence:.2f}",
                    "live_by_hint_raw": str(live_by_hint_raw),
                    "live_by_hint": str(live_by_hint),
                    "live_by_badge": str(live_by_badge),
                    "ad_badge": str(ad_badge),
                    "start_panel_open": str(round_start_panel_open),
                    "start_panel_closed": str(round_start_panel_closed),
                    "focused_context_count": len(focused_context_texts),
                    "profile_source": profile.source,
                    "top_themes": " | ".join(profile.themes),
                    "top_types": " | ".join(profile.types),
                    "top_styles": " | ".join(profile.styles),
                    "share_score": profile.share_score,
                    "share_level": profile.share_level,
                    "share_reason": profile.share_reason,
                    "share_worth_share": str(profile.worth_share),
                    "share_humor_score": profile.humor_score,
                    "share_funny_score": profile.funny_score,
                    "share_parody_score": profile.parody_score,
                    "share_nonsense_score": profile.nonsense_score,
                    "share_abstract_score": profile.abstract_score,
                    "engagement_like_count": engagement_like_count,
                    "engagement_share_count": engagement_share_count,
                    "engagement_share_like_ratio": f"{engagement_share_ratio:.6f}",
                    "engagement_metric_texts": " | ".join(engagement_metric_texts),
                    "video_topic": video_topic,
                    "video_objects": video_objects,
                    "action": action,
                    "task_status": task_status,
                    "panel_open_before": str(panel_open_before),
                    "pressed_x": str(pressed_x),
                    "panel_open_after": str(opened),
                    "share_enabled": str(share_enabled_flag),
                    "share_triggered": str(share_triggered),
                    "share_result": share_result,
                    "share_detail": share_detail,
                    "shared_url": shared_url,
                    "share_target": share_target_value,
                    "share_message": share_message,
                    "comment_refs_count": comment_refs_count,
                    "comment_result": comment_result,
                    "comment_source": comment_source,
                    "comment": draft_comment,
                }
            )
    finally:
        if csv_file is not None:
            csv_file.close()

    return 0


def main() -> int:
    args = parse_args()

    classifier = ContentClassifier()
    vision = HeuristicVision()
    generator = CommentGenerator()
    ai_client = AICommentClient(
        enabled=args.use_ai_comment,
        api_base=args.llm_api_base,
        model=args.llm_model,
        api_key_env=args.llm_api_key_env,
        style=args.comment_style,
        insecure_skip_verify=args.llm_insecure_skip_verify,
        debug=args.llm_debug,
    )
    browser = PlaywrightBrowserAdapter(
        start_url=args.start_url,
        headless=args.headless,
        user_data_dir=args.profile_dir,
        screenshot_dir=args.screenshots,
        dry_run_post=not args.enable_post,
        require_login=args.require_login,
        manual_login_prompt=True,
        login_timeout_seconds=args.login_timeout,
        login_poll_interval_seconds=args.login_poll,
        wait_scale=args.wait_scale,
        post_next_settle_seconds=args.post_next_settle_seconds,
        snapshot_settle_seconds=args.snapshot_settle_seconds,
        snapshot_on_scan=False,
    )
    runtime_log = RuntimeLogWindow(enabled=(not args.no_log_window and args.mode == "scan"))

    if args.login_only:
        try:
            browser.open_home()
            ok = browser.ensure_login()
            print(f"[login-only] logged_in={ok}")
            return 0 if ok else 2
        finally:
            runtime_log.close()
            browser.close()

    try:
        if args.mode == "scan":
            return run_scan_mode(
                browser=browser,
                classifier=classifier,
                vision=vision,
                iterations=args.iterations,
                live_wait_seconds=args.live_wait_seconds,
                video_wait_seconds=args.video_wait_seconds,
                force_non_live=args.force_non_live,
                comment_by_content=args.comment_by_content,
                ai_client=ai_client,
                scan_report_csv=args.scan_report_csv,
                enable_share=args.enable_share,
                comment_without_share=args.comment_without_share,
                share_all=args.share_all,
                share_target=args.share_target,
                comment_mention_friend=args.comment_mention_friend,
                share_strong_only=args.share_strong_only,
                runtime_log=runtime_log,
            )

        runner = DouyinWorkflowRunner(
            browser=browser,
            vision=vision,
            approver=ConsoleApprover(auto_yes=args.auto_approve),
            classifier=classifier,
            generator=generator,
            policy=CommentPolicyEngine(PolicyConfig()),
            config=RunnerConfig(auto_post=args.auto_post),
        )
        recent_comments: tuple[str, ...] = ()
        recent_times: tuple[datetime, ...] = ()

        for idx in range(args.iterations):
            now = datetime.now(timezone.utc)
            result = runner.run_once(
                now=now,
                recent_comments=recent_comments,
                recent_post_times=recent_times,
            )

            print(f"\n[round {idx + 1}] outcome={result.outcome}")
            if result.classification is not None:
                print(
                    "[round {}] classification={} confidence={:.2f} reasons={}".format(
                        idx + 1,
                        result.classification.kind,
                        result.classification.confidence,
                        result.classification.reasons,
                    )
                )
            if result.comment:
                print(f"[round {idx + 1}] comment={result.comment}")
            if result.policy is not None:
                print(f"[round {idx + 1}] policy_allowed={result.policy.allowed}")
                if result.policy.reasons:
                    print(f"[round {idx + 1}] policy_reasons={result.policy.reasons}")

            if result.outcome == "posted" and result.comment:
                recent_comments = (result.comment, *recent_comments)[:200]
                recent_times = (now, *recent_times)[:200]

            already_advanced = {
                "skip_live",
                "skip_unknown",
                "blocked_by_policy",
                "manual_reject",
            }
            if idx < args.iterations - 1:
                if result.outcome not in already_advanced:
                    browser.next_item("loop_next")
    finally:
        runtime_log.close()
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
