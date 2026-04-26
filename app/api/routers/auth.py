"""EduBoost SA — Auth Router"""
from datetime import datetime, timedelta
import hashlib

import jwt
import structlog
from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.core.config import settings
from app.api.core.database import AsyncSessionFactory
from app.api.models.api_models import (
    ErrorResponse,
    GuardianLoginRequest,
    LearnerSessionRequest,
    LearnerSessionResponse,
    TokenResponse,
)

log = structlog.get_logger()
router = APIRouter()

# Rate limiter for auth endpoints (stricter: 10 req/min)
limiter = Limiter(key_func=get_remote_address)


def _create_token(data: dict) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def _verify_guardian(email: str, learner_pseudonym_id: str) -> bool:
    email_hash = hashlib.sha256(email.lower().strip().encode()).hexdigest()
    try:
        async with AsyncSessionFactory() as session:
            identity = await session.execute(
                text(
                    "SELECT 1 FROM learner_identities "
                    "WHERE pseudonym_id = :pid "
                    "AND COALESCE(data_deletion_requested, false) = false "
                    "LIMIT 1"
                ),
                {"pid": learner_pseudonym_id},
            )
            if identity.first() is None:
                log.warning("auth.guardian.identity_not_found", pseudonym=learner_pseudonym_id)
                return False

            consent = await session.execute(
                text(
                    "SELECT guardian_email_hash FROM consent_audit "
                    "WHERE pseudonym_id = :pid AND event_type = 'CONSENT_GIVEN'"
                ),
                {"pid": learner_pseudonym_id},
            )
            hashes = [row[0] for row in consent.fetchall() if row[0]]
            if hashes and email_hash not in hashes:
                log.warning("auth.guardian.email_mismatch", pseudonym=learner_pseudonym_id)
                return False
        return True
    except Exception as e:
        log.error("auth.guardian.db_error", error=str(e))
        return False


@router.post(
    "/guardian/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def guardian_login(request: Request, request_body: GuardianLoginRequest):
    if not await _verify_guardian(request_body.email, request_body.learner_pseudonym_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(error="Invalid guardian credentials", code="INVALID_GUARDIAN_CREDENTIALS").model_dump(),
        )

    email_hash = hashlib.sha256(request_body.email.lower().strip().encode()).hexdigest()
    token = _create_token({"sub": email_hash, "learner_id": request_body.learner_pseudonym_id, "role": "guardian"})
    return TokenResponse(access_token=token, expires_in=settings.JWT_EXPIRY_HOURS * 3600)


@router.post("/learner/session", response_model=LearnerSessionResponse)
@limiter.limit("10/minute")
async def create_learner_session(request: Request, request_body: LearnerSessionRequest):
    token = _create_token({"sub": request_body.learner_id, "role": "learner"})
    return LearnerSessionResponse(session_token=token, expires_in=settings.JWT_EXPIRY_HOURS * 3600)
