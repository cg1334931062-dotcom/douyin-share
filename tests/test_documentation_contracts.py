from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_document(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_readme_documents_safe_defaults_and_offline_regression() -> None:
    readme = _read_document("README.md")

    assert "默认高风险动作是关闭的" in readme
    assert "`启用分享` 控制“是否真实执行分享动作”" in readme
    assert "`启用真实评论发送` 只控制“评论是否真的点发送”" in readme
    assert "python3 -m pytest -q" in readme
    assert "这些测试不访问真实站点，也不会打开浏览器、调用 LLM、发送评论或分享内容。" in readme


def test_handoff_documents_m3_safety_regression_contract() -> None:
    handoff = _read_document("PROJECT_HANDOFF.md")

    assert "### 8.0 M3 regression acceptance" in handoff
    assert "python3 -m pytest -q" in handoff
    assert "does not open a real browser, call an LLM, post comments, or share content" in handoff
    assert "Live and author-area ad-badge content are hard-blocked" in handoff
    assert "omits `--enable-share` and `--enable-post`" in handoff
