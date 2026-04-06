from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import tomllib
from typing import Literal

ShareThresholdMode = Literal["any", "all"]


@dataclass(frozen=True)
class ShareDecision:
    should_share: bool
    ratio: float
    detail: str


@dataclass(frozen=True)
class ShareRuleConfig:
    min_like_count: int = 1_000
    min_share_count: int = 200_000
    min_share_like_ratio: float = 0.5
    share_count_enabled: bool = True
    share_like_ratio_enabled: bool = True
    threshold_mode: ShareThresholdMode = "any"

    def __post_init__(self) -> None:
        if self.min_like_count < 0:
            raise ValueError("min_like_count must be >= 0")
        if self.min_share_count < 0:
            raise ValueError("min_share_count must be >= 0")
        if self.min_share_like_ratio < 0:
            raise ValueError("min_share_like_ratio must be >= 0")
        if self.threshold_mode not in {"any", "all"}:
            raise ValueError("threshold_mode must be 'any' or 'all'")
        if not self.share_count_enabled and not self.share_like_ratio_enabled:
            raise ValueError("at least one share rule must be enabled")

    def with_overrides(
        self,
        *,
        min_like_count: int | None = None,
        min_share_count: int | None = None,
        min_share_like_ratio: float | None = None,
        threshold_mode: ShareThresholdMode | None = None,
    ) -> ShareRuleConfig:
        updates: dict[str, object] = {}
        if min_like_count is not None:
            updates["min_like_count"] = min_like_count
        if min_share_count is not None:
            updates["min_share_count"] = min_share_count
        if min_share_like_ratio is not None:
            updates["min_share_like_ratio"] = min_share_like_ratio
        if threshold_mode is not None:
            updates["threshold_mode"] = threshold_mode
        if not updates:
            return self
        return replace(self, **updates)

    def describe(self) -> str:
        checks: list[str] = []
        if self.share_count_enabled:
            checks.append(f"share_count>{self.min_share_count}")
        if self.share_like_ratio_enabled:
            checks.append(f"ratio>{self.min_share_like_ratio:.6f}")
        joiner = " OR " if self.threshold_mode == "any" else " AND "
        return f"like_count>={self.min_like_count}; rules={joiner.join(checks)}"

    def evaluate(self, *, share_count: int, like_count: int) -> ShareDecision:
        ratio = (share_count / like_count) if like_count > 0 else 0.0
        if like_count < self.min_like_count:
            return ShareDecision(
                should_share=False,
                ratio=ratio,
                detail=(
                    f"like_count={like_count}<min_like_count={self.min_like_count};"
                    f"share_count={share_count};ratio={ratio:.6f}"
                ),
            )

        checks: list[tuple[str, bool]] = []
        if self.share_count_enabled:
            checks.append(
                (
                    f"share_count>{self.min_share_count}",
                    share_count > self.min_share_count,
                )
            )
        if self.share_like_ratio_enabled:
            checks.append(
                (
                    f"ratio>{self.min_share_like_ratio:.6f}",
                    ratio > self.min_share_like_ratio,
                )
            )

        if self.threshold_mode == "all":
            should_share = all(ok for _, ok in checks)
        else:
            should_share = any(ok for _, ok in checks)

        result_bits = ";".join(f"{name}={ok}" for name, ok in checks)
        detail = (
            f"like_count={like_count};share_count={share_count};ratio={ratio:.6f};"
            f"mode={self.threshold_mode};{result_bits}"
        )
        return ShareDecision(should_share=should_share, ratio=ratio, detail=detail)


def load_share_rule_config(path: str | Path) -> ShareRuleConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ValueError(f"share rule config not found: {config_path}")

    try:
        with config_path.open("rb") as fh:
            raw = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid TOML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"share rule config must be a TOML table: {config_path}")

    data = raw.get("share_rules", raw)
    if not isinstance(data, dict):
        raise ValueError(f"share_rules must be a TOML table: {config_path}")

    allowed_keys = {
        "min_like_count",
        "min_share_count",
        "min_share_like_ratio",
        "share_count_enabled",
        "share_like_ratio_enabled",
        "threshold_mode",
    }
    unknown_keys = sorted(key for key in data.keys() if key not in allowed_keys)
    if unknown_keys:
        raise ValueError(
            f"unknown share rule config key(s): {', '.join(unknown_keys)}"
        )

    defaults = ShareRuleConfig()
    return ShareRuleConfig(
        min_like_count=_coerce_int(
            data.get("min_like_count", defaults.min_like_count),
            name="min_like_count",
        ),
        min_share_count=_coerce_int(
            data.get("min_share_count", defaults.min_share_count),
            name="min_share_count",
        ),
        min_share_like_ratio=_coerce_float(
            data.get("min_share_like_ratio", defaults.min_share_like_ratio),
            name="min_share_like_ratio",
        ),
        share_count_enabled=_coerce_bool(
            data.get("share_count_enabled", defaults.share_count_enabled),
            name="share_count_enabled",
        ),
        share_like_ratio_enabled=_coerce_bool(
            data.get("share_like_ratio_enabled", defaults.share_like_ratio_enabled),
            name="share_like_ratio_enabled",
        ),
        threshold_mode=_coerce_mode(
            data.get("threshold_mode", defaults.threshold_mode),
            name="threshold_mode",
        ),
    )


def _coerce_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _coerce_float(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    return float(value)


def _coerce_bool(value: object, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _coerce_mode(value: object, *, name: str) -> ShareThresholdMode:
    if value not in {"any", "all"}:
        raise ValueError(f"{name} must be 'any' or 'all'")
    return value
