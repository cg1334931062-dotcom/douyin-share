from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyConfig:
    min_len: int = 8
    max_len: int = 30
    duplicate_similarity: float = 0.85
    max_comments_per_hour: int = 6
    banned_words: tuple[str, ...] = (
        "加我",
        "私信我",
        "返现",
        "刷单",
        "投资稳赚",
        "赌博",
        "彩票群",
        "带你赚钱",
    )


@dataclass(frozen=True)
class RunnerConfig:
    auto_post: bool = False
