"""
Unit tests for the Ether Profiler (Pillar 5).
Tests archetype classification, signal extraction, and cache behaviour.
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone

from app.api.constitutional_schema.types import EtherArchetype, EtherToneParams
from app.api.profiler import EtherProfiler, get_profiler, _ARCHETYPE_DEFAULTS, _DEFAULT_ARCHETYPE


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_response_events(
    n=10, accuracy=0.7, speed_ms=5000, hint_rate=0.2, completed=True
):
    """Generate synthetic response events."""
    events = []
    for i in range(n):
        is_correct = i < int(n * accuracy)
        events.append({
            "is_correct": is_correct,
            "time_on_task_ms": speed_ms,
            "hint_used": i < int(n * hint_rate),
            "completed": completed,
        })
    return events


# ── Signal Extraction ─────────────────────────────────────────────────────────

class TestSignalExtraction:
    def test_empty_events_returns_defaults(self):
        p = EtherProfiler()
        signals = p._extract_signals([])
        assert signals["accuracy_rate"] == 0.5
        assert signals["speed_norm"] == 0.5

    def test_all_correct_accuracy_is_1(self):
        p = EtherProfiler()
        events = make_response_events(10, accuracy=1.0)
        signals = p._extract_signals(events)
        assert signals["accuracy_rate"] == 1.0

    def test_all_wrong_accuracy_is_0(self):
        p = EtherProfiler()
        events = make_response_events(10, accuracy=0.0)
        signals = p._extract_signals(events)
        assert signals["accuracy_rate"] == 0.0

    def test_fast_response_speed_norm_high(self):
        """Sub-3s responses should give speed_norm near 1.0."""
        p = EtherProfiler()
        events = make_response_events(5, speed_ms=1000)  # 1s — fast
        signals = p._extract_signals(events)
        assert signals["speed_norm"] > 0.8

    def test_slow_response_speed_norm_low(self):
        """15s+ responses should give speed_norm near 0.0."""
        p = EtherProfiler()
        events = make_response_events(5, speed_ms=20000)  # 20s — slow
        signals = p._extract_signals(events)
        assert signals["speed_norm"] < 0.1

    def test_hint_rate_computed_correctly(self):
        p = EtherProfiler()
        events = make_response_events(10, hint_rate=0.5)
        signals = p._extract_signals(events)
        assert abs(signals["hint_rate"] - 0.5) < 0.01


# ── Archetype Classification ──────────────────────────────────────────────────

class TestArchetypeClassification:
    def test_high_ability_fast_maps_to_keter_region(self):
        """High accuracy + fast speed + no hints → should classify to high-ability archetype."""
        p = EtherProfiler()
        events = make_response_events(20, accuracy=0.95, speed_ms=1500, hint_rate=0.0)
        archetype, confidence = p._classify_archetype(events)
        # KETER or CHOKHMAH expected for this profile
        assert archetype in {EtherArchetype.KETER, EtherArchetype.CHOKHMAH, EtherArchetype.GEVURAH}

    def test_struggling_learner_maps_to_foundation_archetype(self):
        """Low accuracy + high hints + low completion → YESOD (foundation needs)."""
        p = EtherProfiler()
        events = [
            {"is_correct": False, "time_on_task_ms": 12000, "hint_used": True, "completed": False}
            for _ in range(15)
        ]
        archetype, confidence = p._classify_archetype(events)
        assert archetype in {EtherArchetype.YESOD, EtherArchetype.CHESED, EtherArchetype.MALKUTH}

    def test_empty_events_returns_default_archetype(self):
        p = EtherProfiler()
        archetype, confidence = p._classify_archetype([])
        assert archetype == _DEFAULT_ARCHETYPE
        assert confidence == 0.3

    def test_confidence_in_valid_range(self):
        p = EtherProfiler()
        events = make_response_events(10)
        _, confidence = p._classify_archetype(events)
        assert 0.3 <= confidence <= 0.95

    def test_all_archetypes_are_classifiable(self):
        """The classifier must produce a valid EtherArchetype for any input."""
        p = EtherProfiler()
        for _ in range(10):
            import random
            events = make_response_events(
                n=random.randint(1, 20),
                accuracy=random.random(),
                speed_ms=random.randint(1000, 20000),
                hint_rate=random.random(),
                completed=random.choice([True, False]),
            )
            archetype, _ = p._classify_archetype(events)
            assert archetype in EtherArchetype.__members__.values()


# ── Parameter Tuning ─────────────────────────────────────────────────────────

class TestParameterTuning:
    def test_high_hint_rate_increases_encouragement(self):
        p = EtherProfiler()
        base = EtherToneParams()
        signals = {"hint_rate": 0.6, "accuracy_rate": 0.5, "speed_norm": 0.5, "completion_rate": 0.7}
        tuned = p._tune_params(base, signals)
        assert tuned.encouragement_freq == "high"

    def test_low_accuracy_slows_pacing(self):
        p = EtherProfiler()
        base = EtherToneParams()
        signals = {"hint_rate": 0.2, "accuracy_rate": 0.3, "speed_norm": 0.5, "completion_rate": 0.8}
        tuned = p._tune_params(base, signals)
        assert tuned.pacing == "slow"
        assert tuned.sa_cultural_depth == "deep"

    def test_high_ability_speeds_up_pacing(self):
        p = EtherProfiler()
        base = EtherToneParams()
        signals = {"hint_rate": 0.0, "accuracy_rate": 0.9, "speed_norm": 0.9, "completion_rate": 1.0}
        tuned = p._tune_params(base, signals)
        assert tuned.pacing == "fast"
        assert tuned.challenge_tolerance >= 0.8


# ── Cold-Start Profile ────────────────────────────────────────────────────────

class TestColdStart:
    @pytest.mark.asyncio
    async def test_cold_start_returns_tiferet(self):
        """First-time profile with no cache → TIFERET default."""
        p = EtherProfiler()  # No Redis
        profile = await p.get_profile("learner-new-user-123")
        assert profile.archetype == EtherArchetype.TIFERET
        assert profile.confidence_score == 0.3
        assert profile.data_points == 0

    @pytest.mark.asyncio
    async def test_cold_start_has_expires_at(self):
        p = EtherProfiler()
        profile = await p.get_profile("learner-cold")
        assert profile.expires_at is not None
        assert profile.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_learner_hash_is_not_learner_id(self):
        """Profile learner_hash must be a non-reversible hash, not the raw ID."""
        p = EtherProfiler()
        raw_id = "00000000-0000-0000-0000-000000000001"
        profile = await p.get_profile(raw_id)
        assert raw_id not in profile.learner_hash
        assert len(profile.learner_hash) == 32


# ── Compute and Cache ─────────────────────────────────────────────────────────

class TestComputeAndCache:
    @pytest.mark.asyncio
    async def test_compute_profile_from_events(self):
        p = EtherProfiler()
        events = make_response_events(10, accuracy=0.8)
        profile = await p.compute_and_cache("learner-compute-test", events)
        assert profile.archetype in EtherArchetype.__members__.values()
        assert profile.data_points == 10
        assert profile.confidence_score > 0.3

    @pytest.mark.asyncio
    async def test_profile_tone_params_valid(self):
        p = EtherProfiler()
        events = make_response_events(8)
        profile = await p.compute_and_cache("learner-params-test", events)
        assert 0.0 <= profile.tone_params.warmth_level <= 1.0
        assert 0.0 <= profile.tone_params.challenge_tolerance <= 1.0
        assert profile.tone_params.pacing in {"slow", "moderate", "fast"}


# ── Archetype Defaults ────────────────────────────────────────────────────────

class TestArchetypeDefaults:
    def test_all_archetypes_have_defaults(self):
        for archetype in EtherArchetype:
            assert archetype in _ARCHETYPE_DEFAULTS, f"No default for {archetype.value}"

    def test_all_defaults_have_valid_tone_params(self):
        for archetype, params in _ARCHETYPE_DEFAULTS.items():
            assert 0.0 <= params.warmth_level <= 1.0
            assert 0.0 <= params.challenge_tolerance <= 1.0
            assert params.pacing in {"slow", "moderate", "fast"}
            assert params.preferred_modality in {"visual", "auditory", "kinesthetic"}


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestProfilerSingleton:
    def test_singleton_returns_same_instance(self):
        import app.api.profiler as pmod
        pmod._profiler = None
        p1 = get_profiler()
        p2 = get_profiler()
        assert p1 is p2
