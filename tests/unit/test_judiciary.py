"""
Unit tests for the Judiciary (Pillar 3).
Tests constitutional review, PII scanning, and stamp issuance.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.api.constitutional_schema.types import (
    ExecutiveAction, ActionType, JudiciaryStamp, StampStatus,
)
from app.api.judiciary import Judiciary, get_judiciary


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_action(
    action_type=ActionType.GENERATE_LESSON,
    grade=3,
    params=None,
):
    if params is None:
        params = {
            "subject_code": "MATH",
            "subject_label": "Mathematics",
            "topic": "Fractions",
            "home_language": "English",
            "learning_style_primary": "visual",
            "mastery_prior": 0.38,
        }
    return ExecutiveAction(
        action_type=action_type,
        learner_id_hash="a" * 32,
        grade=grade,
        params=params,
        claimed_rules=[],
    )


# ── PII Scanning ──────────────────────────────────────────────────────────────

class TestPIIScanning:
    @pytest.mark.asyncio
    async def test_uuid_in_system_prompt_rejected(self):
        """A UUID in the system prompt must cause immediate REJECTION."""
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(
            action=action,
            system_prompt="Learner 00000000-0000-0000-0000-000000000001 is ready",
        )
        assert stamp.status == StampStatus.REJECTED
        assert "PII_01" in stamp.violations

    @pytest.mark.asyncio
    async def test_uuid_in_user_prompt_rejected(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(
            action=action,
            user_prompt="Generate lesson for 12345678-1234-1234-1234-123456789012",
        )
        assert stamp.status == StampStatus.REJECTED
        assert "PII_01" in stamp.violations

    @pytest.mark.asyncio
    async def test_email_in_prompt_rejected(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(
            action=action,
            system_prompt="Parent email: nomvula@gmail.com",
        )
        assert stamp.status == StampStatus.REJECTED

    @pytest.mark.asyncio
    async def test_sa_id_number_in_prompt_rejected(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(
            action=action,
            user_prompt="Learner SA ID: 9001015009087",
        )
        assert stamp.status == StampStatus.REJECTED

    @pytest.mark.asyncio
    async def test_clean_prompts_pass_pii_scan(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(
            action=action,
            system_prompt="You are EduBoost, a South African educational assistant.",
            user_prompt="Generate a Grade 3 Mathematics lesson about Fractions.",
        )
        assert "PII_01" not in stamp.violations
        assert "POPIA_01" not in stamp.violations

    @pytest.mark.asyncio
    async def test_no_prompts_passes_pii_scan(self):
        """No prompts provided → PII scan trivially passes."""
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(action=action)
        assert stamp.status in {StampStatus.APPROVED, StampStatus.REJECTED}
        # Should not be rejected for PII if no prompts provided
        assert "PII_01" not in stamp.violations


# ── Structural Validation ─────────────────────────────────────────────────────

class TestStructuralValidation:
    @pytest.mark.asyncio
    async def test_has_gap_without_gap_grade_rejected(self):
        """has_gap=True with no gap_grade must fail CAPS_03."""
        j = Judiciary(use_llm_review=False)
        action = make_action(params={
            "subject_code": "MATH",
            "subject_label": "Mathematics",
            "topic": "Fractions",
            "has_gap": True,
            "gap_grade": None,  # Missing!
        })
        stamp = await j.review(action=action)
        assert stamp.status == StampStatus.REJECTED
        assert "CAPS_03" in stamp.violations

    @pytest.mark.asyncio
    async def test_gap_grade_equal_to_grade_rejected(self):
        """gap_grade must be strictly less than current grade."""
        j = Judiciary(use_llm_review=False)
        action = make_action(
            grade=3,
            params={
                "subject_code": "MATH",
                "topic": "Fractions",
                "has_gap": True,
                "gap_grade": 3,  # Same as current grade — invalid
            }
        )
        stamp = await j.review(action=action)
        assert stamp.status == StampStatus.REJECTED
        assert "CAPS_03" in stamp.violations

    @pytest.mark.asyncio
    async def test_valid_gap_grade_passes(self):
        """has_gap=True with valid gap_grade < grade should pass structural check."""
        j = Judiciary(use_llm_review=False)
        action = make_action(
            grade=3,
            params={
                "subject_code": "MATH",
                "subject_label": "Mathematics",
                "topic": "Fractions",
                "has_gap": True,
                "gap_grade": 2,
                "mastery_prior": 0.3,
                "home_language": "English",
            }
        )
        stamp = await j.review(action=action)
        assert "CAPS_03" not in stamp.violations

    @pytest.mark.asyncio
    async def test_unexpected_param_keys_flagged(self):
        """Extra keys not in the allowed set trigger POPIA_03."""
        j = Judiciary(use_llm_review=False)
        action = make_action(params={
            "subject_code": "MATH",
            "topic": "Fractions",
            "full_name": "Sipho Dlamini",  # NOT allowed
        })
        stamp = await j.review(action=action)
        assert stamp.status == StampStatus.REJECTED
        assert "POPIA_03" in stamp.violations

    @pytest.mark.asyncio
    async def test_clean_lesson_params_approved(self):
        """Fully clean params should be APPROVED (no LLM review)."""
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(
            action=action,
            system_prompt="You are EduBoost.",
            user_prompt="Grade 3, MATH, Fractions, 38% mastery.",
        )
        assert stamp.status == StampStatus.APPROVED
        assert stamp.violations == []


# ── Stamp Properties ──────────────────────────────────────────────────────────

class TestStampProperties:
    @pytest.mark.asyncio
    async def test_stamp_records_rules_evaluated(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(action=action)
        assert len(stamp.rules_evaluated) > 0

    @pytest.mark.asyncio
    async def test_stamp_has_latency(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(action=action)
        assert stamp.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_stamp_has_reasoning(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        stamp = await j.review(action=action)
        assert stamp.reasoning

    @pytest.mark.asyncio
    async def test_rejection_increments_counter(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        await j.review(action=action, system_prompt="uuid: 12345678-1234-1234-1234-123456789012")
        stats = j.get_stats()
        assert stats["rejections"] >= 1

    @pytest.mark.asyncio
    async def test_approval_increments_stamp_count(self):
        j = Judiciary(use_llm_review=False)
        action = make_action()
        await j.review(action=action)
        stats = j.get_stats()
        assert stats["total_stamps"] >= 1


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestJudiciarySingleton:
    def test_singleton_returns_same_instance(self):
        import importlib
        import app.api.judiciary as jmod
        jmod._judiciary = None  # Reset singleton
        j1 = get_judiciary(use_llm_review=False)
        j2 = get_judiciary(use_llm_review=False)
        assert j1 is j2

    def test_stats_structure(self):
        j = Judiciary(use_llm_review=False)
        stats = j.get_stats()
        assert "total_stamps" in stats
        assert "rejections" in stats
        assert "approval_rate" in stats
