"""EduBoost SA — Parent Portal Router"""
import hashlib
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.models.api_models import (
    ConsentResponse,
    ErrorResponse,
    LearnerProgressResponse,
    ParentReportResponse,
)
from app.api.services.parent_portal_service import ParentPortalService
from app.api.core.database import AsyncSessionFactory

router = APIRouter()


class ParentReportRequest(BaseModel):
    learner_id: UUID
    guardian_id: UUID  # Required for consent verification


class ConsentRequest(BaseModel):
    learner_id: UUID
    guardian_email: str
    consent_version: int = 1
    consented: bool


@router.get("/{learner_id}/progress/{guardian_id}", response_model=LearnerProgressResponse)
async def get_learner_progress(learner_id: UUID, guardian_id: UUID):
    """Get learner progress summary for parent portal."""
    async with AsyncSessionFactory() as session:
        try:
            service = ParentPortalService(session)
            progress = await service.get_learner_progress_summary(learner_id, guardian_id)
            return LearnerProgressResponse(success=True, progress=progress)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get progress: {e}") from e


@router.get("/{learner_id}/diagnostics/{guardian_id}")
async def get_diagnostic_trends(learner_id: UUID, guardian_id: UUID, days: int = 30):
    """Get diagnostic assessment trends for a learner."""
    async with AsyncSessionFactory() as session:
        try:
            service = ParentPortalService(session)
            trends = await service.get_diagnostic_trends(learner_id, guardian_id, days)
            return {"success": True, "trends": trends}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get trends: {e}") from e


@router.get("/{learner_id}/study-plan/{guardian_id}")
async def get_study_plan_adherence(learner_id: UUID, guardian_id: UUID):
    """Get study plan adherence metrics."""
    async with AsyncSessionFactory() as session:
        try:
            service = ParentPortalService(session)
            adherence = await service.get_study_plan_adherence(learner_id, guardian_id)
            return {"success": True, "adherence": adherence}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get adherence: {e}") from e


@router.post("/report/generate", status_code=status.HTTP_200_OK, response_model=ParentReportResponse)
async def generate_parent_report(request: ParentReportRequest):
    """Generate AI-assisted parent report."""
    async with AsyncSessionFactory() as session:
        try:
            service = ParentPortalService(session)
            report = await service.generate_parent_report(
                learner_id=request.learner_id,
                guardian_id=request.guardian_id,
            )
            return ParentReportResponse(success=True, report=report)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Report generation failed: {e}") from e


@router.post(
    "/consent",
    status_code=status.HTTP_201_CREATED,
    response_model=ConsentResponse,
    responses={500: {"model": ErrorResponse}},
)
async def record_consent(request: ConsentRequest):
    import hashlib

    from sqlalchemy import text

    from app.api.core.database import AsyncSessionFactory

    email_hash = hashlib.sha256(request.guardian_email.lower().encode()).hexdigest()
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("""
                    INSERT INTO consent_audit (pseudonym_id, event_type, consent_version, guardian_email_hash)
                    VALUES (:pid, :etype, :cv, :eh)
                """),
                {
                    "pid": str(request.learner_id),
                    "etype": "CONSENT_GIVEN" if request.consented else "CONSENT_WITHDRAWN",
                    "cv": request.consent_version,
                    "eh": email_hash,
                },
            )
            await session.commit()
            action = ExecutiveAction(action_type=ActionType.RECORD_CONSENT, learner_id_hash=str(request.learner_id), grade=0, params={"consent_version": request.consent_version, "consented": request.consented}, claimed_rules=[])
            await get_fourth_estate().publish_domain_event(EventType.CONSENT_RECORDED, action, {"consented": request.consented, "consent_version": request.consent_version})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Consent recording failed: {e}") from e
    return {"recorded": True, "popia_compliant": True}


@router.get("/{learner_id}/progress", response_model=LearnerProgressResponse)
async def get_learner_progress(learner_id: UUID):
    """Get aggregate progress data for parent view."""
    from sqlalchemy import text

    from app.api.core.database import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        learner = await session.execute(
            text("SELECT grade, streak_days, total_xp, overall_mastery FROM learners WHERE learner_id = :id"),
            {"id": str(learner_id)},
        )
        row = learner.mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(error="Learner not found", code="LEARNER_NOT_FOUND").model_dump(),
            )
        mastery = await session.execute(
            text("SELECT subject_code, mastery_score FROM subject_mastery WHERE learner_id = :id"),
            {"id": str(learner_id)},
        )
        mastery_rows = mastery.mappings().all()
        return LearnerProgressResponse(
            success=True,
            grade=row["grade"],
            streak_days=row["streak_days"],
            total_xp=row["total_xp"],
            overall_mastery=row["overall_mastery"],
            subjects={r["subject_code"]: r["mastery_score"] for r in mastery_rows},
        )


# POPIA Deletion Endpoints
class DeletionRequest(BaseModel):
    learner_id: UUID
    guardian_id: UUID
    reason: Optional[str] = None


class DeletionStatusRequest(BaseModel):
    learner_id: UUID
    guardian_id: UUID


@router.post("/deletion/request", status_code=status.HTTP_202_ACCEPTED)
async def request_deletion(request: DeletionRequest):
    """Submit a POPIA deletion request (right to erasure)."""
    from app.api.services.popia_deletion_service import PopiaDeletionService

    async with AsyncSessionFactory() as session:
        try:
            service = PopiaDeletionService(session)
            result = await service.request_deletion(
                learner_id=request.learner_id,
                guardian_id=request.guardian_id,
                reason=request.reason,
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Deletion request failed: {e}") from e


@router.post("/deletion/execute", status_code=status.HTTP_200_OK)
async def execute_deletion(request: DeletionRequest):
    """Execute POPIA deletion (anonymize learner data)."""
    from app.api.services.popia_deletion_service import PopiaDeletionService

    async with AsyncSessionFactory() as session:
        try:
            service = PopiaDeletionService(session)
            result = await service.execute_deletion(
                learner_id=request.learner_id,
                guardian_id=request.guardian_id,
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Deletion execution failed: {e}") from e


@router.get("/deletion/status/{learner_id}/{guardian_id}")
async def get_deletion_status(learner_id: UUID, guardian_id: UUID):
    """Get the status of a POPIA deletion request."""
    from app.api.services.popia_deletion_service import PopiaDeletionService

    async with AsyncSessionFactory() as session:
        try:
            service = PopiaDeletionService(session)
            result = await service.get_deletion_status(learner_id, guardian_id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Status check failed: {e}") from e


@router.get("/export/{learner_id}/{guardian_id}")
async def export_learner_data(learner_id: UUID, guardian_id: UUID):
    """
    Export all learner data (POPIA requirement before deletion).
    
    Parents have the right to receive a copy of all stored data
    before exercising the right to erasure.
    """
    from app.api.services.popia_deletion_service import PopiaDeletionService

    async with AsyncSessionFactory() as session:
        try:
            service = PopiaDeletionService(session)
            result = await service.export_data(learner_id, guardian_id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export failed: {e}") from e