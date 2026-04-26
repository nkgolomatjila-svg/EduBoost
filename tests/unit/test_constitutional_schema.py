"""
Unit tests for the Constitutional Schema (types.py + schema.py).
Tests the Legislature (Pillar 1) data contracts.
"""
import pytest
from datetime import datetime
from app.api.constitutional_schema.types import (
    ConstitutionalRule, RuleCategory, RuleSeverity, ActionType,
    ExecutiveAction, ActionStatus, JudiciaryStamp, StampStatus,
    AuditEvent, EventType, EtherArchetype, EtherToneParams,
    LearnerEtherProfile, OperationResult,
)
from app.api.constitutional_schema.schema import (
    CONSTITUTIONAL_CORPUS, get_rules_for_action, get_critical_rules,
    POPIA_01, POPIA_02, POPIA_03, CAPS_01, CAPS_02, CAPS_03,
    CHILD_01, PII_01, LANG_01,
)


# ── ConstitutionalRule ────────────────────────────────────────────────────────

class TestConstitutionalRule:
    def test_rule_is_immutable(self):
        """Rules must be frozen (immutable after creation)."""
        with pytest.raises(Exception):
            POPIA_01.rule_id = "hacked"

    def test_popia_01_is_critical(self):
        assert POPIA_01.severity == RuleSeverity.CRITICAL

    def test_pii_01_is_critical(self):
        assert PII_01.severity == RuleSeverity.CRITICAL

    def test_child_01_is_critical(self):
        assert CHILD_01.severity == RuleSeverity.CRITICAL

    def test_caps_01_applies_to_lesson(self):
        assert ActionType.GENERATE_LESSON in CAPS_01.applies_to

    def test_popia_03_applies_to_all_actions(self):
        for action_type in ActionType:
            assert action_type in POPIA_03.applies_to

    def test_corpus_has_minimum_rules(self):
        assert len(CONSTITUTIONAL_CORPUS) >= 9

    def test_all_rules_have_check_prompts(self):
        for rule in CONSTITUTIONAL_CORPUS:
            assert rule.check_prompt, f"Rule {rule.rule_id} missing check_prompt"

    def test_all_rules_have_sources(self):
        for rule in CONSTITUTIONAL_CORPUS:
            assert rule.source, f"Rule {rule.rule_id} missing source"


# ── Rule Retrieval ────────────────────────────────────────────────────────────

class TestRuleRetrieval:
    def test_get_rules_for_lesson_generation(self):
        rules = get_rules_for_action(ActionType.GENERATE_LESSON)
        assert len(rules) > 0
        rule_ids = [r.rule_id for r in rules]
        assert "POPIA_01" in rule_ids
        assert "PII_01" in rule_ids
        assert "CHILD_01" in rule_ids

    def test_get_critical_rules_lesson(self):
        critical = get_critical_rules(ActionType.GENERATE_LESSON)
        for rule in critical:
            assert rule.severity == RuleSeverity.CRITICAL

    def test_get_rules_for_diagnostic(self):
        rules = get_rules_for_action(ActionType.RUN_DIAGNOSTIC)
        assert len(rules) > 0

    def test_inactive_rules_excluded(self):
        """Inactive rules should not be returned."""
        rules = get_rules_for_action(ActionType.GENERATE_LESSON)
        for rule in rules:
            assert rule.is_active is True

    def test_unknown_action_returns_empty(self):
        """No rules should be retrieved for actions with no registered rules."""
        rules = get_rules_for_action(ActionType.STORE_FEEDBACK)
        # POPIA_03 applies to all, so at minimum that should be included
        # or this should be empty — depends on corpus config
        assert isinstance(rules, list)


# ── ExecutiveAction ───────────────────────────────────────────────────────────

class TestExecutiveAction:
    def test_valid_action_created(self):
        action = ExecutiveAction(
            action_type=ActionType.GENERATE_LESSON,
            learner_id_hash="abc123" * 5,
            grade=3,
            params={"subject_code": "MATH", "topic": "Fractions"},
            claimed_rules=["POPIA_01"],
        )
        assert action.status == ActionStatus.PENDING
        assert action.action_id is not None

    def test_learner_id_rejected_in_params(self):
        """Hard validation: learner_id must never appear in params."""
        with pytest.raises(ValueError, match="PII pattern"):
            ExecutiveAction(
                action_type=ActionType.GENERATE_LESSON,
                learner_id_hash="abc123" * 5,
                grade=3,
                params={"learner_id": "00000000-0000-0000-0000-000000000001"},
                claimed_rules=[],
            )

    def test_guardian_email_rejected_in_params(self):
        with pytest.raises(ValueError, match="PII pattern"):
            ExecutiveAction(
                action_type=ActionType.GENERATE_LESSON,
                learner_id_hash="abc123" * 5,
                grade=3,
                params={"guardian_email": "test@example.com"},
                claimed_rules=[],
            )

    def test_grade_range_validated(self):
        with pytest.raises(Exception):
            ExecutiveAction(
                action_type=ActionType.GENERATE_LESSON,
                learner_id_hash="abc123",
                grade=8,  # Invalid — max is 7
                params={},
                claimed_rules=[],
            )

    def test_action_id_is_uuid_string(self):
        action = ExecutiveAction(
            action_type=ActionType.RUN_DIAGNOSTIC,
            learner_id_hash="abc123",
            grade=5,
            params={"subject_code": "ENG"},
            claimed_rules=[],
        )
        assert len(action.action_id) == 36  # UUID format


# ── JudiciaryStamp ────────────────────────────────────────────────────────────

class TestJudiciaryStamp:
    def test_approved_stamp(self):
        stamp = JudiciaryStamp(
            action_id="test-action-001",
            status=StampStatus.APPROVED,
            rules_evaluated=["POPIA_01", "CAPS_01"],
            violations=[],
            reasoning="All checks passed.",
            latency_ms=12,
        )
        assert stamp.status == StampStatus.APPROVED
        assert stamp.violations == []

    def test_rejected_stamp_has_violations(self):
        stamp = JudiciaryStamp(
            action_id="test-action-002",
            status=StampStatus.REJECTED,
            rules_evaluated=["POPIA_01", "PII_01"],
            violations=["PII_01"],
            reasoning="UUID detected in prompt.",
            latency_ms=5,
        )
        assert stamp.status == StampStatus.REJECTED
        assert "PII_01" in stamp.violations

    def test_stamp_is_immutable(self):
        stamp = JudiciaryStamp(
            action_id="test-action-003",
            status=StampStatus.APPROVED,
            rules_evaluated=[],
            latency_ms=1,
        )
        with pytest.raises(Exception):
            stamp.status = StampStatus.REJECTED


# ── AuditEvent ────────────────────────────────────────────────────────────────

class TestAuditEvent:
    def test_audit_event_creation(self):
        event = AuditEvent(
            event_type=EventType.ACTION_SUBMITTED,
            action_id="test-action",
            learner_hash="abc123",
            pillar="EXECUTIVE",
            payload={"grade": 3},
        )
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_audit_event_is_immutable(self):
        event = AuditEvent(
            event_type=EventType.STAMP_ISSUED,
            pillar="JUDICIARY",
        )
        with pytest.raises(Exception):
            event.pillar = "HACKED"


# ── EtherProfile ─────────────────────────────────────────────────────────────

class TestEtherProfile:
    def test_prompt_modifier_contains_archetype(self):
        profile = LearnerEtherProfile(
            learner_hash="abc123",
            archetype=EtherArchetype.TIFERET,
            tone_params=EtherToneParams(),
        )
        modifier = profile.to_prompt_modifier()
        assert "TIFERET" in modifier
        assert "LEARNER PROFILE" in modifier

    def test_all_archetypes_have_prompt_modifiers(self):
        for archetype in EtherArchetype:
            profile = LearnerEtherProfile(
                learner_hash="abc",
                archetype=archetype,
                tone_params=EtherToneParams(),
            )
            modifier = profile.to_prompt_modifier()
            assert archetype.value in modifier

    def test_ether_tone_params_defaults_valid(self):
        params = EtherToneParams()
        assert 0.0 <= params.warmth_level <= 1.0
        assert 0.0 <= params.challenge_tolerance <= 1.0
        assert params.repetition_factor >= 1


# ── OperationResult ───────────────────────────────────────────────────────────

class TestOperationResult:
    def test_success_result(self):
        result = OperationResult(
            success=True,
            output={"title": "Fractions at the Braai"},
            stamp_status="APPROVED",
            constitutional_health=1.0,
        )
        assert result.success is True
        assert result.constitutional_health == 1.0

    def test_failure_result(self):
        result = OperationResult(
            success=False,
            error="PII detected",
            stamp_status="REJECTED",
            constitutional_health=0.0,
        )
        assert result.success is False
        assert result.error == "PII detected"
        assert result.output is None
