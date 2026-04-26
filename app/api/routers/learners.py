"""EduBoost SA — Learners Router (Pseudonymous CRUD)"""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.api.core.database import AsyncSessionFactory, get_db
from app.api.models.api_models import (
    DeletionRequestResponse,
    ErrorResponse,
    LearnerCreateRequest,
    LearnerCreateResponse,
    LearnerUpdateRequest,
    LearnerUpdateResponse,
    SubjectMasteryEntry,
    SubjectMasteryResponse,
)

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=LearnerCreateResponse,
    responses={500: {"model": ErrorResponse}},
)
async def create_learner(request: LearnerCreateRequest, db=Depends(get_db)):
    """Create a new pseudonymous learner profile. Returns the UUID — no PII stored."""
    learner_id = uuid4()
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(
                text("""
                    INSERT INTO learners (learner_id, grade, home_language, avatar_id, learning_style)
                    VALUES (:id, :grade, :lang, :avatar, :style::jsonb)
                """),
                {
                    "id": str(learner_id),
                    "grade": request.grade,
                    "lang": request.home_language,
                    "avatar": request.avatar_id,
                    "style": request.model_dump_json(include={"learning_style"})
                    .replace('{"learning_style":', "")
                    .rstrip("}"),
                },
            )
            await session.commit()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(error="Failed to create learner", code="LEARNER_CREATE_FAILED", details={"reason": str(e)}).model_dump(),
            ) from e
    return LearnerCreateResponse(learner_id=learner_id, grade=request.grade)


@router.get("/{learner_id}")
async def get_learner(learner_id: UUID, db=Depends(get_db)):
    """Retrieve pseudonymous learner profile by UUID."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("SELECT * FROM learners WHERE learner_id = :id"), {"id": str(learner_id)})
        row = result.mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(error="Learner not found", code="LEARNER_NOT_FOUND").model_dump(),
            )
        return dict(row)


@router.patch(
    "/{learner_id}",
    response_model=LearnerUpdateResponse,
    responses={400: {"model": ErrorResponse}},
)
async def update_learner(learner_id: UUID, request: LearnerUpdateRequest, db=Depends(get_db)):
    """Update learner profile fields."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error="No fields to update", code="EMPTY_UPDATE").model_dump(),
        )
    set_clause = ", ".join([f"{k} = :{k}" for k in updates])
    updates["id"] = str(learner_id)
    async with AsyncSessionFactory() as session:
        await session.execute(text(f"UPDATE learners SET {set_clause}, last_active_at = NOW() WHERE learner_id = :id"), updates)
        await session.commit()
    return LearnerUpdateResponse(updated=True)


@router.delete(
    "/{learner_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DeletionRequestResponse,
)
async def request_data_deletion(learner_id: UUID, db=Depends(get_db)):
    """POPIA Right to Erasure — marks learner for deletion within 30 days."""
    async with AsyncSessionFactory() as session:
        await session.execute(
            text("""
                UPDATE learner_identities
                SET data_deletion_requested = TRUE
                WHERE pseudonym_id = :id
            """),
            {"id": str(learner_id)},
        )
        await session.commit()
    return DeletionRequestResponse(
        status="deletion_requested",
        learner_id=learner_id,
        note="Data will be purged within 30 days per POPIA Section 24.",
    )


@router.get("/{learner_id}/mastery", response_model=SubjectMasteryResponse)
async def get_subject_mastery(learner_id: UUID, db=Depends(get_db)):
    """Retrieve subject mastery scores for a learner."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("SELECT * FROM subject_mastery WHERE learner_id = :id"), {"id": str(learner_id)})
        rows = result.mappings().all()
        return SubjectMasteryResponse(
            learner_id=learner_id,
            mastery=[SubjectMasteryEntry(**dict(r)) for r in rows],
        )
