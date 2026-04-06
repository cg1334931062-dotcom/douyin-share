from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentGateDecision:
    blocked: bool
    result: str
    detail: str
    task_status: str


def evaluate_hard_content_gate(
    *,
    live_by_hint: bool,
    ad_badge: bool,
) -> ContentGateDecision:
    if live_by_hint:
        return ContentGateDecision(
            blocked=True,
            result="skip_live",
            detail="live_content_hard_block",
            task_status="live_skipped",
        )

    if ad_badge:
        return ContentGateDecision(
            blocked=True,
            result="skip_ad",
            detail="ad_badge=True;rule=author_badge_only",
            task_status="skip_ad",
        )

    return ContentGateDecision(
        blocked=False,
        result="-",
        detail="-",
        task_status="-",
    )
