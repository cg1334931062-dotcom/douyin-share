from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from douyin_agent import (
    CommentGenerator,
    CommentPolicyEngine,
    ContentClassifier,
    ContentSnapshot,
    DouyinWorkflowRunner,
    PolicyConfig,
    RunnerConfig,
    SemanticSummary,
)


class DemoBrowser:
    def __init__(self, snapshot: ContentSnapshot):
        self.snapshot = snapshot
        self.posted: list[str] = []

    def open_home(self) -> None:
        pass

    def ensure_login(self) -> bool:
        return True

    def current_snapshot(self) -> ContentSnapshot:
        return self.snapshot

    def next_item(self, reason: str) -> None:
        print(f"[skip] reason={reason}")

    def capture_frames(self, snapshot: ContentSnapshot) -> tuple[str, ...]:
        return ("美食 教程 家常菜", "锅气很足", "配菜讲解清晰")

    def post_comment(self, comment: str) -> bool:
        self.posted.append(comment)
        print(f"[posted] {comment}")
        return True


class DemoVision:
    def understand(self, snapshot: ContentSnapshot) -> SemanticSummary:
        return SemanticSummary(
            topic="家常菜做法",
            objects=("火候", "调味"),
            tone="positive",
            sensitive_flag=False,
            ocr_snippets=snapshot.frame_texts,
        )


class DemoApprover:
    def approve(self, comment: str, snapshot: ContentSnapshot) -> bool:
        return True


if __name__ == "__main__":
    snapshot = ContentSnapshot(
        video_id="demo-1",
        url="https://www.douyin.com/",
        dom_text="点赞 评论 收藏 分享",
        dom_markers=("comment_button", "like_button", "share_button"),
    )
    runner = DouyinWorkflowRunner(
        browser=DemoBrowser(snapshot),
        vision=DemoVision(),
        approver=DemoApprover(),
        classifier=ContentClassifier(),
        generator=CommentGenerator(),
        policy=CommentPolicyEngine(PolicyConfig()),
        config=RunnerConfig(auto_post=False),
    )

    result = runner.run_once(now=datetime.now(timezone.utc))
    print(result)
