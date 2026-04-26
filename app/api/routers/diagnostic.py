"""EduBoost SA — Diagnostic Router (IRT Adaptive Assessment)"""
import random
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.api.models.api_models import (
    DiagnosticItemsResponse,
    DiagnosticItem,
    DiagnosticRequest,
    DiagnosticRunResponse,
    DiagnosticSessionSummary,
    ErrorResponse,
)
from app.api.core.database import AsyncSessionFactory

router = APIRouter()


async def _persist_diagnostic_session(
    learner_id: uuid.UUID,
    subject_code: str,
    grade: int,
    theta: float,
    sem: float,
    items_administered: int,
    knowledge_gaps: list,
    final_mastery: float,
) -> uuid.UUID:
    """Persist diagnostic session to database."""
    session_id = uuid.uuid4()
    async with AsyncSessionFactory() as session:
        await session.execute(
            text("""
                INSERT INTO diagnostic_sessions 
                (session_id, learner_id, subject_code, grade_level, status, theta_estimate, 
                 standard_error, items_administered, items_total, final_mastery_score, 
                 knowledge_gaps, started_at, completed_at)
                VALUES (:session_id, :learner_id, :subject_code, :grade_level, 'completed', 
                        :theta, :sem, :items_administered, 20, :final_mastery, 
                        :knowledge_gaps, :started_at, :completed_at)
            """),
            {
                "session_id": session_id,
                "learner_id": learner_id,
                "subject_code": subject_code,
                "grade_level": grade,
                "theta": theta,
                "sem": sem,
                "items_administered": items_administered,
                "final_mastery": final_mastery,
                "knowledge_gaps": knowledge_gaps,
                "started_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
            },
        )
        await session.commit()
    return session_id


async def _persist_diagnostic_responses(
    session_id: uuid.UUID,
    responses: list,
) -> None:
    """Persist individual diagnostic responses to database."""
    async with AsyncSessionFactory() as session:
        for resp in responses:
            await session.execute(
                text("""
                    INSERT INTO diagnostic_responses
                    (response_id, session_id, item_id, learner_response, is_correct, 
                     time_taken_ms, theta_before, theta_after, sem_before, sem_after, 
                     information_gain, responded_at)
                    VALUES (:response_id, :session_id, :item_id, :learner_response, 
                            :is_correct, :time_taken_ms, :theta_before, :theta_after, 
                            :sem_before, :sem_after, :information_gain, :responded_at)
                """),
                {
                    "response_id": uuid.uuid4(),
                    "session_id": session_id,
                    "item_id": resp.item_id,
                    "learner_response": "correct" if resp.is_correct else "incorrect",
                    "is_correct": resp.is_correct,
                    "time_taken_ms": resp.time_on_task_ms,
                    "theta_before": 0.0,  # Would need to track this properly
                    "theta_after": 0.0,
                    "sem_before": 0.0,
                    "sem_after": 0.0,
                    "information_gain": 0.0,
                    "responded_at": datetime.utcnow(),
                },
            )
        await session.commit()


@router.post(
    "/run",
    status_code=status.HTTP_200_OK,
    response_model=DiagnosticRunResponse,
    responses={400: {"model": ErrorResponse}},
)
async def run_diagnostic(request: DiagnosticRequest):
    """
    Run an IRT adaptive diagnostic session.
    Returns gap report: theta, mastery score, has_gap, gap_grade.
    Learner_id is used for audit only — never passed to any model.
    """
    from app.api.orchestrator import OrchestratorRequest, get_orchestrator

    try:
        subject_code = request.subject_code
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error="Invalid subject code", code="INVALID_SUBJECT_CODE", details={"subject_code": request.subject_code}).model_dump(),
        ) from e

    try:
        # Run diagnostic through orchestrator (handles constitutional review, profiling, audit)
        orch = get_orchestrator()
        result = await orch.run(
            OrchestratorRequest(
                operation="RUN_DIAGNOSTIC",
                learner_id=str(request.learner_id),
                grade=request.grade,
                params={"subject_code": request.subject_code, "max_questions": request.max_questions},
            )
        )

        if not result.success:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error=result.error or "Diagnostic pipeline error",
                    code="DIAGNOSTIC_PIPELINE_ERROR",
                    details={"reason": result.error},
                ).model_dump(),
            )

        # Extract results from orchestrator
        output = result.output
        gap_report = output.get("gap_report", {})
        session_summary = output.get("session_summary", {})

        # Persist diagnostic session to database
        session_id = await _persist_diagnostic_session(
            learner_id=request.learner_id,
            subject_code=request.subject_code,
            grade=request.grade,
            theta=session_summary.get("theta", 0.0),
            sem=session_summary.get("sem", 0.0),
            items_administered=session_summary.get("questions_administered", 0),
            knowledge_gaps=gap_report.get("knowledge_gaps", []),
            final_mastery=gap_report.get("mastery_score", 0.0),
        )

        # Note: Full response persistence would require tracking responses through orchestrator
        # For now, we log that the session was persisted
        print(f"Diagnostic session {session_id} persisted for learner {request.learner_id}")

        return DiagnosticRunResponse(
            success=True,
            gap_report=gap_report,
            session_summary=DiagnosticSessionSummary(
                questions_administered=session_summary.get("questions_administered", 0),
                theta=session_summary.get("theta", 0.0),
                sem=session_summary.get("sem", 0.0),
                gap_probe_active=session_summary.get("gap_probe_active", False),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="Diagnostic pipeline error",
                code="DIAGNOSTIC_PIPELINE_ERROR",
                details={"reason": str(e)},
            ).model_dump(),
        ) from e


@router.get(
    "/items/{subject_code}/{grade}",
    response_model=DiagnosticItemsResponse,
    responses={400: {"model": ErrorResponse}},
)
async def get_diagnostic_items(subject_code: str, grade: int):
    from app.api.ml.irt_engine import SAMPLE_ITEMS, SubjectCode

    try:
        subject = SubjectCode(subject_code)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error="Invalid subject", code="INVALID_SUBJECT_CODE", details={"subject_code": subject_code}).model_dump(),
        ) from e

    items = [
        DiagnosticItem(
            item_id=i.item_id,
            question_text=i.question_text,
            options=i.options,
            story_context=i.story_context,
            difficulty_label=i.difficulty_label,
        )
        for i in SAMPLE_ITEMS
        if i.subject == subject and i.grade == grade
    ]
    return DiagnosticItemsResponse(subject=subject_code, grade=grade, items=items, count=len(items))


@router.get("/history/{learner_id}")
async def get_diagnostic_history(learner_id: uuid.UUID):
    """Get diagnostic session history for a learner."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            text("""
                SELECT session_id, subject_code, grade_level, status, theta_estimate,
                       standard_error, items_administered, final_mastery_score, 
                       knowledge_gaps, started_at, completed_at
                FROM diagnostic_sessions
                WHERE learner_id = :learner_id
                ORDER BY started_at DESC
                LIMIT 50
            """),
            {"learner_id": learner_id},
        )
        rows = result.fetchall()
        
    sessions = []
    for row in rows:
        sessions.append({
            "session_id": str(row[0]),
            "subject_code": row[1],
            "grade_level": row[2],
            "status": row[3],
            "theta_estimate": row[4],
            "standard_error": row[5],
            "items_administered": row[6],
            "final_mastery_score": row[7],
            "knowledge_gaps": row[8] or [],
            "started_at": row[9].isoformat() if row[9] else None,
            "completed_at": row[10].isoformat() if row[10] else None,
        })
    
    return {"learner_id": str(learner_id), "sessions": sessions, "count": len(sessions)}
