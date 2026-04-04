from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from .classifier import ContentClassifier
from .commenting import CommentGenerator, CommentPolicyEngine
from .config import RunnerConfig
from .models import ContentSnapshot, SemanticSummary, WorkflowResult


class BrowserPort(Protocol):
    def open_home(self) -> None: ...

    def ensure_login(self) -> bool: ...

    def current_snapshot(self) -> ContentSnapshot: ...

    def next_item(self, reason: str) -> None: ...

    def capture_frames(self, snapshot: ContentSnapshot) -> tuple[str, ...]: ...

    def post_comment(self, comment: str) -> bool: ...


class VisionPort(Protocol):
    def understand(self, snapshot: ContentSnapshot) -> SemanticSummary: ...


class ApprovalPort(Protocol):
    def approve(self, comment: str, snapshot: ContentSnapshot) -> bool: ...


@dataclass
class DouyinWorkflowRunner:
    browser: BrowserPort
    vision: VisionPort
    approver: ApprovalPort
    classifier: ContentClassifier
    generator: CommentGenerator
    policy: CommentPolicyEngine
    config: RunnerConfig = RunnerConfig()

    def run_once(
        self,
        now: datetime,
        recent_comments: tuple[str, ...] = (),
        recent_post_times: tuple[datetime, ...] = (),
    ) -> WorkflowResult:
        states: list[str] = []

        states.append("S1_OPEN_DOUYIN")
        self.browser.open_home()

        states.append("S2_CHECK_LOGIN")
        if not self.browser.ensure_login():
            return WorkflowResult(outcome="need_login", states=tuple(states))

        states.append("S3_GET_CURRENT_CONTENT")
        snapshot = self.browser.current_snapshot()

        states.append("S4_CLASSIFY_LIVE_OR_VIDEO")
        classification = self.classifier.classify(snapshot)
        if classification.kind == "live":
            states.append("S5_IF_LIVE_SKIP")
            self.browser.next_item("live")
            return WorkflowResult(
                outcome="skip_live",
                states=tuple(states),
                classification=classification,
            )
        if classification.kind != "short_video":
            states.append("S5_IF_UNKNOWN_SKIP")
            self.browser.next_item("unknown")
            return WorkflowResult(
                outcome="skip_unknown",
                states=tuple(states),
                classification=classification,
            )

        states.append("S6_CAPTURE_FRAMES")
        frame_texts = self.browser.capture_frames(snapshot)
        enriched_snapshot = replace(snapshot, frame_texts=frame_texts)

        states.append("S7_CONTENT_UNDERSTAND")
        summary = self.vision.understand(enriched_snapshot)

        states.append("S8_GENERATE_COMMENT_DRAFT")
        draft = self.generator.generate(summary)

        states.append("S9_POLICY_CHECK")
        decision = self.policy.evaluate(
            comment=draft,
            recent_comments=recent_comments,
            recent_post_times=recent_post_times,
            now=now,
        )
        if not decision.allowed:
            self.browser.next_item("policy_block")
            return WorkflowResult(
                outcome="blocked_by_policy",
                states=tuple(states),
                comment=draft,
                classification=classification,
                policy=decision,
            )

        if not self.config.auto_post:
            states.append("S10_HUMAN_APPROVAL")
            if not self.approver.approve(draft, enriched_snapshot):
                self.browser.next_item("manual_reject")
                return WorkflowResult(
                    outcome="manual_reject",
                    states=tuple(states),
                    comment=draft,
                    classification=classification,
                    policy=decision,
                )

        states.append("S11_POST_AND_VERIFY")
        posted = self.browser.post_comment(draft)
        if not posted:
            return WorkflowResult(
                outcome="post_failed",
                states=tuple(states),
                comment=draft,
                classification=classification,
                policy=decision,
            )

        states.append("S12_COOLDOWN_NEXT")
        return WorkflowResult(
            outcome="posted",
            states=tuple(states),
            comment=draft,
            classification=classification,
            policy=decision,
        )
