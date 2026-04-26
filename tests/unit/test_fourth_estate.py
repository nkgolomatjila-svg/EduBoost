"""
Unit tests for the Fourth Estate (Pillar 4).
Tests audit event publishing, violation flagging, and stats.
"""
import pytest
from unittest.mock import patch, AsyncMock

from app.api.constitutional_schema.types import (
    ExecutiveAction, ActionType, JudiciaryStamp, StampStatus,
    AuditEvent, EventType,
)
from app.api.fourth_estate import FourthEstate, get_fourth_estate


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_action(params=None):
    return ExecutiveAction(
        action_type=ActionType.GENERATE_LESSON,
        learner_id_hash="b" * 32,
        grade=3,
        params=params or {"subject_code": "MATH", "topic": "Fractions"},
        claimed_rules=[],
    )


def make_stamp(status=StampStatus.APPROVED, violations=None):
    return JudiciaryStamp(
        action_id="test-action-001",
        status=status,
        rules_evaluated=["POPIA_01", "CAPS_01"],
        violations=violations or [],
        reasoning="Test stamp.",
        latency_ms=10,
    )


# ── Event Publishing ──────────────────────────────────────────────────────────

class TestEventPublishing:
    @pytest.mark.asyncio
    async def test_publish_increments_event_count(self):
        fe = FourthEstate()  # No Redis — in-memory mode
        assert fe.get_stats()["total_events"] == 0

        event = AuditEvent(
            event_type=EventType.ACTION_SUBMITTED,
            pillar="EXECUTIVE",
        )
        await fe.publish(event)
        assert fe.get_stats()["total_events"] == 1

    @pytest.mark.asyncio
    async def test_published_event_in_buffer(self):
        fe = FourthEstate()
        event = AuditEvent(
            event_type=EventType.STAMP_ISSUED,
            pillar="JUDICIARY",
            payload={"test": True},
        )
        await fe.publish(event)
        recent = fe.get_recent_events(1)
        assert len(recent) == 1
        assert recent[0].event_type == EventType.STAMP_ISSUED

    @pytest.mark.asyncio
    async def test_publish_action_submitted(self):
        fe = FourthEstate()
        action = make_action()
        await fe.publish_action_submitted(action)
        events = fe.get_recent_events(1)
        assert events[0].event_type == EventType.ACTION_SUBMITTED
        assert events[0].pillar == "EXECUTIVE"

    @pytest.mark.asyncio
    async def test_publish_approved_stamp(self):
        fe = FourthEstate()
        action = make_action()
        stamp = make_stamp(status=StampStatus.APPROVED)
        await fe.publish_stamp_issued(stamp, action)
        events = fe.get_recent_events(1)
        assert events[0].event_type == EventType.STAMP_ISSUED

    @pytest.mark.asyncio
    async def test_publish_rejected_stamp_creates_violation_event(self):
        fe = FourthEstate()
        action = make_action()
        stamp = make_stamp(status=StampStatus.REJECTED, violations=["PII_01"])
        await fe.publish_stamp_issued(stamp, action)

        # Should have two events: STAMP_REJECTED + CONSTITUTIONAL_VIOLATION
        all_events = fe.get_recent_events(10)
        event_types = [e.event_type for e in all_events]
        assert EventType.STAMP_REJECTED in event_types
        assert EventType.CONSTITUTIONAL_VIOL in event_types

    @pytest.mark.asyncio
    async def test_violation_increments_violation_count(self):
        fe = FourthEstate()
        action = make_action()
        await fe.flag_constitutional_violation(
            action=action,
            stamp=make_stamp(violations=["PII_01"]),
            violated_rules=["PII_01"],
        )
        assert fe.get_stats()["violations"] >= 1

    @pytest.mark.asyncio
    async def test_publish_llm_success(self):
        fe = FourthEstate()
        action = make_action()
        await fe.publish_llm_result(
            action=action, provider="groq", success=True, latency_ms=450
        )
        events = fe.get_recent_events(1)
        assert events[0].event_type == EventType.LLM_CALL_COMPLETED
        assert events[0].payload["provider"] == "groq"

    @pytest.mark.asyncio
    async def test_publish_llm_failure(self):
        fe = FourthEstate()
        action = make_action()
        await fe.publish_llm_result(
            action=action, provider="groq", success=False, latency_ms=30000
        )
        events = fe.get_recent_events(1)
        assert events[0].event_type == EventType.LLM_CALL_FAILED

    @pytest.mark.asyncio
    async def test_publish_ether_cache_hit(self):
        fe = FourthEstate()
        await fe.publish_ether_event(
            learner_hash="abc123", archetype="TIFERET", cache_hit=True
        )
        events = fe.get_recent_events(1)
        assert events[0].event_type == EventType.ETHER_PROFILE_HIT

    @pytest.mark.asyncio
    async def test_publish_ether_cache_miss(self):
        fe = FourthEstate()
        await fe.publish_ether_event(
            learner_hash="abc123", archetype="TIFERET", cache_hit=False
        )
        events = fe.get_recent_events(1)
        assert events[0].event_type == EventType.ETHER_PROFILE_MISS


# ── Buffer Behaviour ──────────────────────────────────────────────────────────

class TestBufferBehaviour:
    @pytest.mark.asyncio
    async def test_buffer_caps_at_1000_events(self):
        """Buffer should not grow beyond 1000 events (trims to 500)."""
        fe = FourthEstate()
        for _ in range(1100):
            await fe.publish(AuditEvent(event_type=EventType.ACTION_SUBMITTED, pillar="TEST"))
        assert len(fe._buffer) <= 1000

    @pytest.mark.asyncio
    async def test_get_recent_events_returns_n(self):
        fe = FourthEstate()
        for i in range(10):
            await fe.publish(AuditEvent(
                event_type=EventType.STAMP_ISSUED,
                pillar="JUDICIARY",
                payload={"seq": i},
            ))
        recent = fe.get_recent_events(5)
        assert len(recent) == 5

    @pytest.mark.asyncio
    async def test_most_recent_events_returned_last(self):
        """get_recent_events(n) should return the last n events, most recent last."""
        fe = FourthEstate()
        for i in range(5):
            await fe.publish(AuditEvent(
                event_type=EventType.DIAGNOSTIC_RUN,
                pillar="EXECUTIVE",
                payload={"seq": i},
            ))
        recent = fe.get_recent_events(5)
        seqs = [e.payload.get("seq") for e in recent]
        assert seqs == [0, 1, 2, 3, 4]


# ── Stats ─────────────────────────────────────────────────────────────────────

class TestStats:
    def test_initial_stats_zero(self):
        fe = FourthEstate()
        stats = fe.get_stats()
        assert stats["total_events"] == 0
        assert stats["violations"] == 0
        assert stats["buffer_size"] == 0

    def test_stats_contains_stream_key(self):
        fe = FourthEstate(stream_key="test:stream")
        stats = fe.get_stats()
        assert stats["stream_key"] == "test:stream"


# ── Redis Degradation ─────────────────────────────────────────────────────────

class TestRedisDegradation:
    @pytest.mark.asyncio
    async def test_publishes_without_redis(self):
        """Publishing should succeed even when Redis is unavailable."""
        fe = FourthEstate(redis_url="redis://does-not-exist:6379/0")
        event = AuditEvent(event_type=EventType.ACTION_SUBMITTED, pillar="TEST")
        # Should not raise — graceful degradation
        await fe.publish(event)
        assert fe.get_stats()["total_events"] == 1


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestFourthEstateSingleton:
    def test_singleton(self):
        import app.api.fourth_estate as femod
        femod._fourth_estate = None
        fe1 = get_fourth_estate()
        fe2 = get_fourth_estate()
        assert fe1 is fe2
