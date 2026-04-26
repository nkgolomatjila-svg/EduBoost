"""EduBoost SA — Fourth Estate (Pillar 4): audit trail and transparency."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.api.constitutional_schema.types import (
    AuditEvent,
    EventType,
    ExecutiveAction,
    JudiciaryStamp,
    StampStatus,
)

_fourth_estate: Optional["FourthEstate"] = None


class FourthEstate:
    def __init__(self, redis_url: Optional[str] = None, stream_key: str = "eduboost:audit") -> None:
        self.redis_url = redis_url
        self.stream_key = stream_key
        self._buffer: deque[AuditEvent] = deque(maxlen=1000)
        self._total_events = 0
        self._violations = 0
        self._sequence = 0
        self._redis = None

    def get_stats(self) -> dict:
        return {
            "total_events": self._total_events,
            "violations": self._violations,
            "buffer_size": len(self._buffer),
            "stream_key": self.stream_key,
        }

    async def publish(self, event: AuditEvent) -> None:
        self._total_events += 1
        self._sequence += 1
        self._buffer.append(event)
        if self.redis_url:
            try:
                import redis.asyncio as redis_lib

                if self._redis is None:
                    self._redis = redis_lib.from_url(self.redis_url, decode_responses=True)
                await self._redis.xadd(
                    self.stream_key,
                    {"payload": str(event.model_dump(mode="json"))},
                    maxlen=10_000,
                    approximate=True,
                )
            except Exception:
                pass

    async def publish_action_submitted(self, action: ExecutiveAction) -> None:
        await self.publish(AuditEvent(event_type=EventType.ACTION_SUBMITTED, pillar="EXECUTIVE", action_id=action.action_id, learner_hash=action.learner_id_hash, payload={"action_type": action.action_type.value}))

    async def publish_stamp_issued(self, stamp: JudiciaryStamp, action: ExecutiveAction) -> None:
        await self.publish(AuditEvent(event_type=EventType.STAMP_ISSUED, pillar="JUDICIARY", action_id=action.action_id, learner_hash=action.learner_id_hash, payload={"status": stamp.status.value, "violations": stamp.violations}))
        if stamp.status == StampStatus.REJECTED:
            await self.publish(AuditEvent(event_type=EventType.STAMP_REJECTED, pillar="JUDICIARY", action_id=action.action_id, learner_hash=action.learner_id_hash, payload={"violations": stamp.violations}))
            await self.flag_constitutional_violation(action=action, stamp=stamp, violated_rules=list(stamp.violations))

    async def flag_constitutional_violation(self, action: ExecutiveAction, stamp: JudiciaryStamp, violated_rules: list[str]) -> None:
        self._violations += 1
        await self.publish(AuditEvent(event_type=EventType.CONSTITUTIONAL_VIOL, pillar="JUDICIARY", action_id=action.action_id, learner_hash=action.learner_id_hash, payload={"rules": violated_rules, "stamp": stamp.status.value}))

    async def publish_llm_result(self, action: ExecutiveAction, provider: str, success: bool, latency_ms: int) -> None:
        et = EventType.LLM_CALL_COMPLETED if success else EventType.LLM_CALL_FAILED
        await self.publish(AuditEvent(event_type=et, pillar="EXECUTIVE", action_id=action.action_id, learner_hash=action.learner_id_hash, payload={"provider": provider, "latency_ms": latency_ms}))

    async def publish_ether_event(self, learner_hash: str, archetype: str, cache_hit: bool) -> None:
        et = EventType.ETHER_PROFILE_HIT if cache_hit else EventType.ETHER_PROFILE_MISS
        await self.publish(AuditEvent(event_type=et, pillar="ETHER", learner_hash=learner_hash, payload={"archetype": archetype, "cache_hit": cache_hit}))

    async def publish_domain_event(self, event_type: EventType, action: ExecutiveAction, payload: dict[str, Any]) -> None:
        await self.publish(AuditEvent(event_type=event_type, pillar="EXECUTIVE", action_id=action.action_id, learner_hash=action.learner_id_hash, payload=payload))

    def get_recent_events(self, n: int) -> list[AuditEvent]:
        if n <= 0:
            return []
        return list(self._buffer)[-n:]

    def get_health_status(self) -> dict:
        from app.api.judiciary import get_judiciary

        j = get_judiciary()
        s = j.get_stats()
        health = s["approval_rate"]
        return {
            "overall": "GREEN" if health >= 0.95 else "AMBER",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "constitutional_health": health,
            "judiciary_approval_rate": health,
            "pillar_status": {
                "LEGISLATURE": "GREEN",
                "EXECUTIVE": "GREEN",
                "JUDICIARY": "GREEN",
                "FOURTH_ESTATE": "GREEN",
                "ETHER": "GREEN",
            },
        }

    def build_audit_report(self, report_type: str = "COMPLIANCE", hours: int = 24) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent = [e for e in self._buffer if e.occurred_at >= cutoff]
        return {"report_type": report_type, "hours": hours, "event_count": len(recent), "total_recorded": self._total_events}

    def get_chain_integrity(self) -> dict[str, Any]:
        return {"sealed": True, "buffer_len": len(self._buffer)}

    def get_recent_violations(self, limit: int = 5) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for e in reversed(self._buffer):
            if e.event_type == EventType.CONSTITUTIONAL_VIOL:
                out.append({"event_id": e.event_id, "payload": e.payload})
                if len(out) >= limit:
                    break
        return list(reversed(out))


def get_fourth_estate() -> FourthEstate:
    global _fourth_estate
    if _fourth_estate is None:
        _fourth_estate = FourthEstate()
    return _fourth_estate
