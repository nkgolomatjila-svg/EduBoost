"""EduBoost SA — Lessons Router"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.core.database import get_db
from app.api.models.api_models import (
    CachedLessonResponse,
    ErrorResponse,
    LessonFeedback,
    LessonGenerationResponse,
    LessonMeta,
    LessonRequest,
)

router = APIRouter()


def _lesson_params(req: LessonRequest) -> dict:
    return {
        "subject_code": req.subject_code,
        "subject_label": req.subject_label,
        "topic": req.topic,
        "home_language": req.home_language,
        "learning_style_primary": req.learning_style_primary,
        "mastery_prior": req.mastery_prior,
        "has_gap": req.has_gap,
        "gap_grade": req.gap_grade,
    }


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    response_model=LessonGenerationResponse,
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def generate_lesson_endpoint(request: LessonRequest, _db=Depends(get_db)):
    from app.api.orchestrator import OrchestratorRequest, get_orchestrator
    from app.api.services.lesson_service import LLMOutputValidationError

    try:
        orch = get_orchestrator()
        result = await orch.run(
            OrchestratorRequest(
                operation="GENERATE_LESSON",
                learner_id=str(request.learner_id),
                grade=request.grade,
                params=_lesson_params(request),
            )
        )
    except LLMOutputValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(error="LLM output validation failed", code="LLM_OUTPUT_INVALID", details={"reason": str(e), "errors": e.errors}).model_dump(),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(error="Lesson pipeline error", code="LESSON_PIPELINE_ERROR", details={"reason": str(e)}).model_dump(),
        ) from e

    if not result.success:
        if result.stamp_status == "REJECTED":
            raise HTTPException(
                status_code=403,
                detail=ErrorResponse(error="Constitutional violation", code="CONSTITUTIONAL_REJECTION", details={"reason": result.error}).model_dump(),
            )
        if result.error and "validation" in result.error.lower():
            raise HTTPException(
                status_code=422,
                detail=ErrorResponse(error="Lesson validation failed", code="LESSON_VALIDATION_FAILED", details={"reason": result.error}).model_dump(),
            )
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(error="Lesson generation failed", code="LESSON_GENERATION_FAILED", details={"reason": result.error}).model_dump(),
        )

    return LessonGenerationResponse(
        success=True,
        lesson=result.output,
        meta=LessonMeta(
            stamp_status=result.stamp_status,
            stamp_id=result.stamp_id,
            ether_archetype=result.ether_archetype,
            constitutional_health=result.constitutional_health,
            latency_ms=result.latency_ms,
        ),
    )


@router.get("/{lesson_id}", status_code=status.HTTP_200_OK, response_model=CachedLessonResponse)
async def get_cached_lesson(lesson_id: str):
    try:
        import json
        import redis.asyncio as redis_lib

        from app.api.core.config import settings

        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        raw = await r.get(f"lesson:{lesson_id}")
        await r.aclose()
        if raw:
            return CachedLessonResponse(success=True, lesson=json.loads(raw), source="cache")
    except Exception:
        pass
    raise HTTPException(
        status_code=404,
        detail=ErrorResponse(error="Lesson not found", code="LESSON_NOT_FOUND", details={"lesson_id": lesson_id}).model_dump(),
    )


@router.post("/{lesson_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def submit_feedback(lesson_id: str, feedback: LessonFeedback, background_tasks: BackgroundTasks, db=Depends(get_db)):
    background_tasks.add_task(_store_feedback_bg, lesson_id, feedback)


async def _store_feedback_bg(lesson_id: str, feedback: LessonFeedback) -> None:
    try:
        from sqlalchemy import text

        from app.api.core.database import AsyncSessionFactory

        async with AsyncSessionFactory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO session_events (
                        learner_id, session_id, lesson_id, event_type,
                        lesson_efficacy_score, time_on_task_ms
                    )
                    SELECT l.learner_id, gen_random_uuid(), :lesson_id,
                           'FEEDBACK', :les, :time_ms
                    FROM learners l WHERE l.learner_id = :lid LIMIT 1
                """
                ),
                {
                    "lesson_id": lesson_id,
                    "les": feedback.rating / 5.0,
                    "time_ms": feedback.time_spent_seconds * 1000,
                    "lid": str(feedback.learner_id),
                },
            )
            await session.commit()
    except Exception as e:
        import structlog

        structlog.get_logger().warning("feedback.store_failed", error=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """Get lesson cache statistics."""
    from app.api.services.lesson_service import get_lesson_cache
    
    cache = get_lesson_cache()
    return {"cache": cache.stats()}


@router.delete("/cache")
async def clear_cache():
    """Clear the lesson cache."""
    from app.api.services.lesson_service import get_lesson_cache
    
    cache = get_lesson_cache()
    count = cache.clear()
    return {"cleared": count, "success": True}
