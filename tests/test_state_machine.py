from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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


class FakeBrowser:
    def __init__(self, cards: list[ContentSnapshot], frame_texts: dict[str, tuple[str, ...]]):
        self.cards = cards
        self.frame_texts = frame_texts
        self.cursor = 0
        self.next_reasons: list[str] = []
        self.posted_comments: list[str] = []
        self.open_count = 0

    def open_home(self) -> None:
        self.open_count += 1

    def ensure_login(self) -> bool:
        return True

    def current_snapshot(self) -> ContentSnapshot:
        return self.cards[self.cursor]

    def next_item(self, reason: str) -> None:
        self.next_reasons.append(reason)
        if self.cursor < len(self.cards) - 1:
            self.cursor += 1

    def capture_frames(self, snapshot: ContentSnapshot) -> tuple[str, ...]:
        return self.frame_texts.get(snapshot.video_id, ())

    def post_comment(self, comment: str) -> bool:
        self.posted_comments.append(comment)
        return True


@dataclass
class FakeVision:
    semantics: dict[str, SemanticSummary]

    def understand(self, snapshot: ContentSnapshot) -> SemanticSummary:
        return self.semantics[snapshot.video_id]


@dataclass
class FakeApprover:
    allow: bool = True

    def approve(self, comment: str, snapshot: ContentSnapshot) -> bool:
        return self.allow


@dataclass
class ConstantGenerator:
    text: str

    def generate(self, summary: SemanticSummary) -> str:
        return self.text


def test_workflow_skips_live_content() -> None:
    live_card = ContentSnapshot(
        video_id="live-1",
        url="https://www.douyin.com/",
        dom_text="直播中 音浪实时更新",
        dom_markers=("live_badge", "gift_panel"),
    )
    next_card = ContentSnapshot(
        video_id="video-2",
        url="https://www.douyin.com/",
        dom_text="点赞 评论 收藏",
        dom_markers=("comment_button",),
    )

    browser = FakeBrowser(cards=[live_card, next_card], frame_texts={})
    runner = DouyinWorkflowRunner(
        browser=browser,
        vision=FakeVision({"live-1": SemanticSummary(topic="直播", tone="neutral")}),
        approver=FakeApprover(True),
        classifier=ContentClassifier(),
        generator=CommentGenerator(),
        policy=CommentPolicyEngine(PolicyConfig()),
        config=RunnerConfig(auto_post=False),
    )

    result = runner.run_once(now=datetime.now(timezone.utc))
    assert result.outcome == "skip_live"
    assert browser.next_reasons == ["live"]
    assert "S5_IF_LIVE_SKIP" in result.states


def test_workflow_posts_after_policy_and_manual_approval() -> None:
    short_card = ContentSnapshot(
        video_id="video-1",
        url="https://www.douyin.com/",
        dom_text="点赞 评论 收藏",
        dom_markers=("comment_button", "like_button"),
    )
    browser = FakeBrowser(
        cards=[short_card],
        frame_texts={"video-1": ("美食教程", "调味细节", "家常菜")},
    )
    runner = DouyinWorkflowRunner(
        browser=browser,
        vision=FakeVision(
            {
                "video-1": SemanticSummary(
                    topic="家常菜做法",
                    objects=("火候", "调味"),
                    tone="positive",
                )
            }
        ),
        approver=FakeApprover(True),
        classifier=ContentClassifier(),
        generator=CommentGenerator(),
        policy=CommentPolicyEngine(PolicyConfig()),
        config=RunnerConfig(auto_post=False),
    )

    result = runner.run_once(now=datetime.now(timezone.utc))
    assert result.outcome == "posted"
    assert len(browser.posted_comments) == 1
    assert result.comment == browser.posted_comments[0]
    assert "S10_HUMAN_APPROVAL" in result.states


def test_workflow_skips_unknown_content() -> None:
    unknown_card = ContentSnapshot(
        video_id="video-unknown",
        url="https://www.douyin.com/",
        dom_text="欢迎来到推荐页",
        dom_markers=(),
    )
    browser = FakeBrowser(cards=[unknown_card], frame_texts={})
    runner = DouyinWorkflowRunner(
        browser=browser,
        vision=FakeVision({"video-unknown": SemanticSummary(topic="未知内容", tone="neutral")}),
        approver=FakeApprover(True),
        classifier=ContentClassifier(),
        generator=CommentGenerator(),
        policy=CommentPolicyEngine(PolicyConfig()),
        config=RunnerConfig(auto_post=False),
    )

    result = runner.run_once(now=datetime.now(timezone.utc))
    assert result.outcome == "skip_unknown"
    assert browser.next_reasons == ["unknown"]
    assert "S5_IF_UNKNOWN_SKIP" in result.states


def test_workflow_blocks_by_policy_before_approval() -> None:
    short_card = ContentSnapshot(
        video_id="video-3",
        url="https://www.douyin.com/",
        dom_text="点赞 评论 收藏",
        dom_markers=("comment_button", "like_button"),
    )
    browser = FakeBrowser(cards=[short_card], frame_texts={"video-3": ("财经",)})
    runner = DouyinWorkflowRunner(
        browser=browser,
        vision=FakeVision({"video-3": SemanticSummary(topic="财经", tone="neutral")}),
        approver=FakeApprover(True),
        classifier=ContentClassifier(),
        generator=ConstantGenerator("私信我带你赚钱"),
        policy=CommentPolicyEngine(PolicyConfig()),
        config=RunnerConfig(auto_post=False),
    )

    result = runner.run_once(now=datetime.now(timezone.utc))
    assert result.outcome == "blocked_by_policy"
    assert browser.posted_comments == []
    assert browser.next_reasons == ["policy_block"]


def test_workflow_manual_reject() -> None:
    short_card = ContentSnapshot(
        video_id="video-4",
        url="https://www.douyin.com/",
        dom_text="点赞 评论 收藏",
        dom_markers=("comment_button", "like_button"),
    )
    browser = FakeBrowser(cards=[short_card], frame_texts={"video-4": ("旅行",)})
    runner = DouyinWorkflowRunner(
        browser=browser,
        vision=FakeVision({"video-4": SemanticSummary(topic="旅行vlog", tone="neutral")}),
        approver=FakeApprover(False),
        classifier=ContentClassifier(),
        generator=CommentGenerator(),
        policy=CommentPolicyEngine(PolicyConfig()),
        config=RunnerConfig(auto_post=False),
    )

    result = runner.run_once(now=datetime.now(timezone.utc))
    assert result.outcome == "manual_reject"
    assert browser.posted_comments == []
    assert browser.next_reasons == ["manual_reject"]
