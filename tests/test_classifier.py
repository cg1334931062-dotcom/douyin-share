from douyin_agent import ContentClassifier, ContentSnapshot


def test_classify_live_from_markers_and_keywords() -> None:
    classifier = ContentClassifier()
    snapshot = ContentSnapshot(
        video_id="v-live",
        url="https://www.douyin.com/",
        dom_text="直播中 在线2.3万 福袋来啦",
        dom_markers=("live_badge", "gift_panel"),
    )

    result = classifier.classify(snapshot)
    assert result.kind == "live"
    assert result.confidence >= 0.58


def test_classify_short_video_from_interaction_markers() -> None:
    classifier = ContentClassifier()
    snapshot = ContentSnapshot(
        video_id="v-short",
        url="https://www.douyin.com/",
        dom_text="点赞 评论 收藏 转发",
        dom_markers=("comment_button", "like_button", "share_button"),
    )

    result = classifier.classify(snapshot)
    assert result.kind == "short_video"
    assert result.confidence >= 0.58


def test_classify_unknown_when_signal_is_weak() -> None:
    classifier = ContentClassifier()
    snapshot = ContentSnapshot(
        video_id="v-unknown",
        url="https://www.douyin.com/",
        dom_text="欢迎来到推荐页",
        dom_markers=(),
    )

    result = classifier.classify(snapshot)
    assert result.kind == "unknown"
