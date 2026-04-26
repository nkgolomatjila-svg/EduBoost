"""EduBoost SA — Constitutional corpus (Legislature)."""
from __future__ import annotations

from typing import Iterable

from app.api.constitutional_schema.types import (
    ActionType,
    ConstitutionalRule,
    RuleCategory,
    RuleSeverity,
)

_ALL_ACTIONS = frozenset(ActionType)


def _rule(
    rule_id: str,
    category: RuleCategory,
    severity: RuleSeverity,
    check_prompt: str,
    source: str,
    applies_to: Iterable[ActionType],
    is_active: bool = True,
) -> ConstitutionalRule:
    return ConstitutionalRule(
        rule_id=rule_id,
        category=category,
        severity=severity,
        check_prompt=check_prompt,
        source=source,
        applies_to=frozenset(applies_to),
        is_active=is_active,
    )


POPIA_01 = _rule(
    "POPIA_01",
    RuleCategory.POPIA,
    RuleSeverity.CRITICAL,
    "Verify no learner-identifying tokens reach external processors.",
    "POPIA Act 4 of 2013 — Processing limitation",
    (ActionType.GENERATE_LESSON, ActionType.RUN_DIAGNOSTIC),
)
POPIA_02 = _rule(
    "POPIA_02",
    RuleCategory.POPIA,
    RuleSeverity.HIGH,
    "Ensure lawful basis and minimality of personal data processed.",
    "POPIA — Purpose limitation",
    (ActionType.GENERATE_LESSON,),
)
POPIA_03 = _rule(
    "POPIA_03",
    RuleCategory.POPIA,
    RuleSeverity.HIGH,
    "Reject undeclared or excessive data fields in action payloads.",
    "POPIA — Data minimisation",
    _ALL_ACTIONS,
)
CAPS_01 = _rule(
    "CAPS_01",
    RuleCategory.CAPS,
    RuleSeverity.HIGH,
    "Lesson content must align to CAPS band for the stated grade.",
    "CAPS curriculum alignment",
    (ActionType.GENERATE_LESSON,),
)
CAPS_02 = _rule(
    "CAPS_02",
    RuleCategory.CAPS,
    RuleSeverity.MEDIUM,
    "Assessments must respect subject and grade scope.",
    "CAPS scope",
    (ActionType.RUN_DIAGNOSTIC,),
)
CAPS_03 = _rule(
    "CAPS_03",
    RuleCategory.CAPS,
    RuleSeverity.HIGH,
    "Knowledge-gap remediation must declare a valid prior grade strictly below current grade.",
    "CAPS progression",
    (ActionType.GENERATE_LESSON,),
)
CHILD_01 = _rule(
    "CHILD_01",
    RuleCategory.CHILD,
    RuleSeverity.CRITICAL,
    "Content must be age-appropriate for primary learners (Grade R–7).",
    "Children's Act — Best interests of the child",
    (ActionType.GENERATE_LESSON,),
)
PII_01 = _rule(
    "PII_01",
    RuleCategory.PII,
    RuleSeverity.CRITICAL,
    "No UUIDs, emails, phone numbers, or SA ID numbers in LLM-bound prompts.",
    "POPIA — Pseudonymisation / LLM firewall",
    (ActionType.GENERATE_LESSON, ActionType.RUN_DIAGNOSTIC),
)
LANG_01 = _rule(
    "LANG_01",
    RuleCategory.LANGUAGE,
    RuleSeverity.MEDIUM,
    "Respect declared home language and reading level.",
    "CAPS — Home language",
    (ActionType.GENERATE_LESSON,),
)

CONSTITUTIONAL_CORPUS: tuple[ConstitutionalRule, ...] = (
    POPIA_01,
    POPIA_02,
    POPIA_03,
    CAPS_01,
    CAPS_02,
    CAPS_03,
    CHILD_01,
    PII_01,
    LANG_01,
)


def get_rules_for_action(action_type: ActionType) -> list[ConstitutionalRule]:
    return [r for r in CONSTITUTIONAL_CORPUS if r.is_active and action_type in r.applies_to]


def get_critical_rules(action_type: ActionType) -> list[ConstitutionalRule]:
    return [r for r in get_rules_for_action(action_type) if r.severity == RuleSeverity.CRITICAL]


def get_rule(rule_id: str) -> ConstitutionalRule | None:
    for r in CONSTITUTIONAL_CORPUS:
        if r.rule_id == rule_id:
            return r
    return None
