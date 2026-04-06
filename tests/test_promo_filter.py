from douyin_agent import detect_promotional_content


def test_detect_promotional_content_from_profile_labels() -> None:
    decision = detect_promotional_content(
        text="健腹轮居家训练动作拆解",
        types=("健身教学", "产品推广", "生活分享"),
        styles=("直接引导", "实用演示", "激励口号"),
    )

    assert decision.blocked
    assert "promo_types=产品推广" in decision.detail


def test_detect_promotional_content_from_text_cta() -> None:
    decision = detect_promotional_content(
        text="点击下方链接领券，下单同款健腹轮，限时优惠",
    )

    assert decision.blocked
    assert "promo_text_rules=" in decision.detail


def test_detect_promotional_content_allows_regular_content() -> None:
    decision = detect_promotional_content(
        text="家常菜做法分享，火候和调味节奏讲得很清楚",
        types=("美食教程", "生活记录", "经验分享"),
        styles=("轻松讲解", "口语化", "节奏快"),
    )

    assert not decision.blocked
    assert decision.detail == "-"
