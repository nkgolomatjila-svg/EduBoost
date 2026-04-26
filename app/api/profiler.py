"""EduBoost SA — Ether Profiler (Pillar 5): learner tone and archetype."""
from __future__ import annotations

import hashlib
import hmac
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from app.api.constitutional_schema.types import EtherArchetype, EtherToneParams, LearnerEtherProfile
from app.api.core.config import settings

_DEFAULT_ARCHETYPE = EtherArchetype.TIFERET

_ARCHETYPE_DEFAULTS: dict[EtherArchetype, EtherToneParams] = {
    EtherArchetype.KETER: EtherToneParams(
        warmth_level=0.55, challenge_tolerance=0.9, pacing="fast", preferred_modality="visual"
    ),
    EtherArchetype.CHOKHMAH: EtherToneParams(
        warmth_level=0.6, challenge_tolerance=0.85, pacing="fast", preferred_modality="visual"
    ),
    EtherArchetype.BINAH: EtherToneParams(
        warmth_level=0.62, challenge_tolerance=0.75, pacing="moderate", preferred_modality="auditory"
    ),
    EtherArchetype.CHESED: EtherToneParams(
        warmth_level=0.85, challenge_tolerance=0.45, pacing="slow", preferred_modality="kinesthetic"
    ),
    EtherArchetype.GEVURAH: EtherToneParams(
        warmth_level=0.5, challenge_tolerance=0.82, pacing="fast", preferred_modality="visual"
    ),
    EtherArchetype.TIFERET: EtherToneParams(
        warmth_level=0.65, challenge_tolerance=0.55, pacing="moderate", preferred_modality="visual"
    ),
    EtherArchetype.NETZACH: EtherToneParams(
        warmth_level=0.7, challenge_tolerance=0.6, pacing="moderate", preferred_modality="kinesthetic"
    ),
    EtherArchetype.HOD: EtherToneParams(
        warmth_level=0.58, challenge_tolerance=0.65, pacing="moderate", preferred_modality="auditory"
    ),
    EtherArchetype.YESOD: EtherToneParams(
        warmth_level=0.8, challenge_tolerance=0.4, pacing="slow", preferred_modality="kinesthetic"
    ),
    EtherArchetype.MALKUTH: EtherToneParams(
        warmth_level=0.78, challenge_tolerance=0.42, pacing="slow", preferred_modality="kinesthetic"
    ),
}

_profiler: Optional["EtherProfiler"] = None


def _learner_hash(learner_id: str) -> str:
    """
    Salted HMAC-SHA256 of learner_id (Phase 1, item #4).
    Replaces plain SHA-256 which is vulnerable to brute-force reversal of UUIDs.
    """
    salt = (settings.ENCRYPTION_SALT or "").encode("utf-8")
    return hmac.new(salt, learner_id.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


class EtherProfiler:
    def _extract_signals(self, events: list[dict[str, Any]]) -> dict[str, float]:
        if not events:
            return {"accuracy_rate": 0.5, "speed_norm": 0.5, "hint_rate": 0.0, "completion_rate": 0.5}
        acc = sum(1 for e in events if e.get("is_correct")) / len(events)
        times = [float(e.get("time_on_task_ms") or 5000) for e in events]
        avg_ms = statistics.mean(times) if times else 5000.0
        speed_norm = max(0.0, min(1.0, 1.0 - (avg_ms - 1000.0) / 19000.0))
        hints = sum(1 for e in events if e.get("hint_used")) / len(events)
        completion = sum(1 for e in events if e.get("completed", True)) / len(events)
        return {
            "accuracy_rate": acc,
            "speed_norm": speed_norm,
            "hint_rate": hints,
            "completion_rate": completion,
        }

    def _classify_archetype(self, events: list[dict[str, Any]]) -> Tuple[EtherArchetype, float]:
        if not events:
            return _DEFAULT_ARCHETYPE, 0.3
        s = self._extract_signals(events)
        score = (
            0.45 * s["accuracy_rate"]
            + 0.35 * s["speed_norm"]
            + 0.1 * (1.0 - s["hint_rate"])
            + 0.1 * s["completion_rate"]
        )
        confidence = max(0.3, min(0.95, 0.35 + len(events) / 40.0))
        if score >= 0.82:
            return EtherArchetype.KETER, confidence
        if score >= 0.72:
            return EtherArchetype.CHOKHMAH, confidence
        if score >= 0.62:
            return EtherArchetype.GEVURAH, confidence
        if score <= 0.28:
            return EtherArchetype.YESOD, confidence
        if score <= 0.38:
            return EtherArchetype.CHESED, confidence
        if score <= 0.45:
            return EtherArchetype.MALKUTH, confidence
        return EtherArchetype.TIFERET, confidence

    def _tune_params(self, base: EtherToneParams, signals: dict[str, float]) -> EtherToneParams:
        d = base.model_dump()
        if signals["hint_rate"] >= 0.5:
            d["encouragement_freq"] = "high"
        if signals["accuracy_rate"] <= 0.35:
            d["pacing"] = "slow"
            d["sa_cultural_depth"] = "deep"
        if signals["hint_rate"] < 0.15 and signals["accuracy_rate"] >= 0.85 and signals["speed_norm"] >= 0.75:
            d["pacing"] = "fast"
            d["challenge_tolerance"] = max(d["challenge_tolerance"], 0.82)
        return EtherToneParams(**d)

    async def get_profile(self, learner_id: str) -> LearnerEtherProfile:
        lh = _learner_hash(learner_id)
        base = _ARCHETYPE_DEFAULTS[_DEFAULT_ARCHETYPE]
        return LearnerEtherProfile(
            learner_hash=lh,
            archetype=_DEFAULT_ARCHETYPE,
            tone_params=base,
            confidence_score=0.3,
            data_points=0,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

    async def compute_and_cache(self, learner_id: str, events: list[dict[str, Any]]) -> LearnerEtherProfile:
        archetype, conf = self._classify_archetype(events)
        base = _ARCHETYPE_DEFAULTS.get(archetype, _ARCHETYPE_DEFAULTS[_DEFAULT_ARCHETYPE])
        signals = self._extract_signals(events)
        tuned = self._tune_params(base, signals)
        return LearnerEtherProfile(
            learner_hash=_learner_hash(learner_id),
            archetype=archetype,
            tone_params=tuned,
            confidence_score=max(0.31, conf),
            data_points=len(events),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
        )


def get_profiler() -> EtherProfiler:
    global _profiler
    if _profiler is None:
        _profiler = EtherProfiler()
    return _profiler
