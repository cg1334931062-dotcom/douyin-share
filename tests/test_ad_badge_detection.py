from douyin_agent.browser_playwright import (
    _has_author_ad_text,
    _has_author_area_ad_badge,
    _has_author_line_without_date,
)


def test_author_area_exact_ad_badge_is_detected() -> None:
    candidates = (
        (
            "@芯愿科技",
            {"x": 92.0, "y": 620.0, "width": 110.0, "height": 22.0},
            "author",
        ),
        (
            "广告",
            {"x": 214.0, "y": 622.0, "width": 28.0, "height": 16.0},
            "ad",
        ),
    )

    assert _has_author_area_ad_badge(candidates, width=1320.0, height=860.0)


def test_author_handle_plus_ad_in_author_area_is_detected() -> None:
    candidates = (
        (
            "@健身小王 广告",
            {"x": 140.0, "y": 670.0, "width": 120.0, "height": 20.0},
            "generic",
        ),
    )

    assert _has_author_area_ad_badge(candidates, width=1320.0, height=860.0)


def test_author_row_with_followup_description_and_ad_is_detected() -> None:
    candidates = (
        (
            "@趣测_心灵之旅 广告 2026年爆火的霍兰德职业测试",
            {"x": 80.0, "y": 705.0, "width": 360.0, "height": 26.0},
            "author",
        ),
    )

    assert _has_author_area_ad_badge(candidates, width=1320.0, height=860.0)


def test_author_ad_text_fallback_detects_long_author_row() -> None:
    texts = (
        "更多内容 你的MBTI人格有多特别，一测便知你的隐藏天赋！",
        "@考道网mbti性格测试 广告 本以为MBTI就是开盲盒，原来是我一直测错了！",
    )

    assert _has_author_ad_text(texts)


def test_author_ad_text_fallback_does_not_flag_normal_author_row() -> None:
    texts = (
        "@Bobaya 3月20日",
        "2026年热歌榜单Top10 #热歌热门分享",
    )

    assert not _has_author_ad_text(texts)


def test_author_line_without_date_is_detected_as_ad_fallback() -> None:
    texts = (
        "练好行书并不难，掌握了连笔轨迹能事半功倍#行书 #连笔字",
        "@橙小汐 练好行书并不难，掌握了连笔轨迹能事半功倍#行书 #连笔字",
    )

    assert _has_author_line_without_date(texts)


def test_author_line_with_date_is_not_detected_as_ad_fallback() -> None:
    texts = (
        "第24集：她跪在雪里求队友救丈夫，换来的却是沉默",
        "@探险者 · 2月10日 第24集：她跪在雪里求队友救丈夫，换来的却是沉默",
    )

    assert not _has_author_line_without_date(texts)


def test_ad_text_outside_author_area_is_not_detected() -> None:
    candidates = (
        (
            "@芯愿科技",
            {"x": 92.0, "y": 620.0, "width": 110.0, "height": 22.0},
            "author",
        ),
        (
            "广告",
            {"x": 990.0, "y": 120.0, "width": 28.0, "height": 16.0},
            "ad",
        ),
    )

    assert not _has_author_area_ad_badge(candidates, width=1320.0, height=860.0)


def test_non_ad_text_in_author_area_is_not_detected() -> None:
    candidates = (
        (
            "品牌合作",
            {"x": 120.0, "y": 650.0, "width": 52.0, "height": 18.0},
            "generic",
        ),
    )

    assert not _has_author_area_ad_badge(candidates, width=1320.0, height=860.0)


def test_standalone_ad_without_author_name_is_not_detected() -> None:
    candidates = (
        (
            "广告",
            {"x": 214.0, "y": 622.0, "width": 28.0, "height": 16.0},
            "ad",
        ),
    )

    assert not _has_author_area_ad_badge(candidates, width=1320.0, height=860.0)


def test_ad_badge_not_on_same_row_as_author_is_not_detected() -> None:
    candidates = (
        (
            "@Bobaya",
            {"x": 92.0, "y": 700.0, "width": 92.0, "height": 22.0},
            "author",
        ),
        (
            "广告",
            {"x": 214.0, "y": 622.0, "width": 28.0, "height": 16.0},
            "ad",
        ),
    )

    assert not _has_author_area_ad_badge(candidates, width=1320.0, height=860.0)
