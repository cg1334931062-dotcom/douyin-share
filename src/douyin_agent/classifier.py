from __future__ import annotations

from dataclasses import dataclass

from .models import ClassificationResult, ContentSnapshot

LIVE_MARKERS = {
    "live_badge",
    "gift_panel",
    "online_count",
    "live_room",
    "liveroom",
}

SHORT_VIDEO_MARKERS = {
    "like_button",
    "comment_button",
    "share_button",
    "collect_button",
}

LIVE_KEYWORDS = (
    "直播",
    "直播中",
    "正在直播",
    "福袋",
    "在线",
    "音浪",
    "礼物",
    "小时榜",
)

SHORT_VIDEO_KEYWORDS = (
    "评论",
    "点赞",
    "收藏",
    "转发",
    "作品",
    "短视频",
)


@dataclass
class ContentClassifier:
    min_signal_confidence: float = 0.58

    def classify(self, snapshot: ContentSnapshot) -> ClassificationResult:
        merged = " ".join(
            [snapshot.dom_text, *snapshot.dom_markers, *snapshot.frame_texts]
        ).lower()

        live_marker_hits = sum(
            1 for marker in snapshot.dom_markers if marker.lower() in LIVE_MARKERS
        )
        short_marker_hits = sum(
            1
            for marker in snapshot.dom_markers
            if marker.lower() in SHORT_VIDEO_MARKERS
        )

        live_keyword_hits = sum(1 for kw in LIVE_KEYWORDS if kw in merged)
        short_keyword_hits = sum(1 for kw in SHORT_VIDEO_KEYWORDS if kw in merged)

        live_score = min(1.0, live_marker_hits * 0.28 + live_keyword_hits * 0.10)
        short_score = min(1.0, short_marker_hits * 0.22 + short_keyword_hits * 0.10)

        diff = live_score - short_score
        if max(live_score, short_score) < 0.20:
            return ClassificationResult(
                kind="unknown",
                confidence=0.45,
                reasons=("insufficient_signals",),
            )

        if diff > 0.12:
            confidence = max(self.min_signal_confidence, min(0.99, 0.55 + abs(diff)))
            return ClassificationResult(
                kind="live",
                confidence=confidence,
                reasons=(
                    f"live_marker_hits={live_marker_hits}",
                    f"live_keyword_hits={live_keyword_hits}",
                ),
            )

        if diff < -0.08:
            confidence = max(self.min_signal_confidence, min(0.99, 0.55 + abs(diff)))
            return ClassificationResult(
                kind="short_video",
                confidence=confidence,
                reasons=(
                    f"short_marker_hits={short_marker_hits}",
                    f"short_keyword_hits={short_keyword_hits}",
                ),
            )

        return ClassificationResult(
            kind="unknown",
            confidence=0.50,
            reasons=("mixed_signals",),
        )
