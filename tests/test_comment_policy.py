from datetime import datetime, timedelta, timezone

from douyin_agent import CommentGenerator, CommentPolicyEngine, PolicyConfig, SemanticSummary


def test_comment_generator_respects_length_and_topic() -> None:
    generator = CommentGenerator(min_len=8, max_len=30)
    summary = SemanticSummary(
        topic="家常菜做法",
        objects=("火候", "调味"),
        tone="positive",
    )

    comment = generator.generate(summary)
    assert 8 <= len(comment) <= 30
    assert "家常菜" in comment


def test_policy_blocks_banned_words() -> None:
    engine = CommentPolicyEngine(PolicyConfig())
    now = datetime.now(timezone.utc)
    decision = engine.evaluate(
        comment="这个太强了，私信我一起做",
        recent_comments=(),
        recent_post_times=(),
        now=now,
    )

    assert not decision.allowed
    assert any(reason.startswith("contains_banned_word") for reason in decision.reasons)


def test_policy_blocks_duplicate_comments() -> None:
    engine = CommentPolicyEngine(PolicyConfig())
    now = datetime.now(timezone.utc)
    comment = "家常菜做法这个点讲得很清楚"
    decision = engine.evaluate(
        comment=comment,
        recent_comments=(comment,),
        recent_post_times=(),
        now=now,
    )

    assert not decision.allowed
    assert any(reason.startswith("too_similar") for reason in decision.reasons)


def test_policy_blocks_hourly_quota_exceeded() -> None:
    config = PolicyConfig(max_comments_per_hour=2)
    engine = CommentPolicyEngine(config)
    now = datetime.now(timezone.utc)
    decision = engine.evaluate(
        comment="这个角度很有意思，学到了。",
        recent_comments=(),
        recent_post_times=(now - timedelta(minutes=20), now - timedelta(minutes=5)),
        now=now,
    )

    assert not decision.allowed
    assert "hourly_quota_exceeded" in decision.reasons
