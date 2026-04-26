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


# ── Diagnostic Benchmarking Endpoints ─────────────────────────────────────────

@router.get("/benchmark/metrics")
async def get_diagnostic_benchmark_metrics(days: int = 30):
    """
    Get diagnostic engine benchmark metrics.
    
    Returns performance statistics including:
    - Average session duration
    - Accuracy metrics
    - Standard error of measurement
    - SLO compliance status
    """
    from app.api.services.diagnostic_benchmark_service import DiagnosticBenchmarkService
    
    async with AsyncSessionFactory() as session:
        try:
            service = DiagnosticBenchmarkService(session)
            metrics = await service.get_benchmark_metrics(days=days)
            
            return {
                "success": True,
                "metrics": {
                    "period_days": metrics.period_days,
                    "total_sessions": metrics.total_sessions,
                    "sessions_in_period": metrics.sessions_in_period,
                    "avg_session_duration_ms": round(metrics.avg_session_duration_ms, 2),
                    "p95_session_duration_ms": round(metrics.p95_session_duration_ms, 2),
                    "min_session_duration_ms": round(metrics.min_session_duration_ms, 2),
                    "max_session_duration_ms": round(metrics.max_session_duration_ms, 2),
                    "avg_accuracy": round(metrics.avg_accuracy, 4),
                    "min_accuracy": round(metrics.min_accuracy, 4),
                    "max_accuracy": round(metrics.max_accuracy, 4),
                    "avg_theta_sem": round(metrics.avg_theta_sem, 4),
                    "avg_items_administered": metrics.avg_items_administered,
                },
                "slo_status": {
                    "targets_met": metrics.targets_met,
                    "violations": metrics.violations if metrics.violations else ["None - all SLOs met!"],
                },
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Benchmark metrics failed: {e}") from e


@router.get("/benchmark/report")
async def get_diagnostic_benchmark_report(days: int = 30):
    """
    Get comprehensive diagnostic benchmark report.
    
    Includes overall metrics, per-subject performance, per-grade performance,
    and SLO compliance status.
    """
    from app.api.services.diagnostic_benchmark_service import DiagnosticBenchmarkService
    
    async with AsyncSessionFactory() as session:
        try:
            service = DiagnosticBenchmarkService(session)
            report = await service.generate_benchmark_report(days=days)
            
            return {
                "success": True,
                "report": report,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Benchmark report failed: {e}") from e


@router.get("/benchmark/by-subject")
async def get_diagnostic_metrics_by_subject(days: int = 30):
    """
    Get diagnostic metrics broken down by subject.
    
    Useful for identifying which subject assessments may need calibration.
    """
    from app.api.services.diagnostic_benchmark_service import DiagnosticBenchmarkService
    
    async with AsyncSessionFactory() as session:
        try:
            service = DiagnosticBenchmarkService(session)
            by_subject = await service.get_accuracy_by_subject(days=days)
            
            return {
                "success": True,
                "period_days": days,
                "by_subject": by_subject,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Subject metrics failed: {e}") from e


@router.get("/benchmark/by-grade")
async def get_diagnostic_metrics_by_grade(days: int = 30):
    """
    Get diagnostic metrics broken down by grade level.
    
    Useful for identifying grade-level trends in assessment performance.
    """
    from app.api.services.diagnostic_benchmark_service import DiagnosticBenchmarkService
    
    async with AsyncSessionFactory() as session:
        try:
            service = DiagnosticBenchmarkService(session)
            by_grade = await service.get_accuracy_by_grade(days=days)
            
            return {
                "success": True,
                "period_days": days,
                "by_grade": by_grade,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Grade metrics failed: {e}") from e
