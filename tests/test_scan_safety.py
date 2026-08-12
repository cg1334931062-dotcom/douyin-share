from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


RUNNER_PATH = Path(__file__).resolve().parents[1] / "examples" / "run_real_site_once.py"
spec = importlib.util.spec_from_file_location("run_real_site_once", RUNNER_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"cannot load {RUNNER_PATH}")
run_real_site_once = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = run_real_site_once
spec.loader.exec_module(run_real_site_once)
format_runtime_round_log = run_real_site_once.format_runtime_round_log


def test_runtime_log_includes_low_engagement_reason() -> None:
    line = format_runtime_round_log(
        round_idx=2,
        total_iterations=5,
        ai_comment="",
        share_result="skip_low_engagement",
        share_detail="like_count=20<min_like_count=1000",
        like_count=20,
        share_count=5000,
        ratio=250.0,
        task_status="skip_low_engagement",
        comment_result="skip_not_share_candidate",
    )

    assert "安全门: skip_low_engagement (like_count=20<min_like_count=1000)" in line
    assert "任务状态: skip_low_engagement" in line
    assert "评论生成/评论发送: 否/否" in line


def test_runtime_log_identifies_promotional_hard_block() -> None:
    line = format_runtime_round_log(
        round_idx=1,
        total_iterations=1,
        ai_comment="",
        share_result="skip_promo",
        share_detail="promo_text_rules=click_link_cta",
        like_count=2000,
        share_count=3000,
        ratio=1.5,
        task_status="skip_promo",
        comment_result="skip_not_share_candidate",
    )

    assert "视频类型: 推广内容" in line
    assert "安全门: skip_promo (promo_text_rules=click_link_cta)" in line
