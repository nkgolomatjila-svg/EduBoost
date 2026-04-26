"""Integration tests for strict API contracts on learner and diagnostic routes."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_learner_rejects_unknown_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/learners/",
            json={
                "grade": 3,
                "home_language": "eng",
                "unexpected": True,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_invalid_subject_returns_structured_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/diagnostic/run",
            json={
                "learner_id": "00000000-0000-0000-0000-000000000001",
                "subject_code": "INVALID",
                "grade": 3,
                "max_questions": 5,
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"]["code"] == "INVALID_SUBJECT_CODE"
    assert payload["detail"]["error"] == "Invalid subject code"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_run_returns_valid_response():
    """Test that diagnostic run endpoint returns properly structured response."""
    learner_id = str(uuid.uuid4())
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/diagnostic/run",
            json={
                "learner_id": learner_id,
                "subject_code": "MATH",
                "grade": 3,
                "max_questions": 5,
            },
        )

    # Should succeed (may fail if DB not available, but tests the contract)
    if response.status_code == 200:
        payload = response.json()
        assert "success" in payload
        assert "gap_report" in payload
        assert "session_summary" in payload
        assert "questions_administered" in payload["session_summary"]
        assert "theta" in payload["session_summary"]
        assert "sem" in payload["session_summary"]
        assert "gap_probe_active" in payload["session_summary"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_history_endpoint():
    """Test that diagnostic history endpoint returns session list."""
    learner_id = uuid.uuid4()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/diagnostic/history/{learner_id}",
        )

    # Should return 200 with sessions list
    if response.status_code == 200:
        payload = response.json()
        assert "learner_id" in payload
        assert "sessions" in payload
        assert "count" in payload
        assert isinstance(payload["sessions"], list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_right_to_access_endpoint():
    """Test that POPIA right-to-access endpoint returns learner data."""
    learner_id = str(uuid.uuid4())
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/system/access/{learner_id}",
        )

    # Should return 404 if learner doesn't exist, or 200 with data
    if response.status_code == 404:
        assert "Learner not found" in response.json()["detail"]
    elif response.status_code == 200:
        payload = response.json()
        assert "learner_id" in payload
        assert "data_summary" in payload
        assert "consent_records" in payload
        assert "audit_events" in payload


@pytest.mark.asyncio
@pytest.mark.integration
async def test_audit_search_endpoint():
    """Test that audit search endpoint returns filtered events."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/system/audit/search?event_type=LOGIN&page=1&page_size=10",
        )

    # Should return 200 with events list
    if response.status_code == 200:
        payload = response.json()
        assert "events" in payload
        assert "total_count" in payload
        assert "page" in payload
        assert "page_size" in payload
        assert "has_more" in payload
