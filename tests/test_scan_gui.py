from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


GUI_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_scan_gui.py"
spec = importlib.util.spec_from_file_location("run_scan_gui", GUI_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"cannot load {GUI_PATH}")
run_scan_gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_scan_gui)
build_scan_command = run_scan_gui.build_scan_command


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "examples" / "run_real_site_once.py"
SHARE_RULES = ROOT / "configs" / "share_rules.toml"


def build_command(**overrides: object) -> list[str]:
    values: dict[str, object] = {
        "python_executable": sys.executable,
        "runner": RUNNER,
        "iterations": 20,
        "profile_dir": ".playwright_profile_main",
        "wait_scale": 1.6,
        "live_wait": 3.0,
        "video_wait": 10.0,
        "post_next_settle": 8.0,
        "snapshot_settle": 2.0,
        "comment_style": "humorous",
        "share_rules_config": SHARE_RULES,
        "share_min_like": 100,
        "share_min_share": 500,
        "share_min_ratio": 0.5,
        "share_threshold_mode": "any",
        "require_login": True,
        "headless": False,
        "no_log_window": False,
        "comment_by_content": True,
        "use_ai_comment": True,
        "llm_api_base": "https://api.deepseek.com/v1",
        "llm_model": "deepseek-chat",
        "llm_api_key_env": "DEEPSEEK_API_KEY",
        "insecure_skip_verify": True,
        "enable_share": False,
        "share_target": "",
        "comment_without_share": False,
        "enable_post": False,
        "mention_friend": "",
    }
    values.update(overrides)
    return build_scan_command(**values)  # type: ignore[arg-type]


def test_command_contains_scan_and_wait_parameters() -> None:
    command = build_command(
        iterations=7,
        wait_scale=2.25,
        live_wait=4.0,
        video_wait=12.0,
        post_next_settle=9.0,
        snapshot_settle=3.0,
    )

    assert command[:2] == [sys.executable, str(RUNNER)]
    assert command[command.index("--iterations") + 1] == "7"
    assert command[command.index("--wait-scale") + 1] == "2.25"
    assert command[command.index("--live-wait-seconds") + 1] == "4.0"
    assert command[command.index("--video-wait-seconds") + 1] == "12.0"
    assert command[command.index("--post-next-settle-seconds") + 1] == "9.0"
    assert command[command.index("--snapshot-settle-seconds") + 1] == "3.0"


def test_command_contains_share_target_and_thresholds() -> None:
    command = build_command(
        enable_share=True,
        share_target="  好友   群  ",
        share_min_like=200,
        share_min_share=600,
        share_min_ratio=0.75,
        share_threshold_mode="all",
    )

    assert "--enable-share" in command
    assert command[command.index("--share-target") + 1] == "好友 群"
    assert command[command.index("--share-min-like-count") + 1] == "200"
    assert command[command.index("--share-min-share-count") + 1] == "600"
    assert command[command.index("--share-min-share-like-ratio") + 1] == "0.75"
    assert command[command.index("--share-threshold-mode") + 1] == "all"


def test_disabled_side_effects_are_absent_and_comment_options_are_explicit() -> None:
    command = build_command(
        comment_by_content=True,
        use_ai_comment=False,
        enable_share=False,
        comment_without_share=True,
        enable_post=False,
    )

    assert "--comment-by-content" in command
    assert "--no-ai-comment" in command
    assert "--comment-without-share" in command
    assert "--enable-share" not in command
    assert "--share-target" not in command
    assert "--enable-post" not in command


def test_ai_mention_configuration_is_included_consistently() -> None:
    command = build_command(
        comment_by_content=True,
        use_ai_comment=True,
        llm_api_base="https://llm.example/v1",
        llm_model="test-model",
        llm_api_key_env="TEST_API_KEY",
        insecure_skip_verify=False,
        mention_friend="张三,李四",
    )

    assert command[command.index("--llm-api-base") + 1] == "https://llm.example/v1"
    assert command[command.index("--llm-model") + 1] == "test-model"
    assert command[command.index("--llm-api-key-env") + 1] == "TEST_API_KEY"
    assert "--llm-verify" in command
    assert command[command.index("--comment-mention-friend") + 1] == "张三,李四"
