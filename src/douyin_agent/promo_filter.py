from __future__ import annotations

from dataclasses import dataclass
import re


PROMO_TYPE_HINTS = (
    "产品推广",
    "商品推广",
    "品牌推广",
    "广告营销",
    "种草带货",
    "带货",
    "导购",
    "好物推荐",
)

PROMO_STYLE_HINTS = (
    "直接引导",
    "购买引导",
    "促销",
    "转化导向",
    "口播卖货",
    "强引导",
)

PROMO_TEXT_RULES: tuple[tuple[str, str], ...] = (
    (r"点击(?:下方|左下角|右下角|链接)", "click_link_cta"),
    (r"(?:立即|直接|赶紧)?下单", "place_order_cta"),
    (r"(?:领|抢)[^\s，。]{0,6}券", "coupon_cta"),
    (r"(?:橱窗|小黄车|购物车)", "shopping_entry"),
    (r"(?:官方)?旗舰店", "brand_store"),
    (r"(?:购买|下单)链接", "purchase_link"),
    (r"(?:拍下|入手|购买)同款", "buy_same_item"),
    (r"(?:限时|今日|现在)[^\s，。]{0,6}(?:优惠|折扣|秒杀)", "promo_offer"),
    (r"(?:店铺|商品)链接", "store_link"),
)


@dataclass(frozen=True)
class PromotionalDecision:
    blocked: bool
    detail: str


def detect_promotional_content(
    *,
    text: str,
    types: tuple[str, ...] = (),
    styles: tuple[str, ...] = (),
) -> PromotionalDecision:
    normalized = " ".join(text.split())
    type_hits = tuple(item for item in types if any(hint in item for hint in PROMO_TYPE_HINTS))
    style_hits = tuple(item for item in styles if any(hint in item for hint in PROMO_STYLE_HINTS))
    text_hits = tuple(
        label
        for pattern, label in PROMO_TEXT_RULES
        if re.search(pattern, normalized, flags=re.IGNORECASE)
    )

    blocked = bool(type_hits) or bool(text_hits) or (bool(style_hits) and ("推广" in normalized))
    if not blocked:
        return PromotionalDecision(blocked=False, detail="-")

    detail_parts: list[str] = []
    if type_hits:
        detail_parts.append("promo_types=" + ",".join(type_hits))
    if style_hits:
        detail_parts.append("promo_styles=" + ",".join(style_hits))
    if text_hits:
        detail_parts.append("promo_text_rules=" + ",".join(text_hits))
    return PromotionalDecision(blocked=True, detail=";".join(detail_parts))
