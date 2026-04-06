from __future__ import annotations

import pytest

from douyin_agent import ShareRuleConfig, load_share_rule_config


def test_default_share_rules_match_existing_behavior() -> None:
    config = ShareRuleConfig()

    low_like = config.evaluate(share_count=500_000, like_count=999)
    strong_share_count = config.evaluate(share_count=250_000, like_count=1_500)
    strong_ratio = config.evaluate(share_count=900, like_count=1_500)

    assert not low_like.should_share
    assert strong_share_count.should_share
    assert strong_ratio.should_share


def test_share_rule_all_mode_requires_all_enabled_checks() -> None:
    config = ShareRuleConfig(
        min_like_count=100,
        min_share_count=300,
        min_share_like_ratio=0.4,
        threshold_mode="all",
    )

    ratio_only = config.evaluate(share_count=250, like_count=500)
    both = config.evaluate(share_count=350, like_count=500)

    assert not ratio_only.should_share
    assert both.should_share


def test_load_share_rule_config_supports_custom_thresholds(tmp_path) -> None:
    config_path = tmp_path / "share_rules.toml"
    config_path.write_text(
        "\n".join(
            (
                "min_like_count = 200",
                "min_share_count = 600",
                "min_share_like_ratio = 0.75",
                "share_count_enabled = false",
                "share_like_ratio_enabled = true",
                'threshold_mode = "all"',
            )
        ),
        encoding="utf-8",
    )

    config = load_share_rule_config(config_path)

    assert config.min_like_count == 200
    assert config.min_share_count == 600
    assert config.min_share_like_ratio == 0.75
    assert not config.share_count_enabled
    assert config.share_like_ratio_enabled
    assert config.threshold_mode == "all"


def test_share_rule_requires_one_enabled_check() -> None:
    with pytest.raises(ValueError, match="at least one share rule must be enabled"):
        ShareRuleConfig(share_count_enabled=False, share_like_ratio_enabled=False)
