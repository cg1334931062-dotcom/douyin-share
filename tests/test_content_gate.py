from douyin_agent import evaluate_hard_content_gate


def test_live_content_is_always_hard_blocked() -> None:
    decision = evaluate_hard_content_gate(
        live_by_hint=True,
        ad_badge=False,
    )

    assert decision.blocked
    assert decision.result == "skip_live"
    assert decision.task_status == "live_skipped"


def test_live_hint_false_does_not_hard_block() -> None:
    decision = evaluate_hard_content_gate(
        live_by_hint=False,
        ad_badge=False,
    )

    assert not decision.blocked


def test_ad_content_is_always_hard_blocked() -> None:
    decision = evaluate_hard_content_gate(
        live_by_hint=False,
        ad_badge=True,
    )

    assert decision.blocked
    assert decision.result == "skip_ad"
    assert decision.task_status == "skip_ad"


def test_regular_short_video_is_not_hard_blocked() -> None:
    decision = evaluate_hard_content_gate(
        live_by_hint=False,
        ad_badge=False,
    )

    assert not decision.blocked
