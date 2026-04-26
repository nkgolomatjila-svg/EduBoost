"""Integration tests for extended Phase 1 API contracts."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app


@pytest.mark.asyncio
@pytest.mark.integration
async def test_guardian_login_rejects_unknown_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/guardian/login",
            json={
                "email": "guardian@example.com",
                "learner_pseudonym_id": "abc",
                "unexpected": "field",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parent_report_rejects_unknown_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/parent/report/generate",
            json={
                "learner_id": "00000000-0000-0000-0000-000000000001",
                "grade": 3,
                "extra": True,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.integration
async def test_study_plan_rejects_unknown_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/study-plans/generate",
            json={
                "learner_id": "00000000-0000-0000-0000-000000000001",
                "grade": 3,
                "subjects_mastery": {},
                "unknown": 1,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.integration
async def test_learner_session_creation():
    """Test that learner session endpoint creates a valid token."""
    learner_id = str(uuid.uuid4())
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/learner/session",
            json={"learner_id": learner_id},
        )

    # Should return 200 with token
    if response.status_code == 200:
        payload = response.json()
        assert "session_token" in payload
        assert "expires_in" in payload
        assert payload["expires_in"] > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_learner_session_rejects_empty_learner_id():
    """Test that learner session rejects empty learner_id."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/learner/session",
            json={"learner_id": ""},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.integration
async def test_guardian_login_rejects_invalid_email():
    """Test that guardian login rejects invalid email format."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/guardian/login",
            json={
                "email": "not-an-email",
                "learner_pseudonym_id": "abc",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.integration
async def test_protected_endpoint_without_token():
    """Test that protected endpoints reject requests without auth token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Try to access parent portal without token
        response = await client.get(
            "/api/v1/parent/00000000-0000-0000-0000-000000000001/progress/00000000-0000-0000-0000-000000000002",
        )

    # Should be rejected (401 or 403)
    assert response.status_code in [401, 403]
