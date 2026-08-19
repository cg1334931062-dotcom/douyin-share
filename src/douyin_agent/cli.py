"""Stable, automation-friendly command line entry point.

The demo mode is fully offline and is the recommended first command for both
people and agents.  Scan mode is an explicit bridge to the existing browser
runner and keeps all real-site safety switches opt-in.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Sequence

from .commenting import CommentGenerator, CommentPolicyEngine
from .classifier import ContentClassifier
from .config import PolicyConfig, RunnerConfig
from .models import ContentSnapshot, SemanticSummary, WorkflowResult
from .state_machine import DouyinWorkflowRunner


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        payload = {
            "schema_version": "1",
            "task_status": "invalid_args",
            "mode": None,
            "completed_rounds": 0,
            "errors": [message],
        }
        print(json.dumps(payload, ensure_ascii=False))
        raise SystemExit(2)


class _DemoBrowser:
    def __init__(self, snapshot: ContentSnapshot) -> None:
        self.snapshot = snapshot
        self.posted: list[str] = []

    def open_home(self) -> None:
        return None

    def ensure_login(self) -> bool:
        return True

    def current_snapshot(self) -> ContentSnapshot:
        return self.snapshot

    def next_item(self, reason: str) -> None:
        return None

    def capture_frames(self, snapshot: ContentSnapshot) -> tuple[str, ...]:
        return ("美食 教程 家常菜", "锅气很足", "配菜讲解清晰")

    def post_comment(self, comment: str) -> bool:
        self.posted.append(comment)
        return True


class _DemoVision:
    def understand(self, snapshot: ContentSnapshot) -> SemanticSummary:
        return SemanticSummary(
            topic="家常菜做法",
            objects=("火候", "调味"),
            tone="positive",
            sensitive_flag=False,
            ocr_snippets=snapshot.frame_texts,
        )


class _DemoApprover:
    def approve(self, comment: str, snapshot: ContentSnapshot) -> bool:
        # Demo mode must never simulate an approved external action.
        return False


def _result_payload(result: WorkflowResult) -> dict[str, object]:
    return {
        "outcome": result.outcome,
        "states": list(result.states),
        "comment": result.comment,
        "classification": (
            {
                "kind": result.classification.kind,
                "confidence": result.classification.confidence,
                "reasons": list(result.classification.reasons),
            }
            if result.classification
            else None
        ),
        "policy": (
            {"allowed": result.policy.allowed, "reasons": list(result.policy.reasons)}
            if result.policy
            else None
        ),
    }


def _run_demo(iterations: int) -> dict[str, object]:
    snapshot = ContentSnapshot(
        video_id="demo-1",
        url="https://www.douyin.com/",
        dom_text="点赞 评论 收藏 分享",
        dom_markers=("comment_button", "like_button", "share_button"),
    )
    browser = _DemoBrowser(snapshot)
    runner = DouyinWorkflowRunner(
        browser=browser,
        vision=_DemoVision(),
        approver=_DemoApprover(),
        classifier=ContentClassifier(),
        generator=CommentGenerator(),
        policy=CommentPolicyEngine(PolicyConfig()),
        config=RunnerConfig(auto_post=False),
    )
    results: list[WorkflowResult] = []
    for _ in range(iterations):
        results.append(runner.run_once(now=datetime.now(timezone.utc)))

    outcomes = Counter(result.outcome for result in results)
    return {
        "schema_version": "1",
        "task_status": "completed",
        "mode": "demo",
        "side_effects_enabled": False,
        "requested_rounds": iterations,
        "completed_rounds": len(results),
        "outcomes": dict(outcomes),
        "skip_reasons": {key: value for key, value in outcomes.items() if key.startswith(("skip_", "blocked_", "manual_"))},
        "share_results": {},
        "errors": [],
        "rounds": [_result_payload(result) for result in results],
    }


def _scan_command(args: argparse.Namespace) -> list[str]:
    root = Path(__file__).resolve().parents[2]
    runner = root / "examples" / "run_real_site_once.py"
    command = [
        sys.executable,
        str(runner),
        "--mode",
        "scan",
        "--iterations",
        str(args.iterations),
        "--profile-dir",
        args.profile_dir,
        "--no-log-window",
    ]
    if args.require_login:
        command.append("--require-login")
    if args.headless:
        command.append("--headless")
    if args.enable_post:
        command.append("--enable-post")
    if args.enable_share:
        command.append("--enable-share")
    if args.share_target:
        command.extend(["--share-target", args.share_target])
    if args.comment_by_content:
        command.append("--comment-by-content")
    command.append("--use-ai-comment" if args.use_ai_comment else "--no-ai-comment")
    return command


def _run_scan(args: argparse.Namespace) -> dict[str, object]:
    completed = subprocess.run(_scan_command(args), capture_output=True, text=True)
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    rounds = [int(value) for value in re.findall(r"\[round (\d+)\]", output)]
    share_results = Counter(re.findall(r"share_result=([a-z_]+)", output))
    task_statuses = Counter(re.findall(r"task_status=([a-z_]+)", output))
    payload: dict[str, object] = {
        "schema_version": "1",
        "task_status": "completed" if completed.returncode == 0 else "failed",
        "mode": "scan",
        "side_effects_enabled": bool(args.enable_post or args.enable_share),
        "requested_rounds": args.iterations,
        "completed_rounds": max(rounds, default=0),
        "outcomes": {},
        "skip_reasons": dict(task_statuses),
        "share_results": dict(share_results),
        "errors": [] if completed.returncode == 0 else [output[-2000:] or "scan failed"],
    }
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        prog="python -m douyin_agent",
        description="安全优先的抖音扫描助手 CLI；默认运行离线 demo。",
    )
    parser.add_argument("--mode", choices=("demo", "scan"), default="demo")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--require-login", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--profile-dir", default=".playwright_profile")
    parser.add_argument("--enable-post", action="store_true", help="显式开启真实评论发送")
    parser.add_argument("--enable-share", action="store_true", help="显式开启真实分享")
    parser.add_argument("--share-target", default="")
    parser.add_argument("--comment-by-content", action="store_true")
    parser.add_argument("--use-ai-comment", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.iterations <= 0:
        parser.error("--iterations must be greater than 0")
    if args.enable_share and not args.share_target:
        parser.error("--share-target is required when --enable-share is set")

    payload = _run_demo(args.iterations) if args.mode == "demo" else _run_scan(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["task_status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
