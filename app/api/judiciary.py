"""EduBoost SA — Judiciary (Pillar 3): constitutional review before side effects."""
from __future__ import annotations

import re
import time
from typing import Optional

from app.api.constitutional_schema.schema import get_rules_for_action
from app.api.constitutional_schema.types import (
    ActionType,
    ExecutiveAction,
    JudiciaryStamp,
    StampStatus,
)

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b0[67]\d{8}\b")
_SA_ID_RE = re.compile(r"\b\d{13}\b")

_LESSON_ALLOWED_KEYS = frozenset({
    "subject_code",
    "subject_label",
    "topic",
    "home_language",
    "learning_style_primary",
    "mastery_prior",
    "has_gap",
    "gap_grade",
    "sa_theme",
})

_judiciary: Optional["Judiciary"] = None


class Judiciary:
    def __init__(self, use_llm_review: bool = True) -> None:
        self.use_llm_review = use_llm_review
        self._total = 0
        self._rejections = 0

    def get_stats(self) -> dict:
        rate = 0.0 if self._total == 0 else (self._total - self._rejections) / self._total
        return {
            "total_stamps": self._total,
            "rejections": self._rejections,
            "approval_rate": round(rate, 4),
        }

    def _scan_prompts(self, system_prompt: Optional[str], user_prompt: Optional[str]) -> list[str]:
        violations: list[str] = []
        blob = f"{system_prompt or ''}\n{user_prompt or ''}"
        if _UUID_RE.search(blob):
            violations.append("PII_01")
        if _EMAIL_RE.search(blob):
            violations.append("PII_01")
        if _PHONE_RE.search(blob):
            violations.append("PII_01")
        if _SA_ID_RE.search(blob):
            violations.append("PII_01")
        return violations

    def _structural(self, action: ExecutiveAction) -> list[str]:
        violations: list[str] = []
        if action.action_type == ActionType.GENERATE_LESSON:
            keys = set(action.params.keys())
            if not keys.issubset(_LESSON_ALLOWED_KEYS):
                violations.append("POPIA_03")
                return violations
            if action.params.get("has_gap"):
                gg = action.params.get("gap_grade")
                if gg is None:
                    violations.append("CAPS_03")
                elif gg >= action.grade:
                    violations.append("CAPS_03")
        return violations

    async def review(
        self,
        action: ExecutiveAction,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> JudiciaryStamp:
        t0 = time.perf_counter()
        rules = [r.rule_id for r in get_rules_for_action(action.action_type)]
        violations: list[str] = list(dict.fromkeys(self._structural(action)))
        violations.extend(v for v in self._scan_prompts(system_prompt, user_prompt) if v not in violations)

        if violations:
            self._rejections += 1
            self._total += 1
            return JudiciaryStamp(
                action_id=action.action_id,
                status=StampStatus.REJECTED,
                rules_evaluated=rules,
                violations=violations,
                reasoning="Constitutional review rejected: " + ", ".join(violations),
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        self._total += 1
        return JudiciaryStamp(
            action_id=action.action_id,
            status=StampStatus.APPROVED,
            rules_evaluated=rules,
            violations=[],
            reasoning="All automated constitutional checks passed.",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )


def get_judiciary(use_llm_review: bool = True) -> Judiciary:
    global _judiciary
    if _judiciary is None:
        _judiciary = Judiciary(use_llm_review=use_llm_review)
    return _judiciary
