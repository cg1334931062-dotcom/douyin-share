from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

ContentKind = Literal["live", "short_video", "unknown"]


@dataclass(frozen=True)
class ContentSnapshot:
    video_id: str
    url: str
    dom_text: str
    dom_markers: tuple[str, ...] = ()
    frame_texts: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ClassificationResult:
    kind: ContentKind
    confidence: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SemanticSummary:
    topic: str
    objects: tuple[str, ...] = ()
    tone: str = "neutral"
    sensitive_flag: bool = False
    ocr_snippets: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowResult:
    outcome: str
    states: tuple[str, ...]
    comment: str | None = None
    classification: ClassificationResult | None = None
    policy: PolicyDecision | None = None
