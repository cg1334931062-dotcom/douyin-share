from __future__ import annotations

import json

import pytest

from douyin_agent.cli import main


def test_demo_returns_machine_readable_success_and_safe_defaults(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--mode", "demo", "--iterations", "2"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["task_status"] == "completed"
    assert payload["mode"] == "demo"
    assert payload["completed_rounds"] == 2
    assert payload["side_effects_enabled"] is False
    assert payload["errors"] == []


def test_invalid_iterations_returns_json_error_and_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--mode", "demo", "--iterations", "0"])
    assert exc_info.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["task_status"] == "invalid_args"
    assert "iterations" in payload["errors"][0]


def test_share_requires_explicit_target(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--mode", "scan", "--enable-share"])
    assert exc_info.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["task_status"] == "invalid_args"
    assert "share-target" in payload["errors"][0]
