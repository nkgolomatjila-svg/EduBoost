"""EduBoost SA — Study Plans Router"""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.models.api_models import CurrentStudyPlanResponse, ErrorResponse, StudyPlanGenerationResponse
from app.api.services.study_plan_service import StudyPlanService
from app.api.core.database import AsyncSessionFactory

router = APIRouter()


class StudyPlanRequest(BaseModel):
    learner_id: UUID
    grade: int = Field(ge=0, le=7)
    knowledge_gaps: list = Field(default_factory=list)
    subjects_mastery: dict = Field(default_factory=dict)
    gap_ratio: float = Field(default=0.4, ge=0.3, le=0.6)


@router.post("/generate", status_code=status.HTTP_200_OK, response_model=StudyPlanGenerationResponse)
async def generate_study_plan(request: StudyPlanRequest):
    """Generate a new study plan for a learner."""
    async with AsyncSessionFactory() as session:
        try:
            service = StudyPlanService(session)
            plan = await service.generate_plan(
                learner_id=request.learner_id,
                grade=request.grade,
                knowledge_gaps=request.knowledge_gaps,
                subjects_mastery=request.subjects_mastery,
                gap_ratio=request.gap_ratio,
            )
            return StudyPlanGenerationResponse(success=True, plan=plan)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Study plan generation failed: {e}") from e


@router.get("/{learner_id}/current", response_model=CurrentStudyPlanResponse)
async def get_current_plan(learner_id: UUID):
    """Retrieve the learner's current active study plan."""
    async with AsyncSessionFactory() as session:
        service = StudyPlanService(session)
        plan = await service.get_current_plan(learner_id)

        if not plan:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(error="No study plan found for this learner", code="STUDY_PLAN_NOT_FOUND").model_dump(),
            )

        return CurrentStudyPlanResponse(
            success=True,
            plan={
                "plan_id": str(plan.plan_id),
                "learner_id": str(plan.learner_id),
                "week_start": plan.week_start.isoformat(),
                "schedule": plan.schedule,
                "gap_ratio": plan.gap_ratio,
                "week_focus": plan.week_focus,
                "generated_by": plan.generated_by,
                "created_at": plan.created_at.isoformat(),
            },
        )


@router.post("/{learner_id}/refresh", response_model=StudyPlanGenerationResponse)
async def refresh_study_plan(learner_id: UUID, gap_ratio: float = Field(default=0.4, ge=0.3, le=0.6)):
    """Regenerate a study plan with updated learner data."""
    async with AsyncSessionFactory() as session:
        try:
            service = StudyPlanService(session)
            plan = await service.refresh_plan(learner_id=learner_id, gap_ratio=gap_ratio)
            return StudyPlanGenerationResponse(success=True, plan=plan)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Study plan refresh failed: {e}") from e
