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
    live_by_badge: bool = False,
) -> ContentGateDecision:
    live_sources: list[str] = []
    if live_by_hint:
        live_sources.append("room_hint")
    if live_by_badge:
        live_sources.append("live_badge")
    if live_sources:
        return ContentGateDecision(
            blocked=True,
            result="skip_live",
            detail=f"live_content_hard_block;source={'+'.join(live_sources)}",
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
