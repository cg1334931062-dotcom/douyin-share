from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from .config import PolicyConfig
from .models import PolicyDecision, SemanticSummary


@dataclass
class CommentGenerator:
    min_len: int = 8
    max_len: int = 30

    def generate(
        self,
        summary: SemanticSummary,
        reference_comments: tuple[str, ...] = (),
        style: str = "neutral",
        recent_generated_comments: tuple[str, ...] = (),
    ) -> str:
        topic = summary.topic.strip() or "这个内容"
        tone = summary.tone.lower().strip()
        objects = "、".join(summary.objects[:2]) if summary.objects else ""

        if summary.sensitive_flag:
            templates = (
                "{topic}这个话题信息量很大，建议理性判断。",
                "关于{topic}，先核实信息再下结论更稳妥。",
                "{topic}讨论度很高，保持理性更重要。",
            )
            include_object_hint = False
        else:
            if style == "humorous":
                if tone in {"positive", "upbeat", "happy"}:
                    templates = (
                        "{topic}这段有点东西，笑着就学会了。",
                        "{topic}这条太会讲了，边笑边记笔记。",
                        "{topic}这波讲解很丝滑，脑子秒懂。",
                    )
                elif tone in {"critical", "serious"}:
                    templates = (
                        "{topic}这提醒太及时，差点就踩坑了。",
                        "{topic}这条像避坑地图，直接省事。",
                        "{topic}这一句点醒我了，真省学费。",
                    )
                else:
                    templates = (
                        "{topic}这条有梗又有料，挺上头。",
                        "{topic}看得我嘴角上扬，还挺实用。",
                        "{topic}这节奏可以，轻松但不水。",
                    )
            else:
                if tone in {"positive", "upbeat", "happy"}:
                    templates = (
                        "{topic}这个点很实用，学到了。",
                        "{topic}讲得挺清楚，收获不少。",
                        "{topic}这条内容很有参考价值。",
                    )
                elif tone in {"critical", "serious"}:
                    templates = (
                        "{topic}这个角度挺有价值，值得继续讨论。",
                        "关于{topic}的提醒很及时，感谢分享。",
                        "{topic}这点说得直白，确实值得注意。",
                    )
                else:
                    templates = (
                        "{topic}这个方向挺有意思。",
                        "{topic}这条看完有启发。",
                        "{topic}内容还挺实在。",
                    )
            include_object_hint = bool(objects)

        style_suffix = self._style_suffix(reference_comments, tone=tone)
        candidates: list[str] = []
        for template in self._ordered_templates(templates, topic):
            draft = template.format(topic=topic, obj=objects)
            if include_object_hint:
                draft = f"{draft} 尤其是{objects}这部分。"
            if style_suffix:
                draft = f"{draft} {style_suffix}"
            normalized = self._normalize_len(draft)
            if normalized not in candidates:
                candidates.append(normalized)

        for candidate in candidates:
            if not self._too_similar_to_recent(candidate, recent_generated_comments):
                return candidate

        anti_repeat = self._normalize_len(
            self._anti_repeat_line(topic=topic, objects=objects, style=style, tone=tone)
        )
        if not self._too_similar_to_recent(anti_repeat, recent_generated_comments):
            return anti_repeat
        return candidates[0]

    def _pick_template(self, templates: tuple[str, ...], topic: str) -> str:
        idx = sum(ord(ch) for ch in topic) % len(templates)
        return templates[idx]

    def _ordered_templates(self, templates: tuple[str, ...], topic: str) -> tuple[str, ...]:
        if not templates:
            return ()
        start = sum(ord(ch) for ch in topic) % len(templates)
        return tuple(templates[(start + offset) % len(templates)] for offset in range(len(templates)))

    def _style_suffix(self, reference_comments: tuple[str, ...], tone: str) -> str:
        if not reference_comments:
            return ""
        merged = " ".join(reference_comments)

        if "哈哈" in merged or "笑死" in merged:
            return "哈哈这个细节很有画面感。"
        if "学到了" in merged or "收藏" in merged:
            return "先收藏，回头再复盘。"
        if "绝了" in merged or "太强" in merged:
            return "这个点确实有东西。"
        if "真实" in merged or "同感" in merged:
            return "这个我也挺有共鸣。"
        if tone in {"critical", "serious"}:
            return "这个提醒很及时。"
        return ""

    def _too_similar_to_recent(
        self,
        comment: str,
        recent_generated_comments: tuple[str, ...],
        threshold: float = 0.84,
    ) -> bool:
        candidate = comment.strip()
        if not candidate:
            return False
        for old in recent_generated_comments[:10]:
            previous = old.strip()
            if not previous:
                continue
            if candidate == previous:
                return True
            similarity = SequenceMatcher(a=candidate, b=previous).ratio()
            if similarity >= threshold:
                return True
        return False

    def _anti_repeat_line(self, topic: str, objects: str, style: str, tone: str) -> str:
        if style == "humorous":
            if tone in {"critical", "serious"}:
                options = (
                    f"{topic}这条预警拉满，差点就中招。",
                    f"{topic}这波提醒够硬核，省下冤枉路。",
                    f"{topic}这个避坑角度太实在了。",
                )
            else:
                options = (
                    f"{topic}这条反差感很强，越看越上头。",
                    f"{topic}这思路挺新，笑点和干货都在线。",
                    f"{topic}这波细节拿捏住了，挺会整活。",
                )
        else:
            if tone in {"critical", "serious"}:
                options = (
                    f"{topic}这条提醒很有价值，确实要注意。",
                    f"{topic}这个角度很关键，避免踩坑了。",
                    f"{topic}这点说得很到位，值得留意。",
                )
            else:
                options = (
                    f"{topic}这个角度挺新，内容很实在。",
                    f"{topic}这条信息密度不错，有收获。",
                    f"{topic}这段表达很清楚，容易理解。",
                )

        index_seed = sum(ord(ch) for ch in (topic + objects + tone))
        line = options[index_seed % len(options)]
        if objects:
            line = f"{line} {objects}这块尤其清楚。"
        return line

    def _normalize_len(self, text: str) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) < self.min_len:
            cleaned = (cleaned + " 很有启发。").strip()
        if len(cleaned) > self.max_len:
            cleaned = cleaned[: self.max_len]
        return cleaned


@dataclass
class CommentPolicyEngine:
    config: PolicyConfig

    def evaluate(
        self,
        comment: str,
        recent_comments: tuple[str, ...],
        recent_post_times: tuple[datetime, ...],
        now: datetime,
    ) -> PolicyDecision:
        reasons: list[str] = []

        if len(comment) < self.config.min_len:
            reasons.append("comment_too_short")
        if len(comment) > self.config.max_len:
            reasons.append("comment_too_long")

        lowered = comment.lower()
        for banned in self.config.banned_words:
            if banned.lower() in lowered:
                reasons.append(f"contains_banned_word:{banned}")
                break

        for old in recent_comments:
            similarity = SequenceMatcher(a=comment, b=old).ratio()
            if similarity >= self.config.duplicate_similarity:
                reasons.append(f"too_similar:{similarity:.2f}")
                break

        hour_ago = now - timedelta(hours=1)
        recent_count = sum(1 for ts in recent_post_times if ts >= hour_ago)
        if recent_count >= self.config.max_comments_per_hour:
            reasons.append("hourly_quota_exceeded")

        return PolicyDecision(allowed=not reasons, reasons=tuple(reasons))
