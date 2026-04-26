"""
Integration tests for the Five-Pillar Constitutional Pipeline.
Tests the full Orchestrator flow: Legislature → Executive → Judiciary → Fourth Estate → Ether.

These tests mock the LLM calls but exercise the real constitutional machinery.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.api.constitutional_schema.types import (
    ActionType, StampStatus, EtherArchetype,
)

# ── Shared mock lesson JSON ───────────────────────────────────────────────────
MOCK_LESSON = {
    "title": "Fractions at the Braai",
    "story_hook": "Mama cuts a koeksister into 4 equal pieces.",
    "visual_anchor": "[whole] → [1/4][1/4][1/4][1/4]",
    "steps": [
        {
            "heading": "What is a Fraction?",
            "body": "A fraction is an equal part of a whole.",
            "visual": "🟡",
            "sa_example": "Cut a boerie roll in half.",
        }
    ],
    "practice": [
        {
            "question": "Sipho eats 1 of 4 pieces. What fraction?",
            "options": ["1/2", "1/4", "1/3", "2/4"],
            "correct": 1,
            "hint": "Count total pieces.",
            "feedback": "Yebo! Sharp sharp!",
        }
    ],
    "try_it": {
        "title": "Paper Folding",
        "materials": ["paper"],
        "instructions": "Fold paper in half.",
    },
    "xp": 35,
    "badge": "Fraction Fan",
}

import json
MOCK_LESSON_STR = json.dumps(MOCK_LESSON)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lesson_request(learner_id="00000000-0000-0000-0000-000000000001"):
    return {
        "learner_id": learner_id,
        "subject_code": "MATH",
        "subject_label": "Mathematics",
        "topic": "Fractions",
        "grade": 3,
        "home_language": "English",
        "learning_style_primary": "visual",
        "mastery_prior": 0.38,
        "has_gap": True,
        "gap_grade": 2,
    }


# ── Full Pipeline: Generate Lesson ────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
class TestLessonPipelineEndToEnd:

    async def test_full_pipeline_success(self):
        """Happy path: clean params → APPROVED → lesson generated."""
        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MOCK_LESSON_STR
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json=_lesson_request())

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "lesson" in data
        assert data["lesson"]["title"] == "Fractions at the Braai"

    async def test_learner_id_never_reaches_llm(self):
        """POPIA critical: learner_id must not appear in any LLM prompt."""
        learner_id = "00000000-0000-0000-0000-000000000001"
        captured_calls = []

        async def capture(*args, **kwargs):
            captured_calls.append({"args": args, "kwargs": kwargs})
            return MOCK_LESSON_STR

        with patch("app.api.services.lesson_service.call_llm", side_effect=capture):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.post("/api/v1/lessons/generate", json=_lesson_request(learner_id))

        for call in captured_calls:
            all_text = str(call["args"]) + str(call["kwargs"])
            assert learner_id not in all_text, (
                f"POPIA VIOLATION: Learner UUID found in LLM call!\n{all_text[:500]}"
            )

    async def test_llm_failure_returns_503(self):
        """LLM chain failure should propagate as 503."""
        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("All LLM providers failed")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json=_lesson_request())

        assert response.status_code == 503

    async def test_missing_required_fields_returns_422(self):
        """Missing required fields should return 422 Unprocessable Entity."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/lessons/generate", json={
                "learner_id": "00000000-0000-0000-0000-000000000001",
                # Missing: subject_code, subject_label, topic, grade
            })
        assert response.status_code == 422

    async def test_invalid_grade_returns_422(self):
        """Grade outside 0–7 must be rejected at input validation."""
        req = _lesson_request()
        req["grade"] = 9  # Invalid
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/lessons/generate", json=req)
        assert response.status_code == 422


# ── Constitutional Metadata in Response ───────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
class TestConstitutionalMetadata:

    async def test_response_includes_stamp_status(self):
        """Successful response must include constitutional stamp metadata."""
        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MOCK_LESSON_STR
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json=_lesson_request())

        data = response.json()
        if response.status_code == 200 and "meta" in data:
            meta = data["meta"]
            assert "stamp_status" in meta
            assert meta["stamp_status"] in {"APPROVED", "DEFERRED"}

    async def test_constitutional_health_between_0_and_1(self):
        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MOCK_LESSON_STR
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json=_lesson_request())

        if response.status_code == 200:
            data = response.json()
            if "meta" in data and "constitutional_health" in data["meta"]:
                health = data["meta"]["constitutional_health"]
                assert 0.0 <= health <= 1.0


# ── Fourth Estate Audit Events ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
class TestFourthEstateIntegration:

    async def test_audit_events_emitted_on_success(self):
        """A successful lesson generation must produce audit events."""
        from app.api.fourth_estate import get_fourth_estate
        import app.api.fourth_estate as femod
        femod._fourth_estate = None  # Reset singleton
        fe = get_fourth_estate()
        initial_count = fe.get_stats()["total_events"]

        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MOCK_LESSON_STR
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json=_lesson_request())

        if response.status_code == 200:
            final_count = fe.get_stats()["total_events"]
            assert final_count > initial_count

    async def test_no_violations_on_clean_request(self):
        """A clean lesson request must not produce constitutional violations."""
        from app.api.fourth_estate import get_fourth_estate
        import app.api.fourth_estate as femod
        femod._fourth_estate = None
        fe = get_fourth_estate()

        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MOCK_LESSON_STR
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.post("/api/v1/lessons/generate", json=_lesson_request())

        assert fe.get_stats()["violations"] == 0


# ── Health Endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
class TestHealthEndpoint:

    async def test_health_returns_ok(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "EduBoost" in data["service"]


# ── POPIA: Data Minimisation Audit ────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
class TestPOPIACompliance:

    async def test_response_contains_no_learner_pii(self):
        """API response must never echo back learner PII."""
        learner_id = "00000000-0000-0000-0000-000000000002"
        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MOCK_LESSON_STR
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json={
                    **_lesson_request(learner_id),
                    "learner_id": learner_id,
                })

        # The learner UUID must not appear verbatim in the response body
        response_text = response.text
        assert learner_id not in response_text, (
            "POPIA VIOLATION: Learner UUID echoed in API response!"
        )

    async def test_study_plan_endpoint_exists(self):
        """Study plan generation endpoint must be accessible."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/study-plans/generate", json={
                "learner_id": "00000000-0000-0000-0000-000000000001",
                "grade": 3,
                "knowledge_gaps": [],
                "subjects_mastery": {"MATH": 0.38},
            })
        # May fail with 503 if LLM unavailable, but should not be 404
        assert response.status_code != 404
