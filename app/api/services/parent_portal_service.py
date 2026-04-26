"""
EduBoost SA — Parent Portal Service

Provides progress summaries, diagnostic trends, study plan adherence,
and AI-assisted parent reports with clear, explainable language.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.db_models import (
    Learner,
    LearnerIdentity,
    SubjectMastery,
    StudyPlan,
    SessionEvent,
    DiagnosticSession,
    ConsentAudit,
)


class ParentPortalService:
    """Service for parent portal functionality."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_learner_progress_summary(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> dict:
        """
        Get a progress summary for a learner's guardian.
        
        Requires consent verification before exposing data.
        """
        # Verify guardian has access
        await self._verify_guardian_access(learner_id, guardian_id)

        # Get learner data
        learner = await self.session.get(Learner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        # Get subject mastery
        result = await self.session.execute(
            select(SubjectMastery).where(SubjectMastery.learner_id == learner_id)
        )
        subject_mastery = result.scalars().all()

        # Build progress summary
        subjects = []
        for sm in subject_mastery:
            subjects.append({
                "subject_code": sm.subject_code,
                "mastery_score": sm.mastery_score,
                "concepts_mastered": len(sm.concepts_mastered or []),
                "knowledge_gaps": sm.knowledge_gaps or [],
                "last_assessed": sm.last_assessed_at.isoformat() if sm.last_assessed_at else None,
            })

        # Calculate overall progress
        avg_mastery = sum(s["mastery_score"] for s in subjects) / len(subjects) if subjects else 0

        return {
            "learner_id": str(learner_id),
            "grade": learner.grade,
            "overall_mastery": learner.overall_mastery,
            "average_subject_mastery": avg_mastery,
            "streak_days": learner.streak_days,
            "total_xp": learner.total_xp,
            "subjects": subjects,
            "last_active": learner.last_active_at.isoformat() if learner.last_active_at else None,
        }

    async def get_diagnostic_trends(
        self,
        learner_id: UUID,
        guardian_id: UUID,
        days: int = 30,
    ) -> dict:
        """Get diagnostic assessment trends over time."""
        # Verify guardian access
        await self._verify_guardian_access(learner_id, guardian_id)

        # Get diagnostic sessions
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await self.session.execute(
            select(DiagnosticSession)
            .where(
                DiagnosticSession.learner_id == learner_id,
                DiagnosticSession.completed_at >= cutoff_date,
            )
            .order_by(DiagnosticSession.started_at)
        )
        sessions = result.scalars().all()

        trends = []
        for session in sessions:
            trends.append({
                "session_id": str(session.session_id),
                "subject_code": session.subject_code,
                "grade_level": session.grade_level,
                "theta_estimate": session.theta_estimate,
                "mastery_score": session.final_mastery_score,
                "items_administered": session.items_administered,
                "knowledge_gaps": session.knowledge_gaps or [],
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            })

        # Calculate improvement
        if len(trends) >= 2:
            first_mastery = trends[0].get("mastery_score", 0)
            last_mastery = trends[-1].get("mastery_score", 0)
            improvement = last_mastery - first_mastery
        else:
            improvement = 0

        return {
            "learner_id": str(learner_id),
            "period_days": days,
            "sessions_count": len(trends),
            "trends": trends,
            "improvement": improvement,
        }

    async def get_study_plan_adherence(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> dict:
        """Get study plan adherence metrics."""
        # Verify guardian access
        await self._verify_guardian_access(learner_id, guardian_id)

        # Get current study plan
        result = await self.session.execute(
            select(StudyPlan)
            .where(StudyPlan.learner_id == learner_id)
            .order_by(StudyPlan.created_at.desc())
            .limit(1)
        )
        plan = result.scalar_one_or_none()

        if not plan:
            return {
                "learner_id": str(learner_id),
                "has_active_plan": False,
                "message": "No study plan currently active",
            }

        # Get session events for this plan period
        plan_start = plan.week_start
        result = await self.session.execute(
            select(SessionEvent)
            .where(
                SessionEvent.learner_id == learner_id,
                SessionEvent.occurred_at >= plan_start,
            )
        )
        events = result.scalars().all()

        # Calculate adherence
        schedule = plan.schedule or {}
        total_planned = sum(len(tasks) for tasks in schedule.values())
        completed_tasks = len([e for e in events if e.event_type == "lesson_complete"])

        adherence_rate = (completed_tasks / total_planned * 100) if total_planned > 0 else 0

        return {
            "learner_id": str(learner_id),
            "has_active_plan": True,
            "plan_id": str(plan.plan_id),
            "week_start": plan.week_start.isoformat(),
            "week_focus": plan.week_focus,
            "gap_ratio": plan.gap_ratio,
            "total_planned_tasks": total_planned,
            "completed_tasks": completed_tasks,
            "adherence_rate": adherence_rate,
            "schedule": schedule,
        }

    async def generate_parent_report(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> dict:
        """
        Generate an AI-assisted parent report with clear, explainable language.
        
        This creates a human-readable summary of learner progress.
        """
        # Verify guardian access
        await self._verify_guardian_access(learner_id, guardian_id)

        # Get all data
        progress = await self.get_learner_progress_summary(learner_id, guardian_id)
        trends = await self.get_diagnostic_trends(learner_id, guardian_id)
        adherence = await self.get_study_plan_adherence(learner_id, guardian_id)

        # Generate report sections
        report_sections = []

        # Overall summary
        mastery_pct = int(progress["overall_mastery"] * 100)
        if mastery_pct >= 70:
            status = "performing well"
            emoji = "🌟"
        elif mastery_pct >= 40:
            status = "making progress"
            emoji = "📈"
        else:
            status = "needs additional support"
            emoji = "💪"

        report_sections.append({
            "section": "overall_summary",
            "title": "Overall Progress",
            "content": f"{emoji} Your child is {status} in their learning journey. They have achieved {mastery_pct}% overall mastery across {len(progress['subjects'])} subjects.",
        })

        # Subject breakdown
        subject_lines = []
        for subject in progress["subjects"]:
            mastery = int(subject["mastery_score"] * 100)
            subject_lines.append(f"- **{subject['subject_code']}**: {mastery}% mastery")

        report_sections.append({
            "section": "subject_breakdown",
            "title": "Subject Performance",
            "content": "\n".join(subject_lines) if subject_lines else "No subject data available yet.",
        })

        # Streak and engagement
        if progress["streak_days"] > 0:
            report_sections.append({
                "section": "engagement",
                "title": "Learning Streak",
                "content": f"🔥 Your child has a {progress['streak_days']}-day learning streak! They've earned {progress['total_xp']} XP total.",
            })

        # Diagnostic trends
        if trends["sessions_count"] > 0:
            improvement = trends["improvement"]
            if improvement > 0.1:
                trend_msg = f"Diagnostic assessments show a {int(improvement*100)}% improvement over the past {trends['period_days']} days."
            elif improvement < -0.1:
                trend_msg = f"Diagnostic assessments show a {int(abs(improvement)*100)}% decrease over the past {trends['period_days']} days. Consider reviewing the study plan."
            else:
                trend_msg = "Diagnostic assessments show stable performance."

            report_sections.append({
                "section": "diagnostics",
                "title": "Assessment Trends",
                "content": trend_msg,
            })

        # Study plan adherence
        if adherence["has_active_plan"]:
            rate = int(adherence["adherence_rate"])
            if rate >= 80:
                adherence_msg = f"Excellent! Your child has completed {rate}% of their planned study tasks this week."
            elif rate >= 50:
                adherence_msg = f"Your child has completed {rate}% of their planned tasks. Encouraging consistent study habits will help."
            else:
                adherence_msg = f"Your child has completed {rate}% of planned tasks. Let's work together to build better study routines."

            report_sections.append({
                "section": "study_plan",
                "title": "This Week's Study Plan",
                "content": f"{adherence_msg}\n\nFocus areas: {adherence.get('week_focus', 'General review')}",
            })

        # Recommendations
        recommendations = []
        if mastery_pct < 50:
            recommendations.append("Consider scheduling extra practice sessions in weaker subjects.")
        if progress["streak_days"] < 3:
            recommendations.append("Encourage daily learning to build a streak and reinforce habits.")
        if adherence["has_active_plan"] and adherence["adherence_rate"] < 50:
            recommendations.append("Review the study plan together and adjust if needed.")

        if recommendations:
            report_sections.append({
                "section": "recommendations",
                "title": "Recommendations",
                "content": "\n".join(f"- {r}" for r in recommendations),
            })

        return {
            "learner_id": str(learner_id),
            "report_date": datetime.now().isoformat(),
            "sections": report_sections,
        }

    async def _verify_guardian_access(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> None:
        """
        Verify that a guardian has consent to access learner data.
        
        Raises HTTPException if access is not permitted.
        """
        from fastapi import HTTPException

        # Check consent audit for this guardian
        result = await self.session.execute(
            select(ConsentAudit)
            .where(
                ConsentAudit.pseudonym_id == learner_id,
                ConsentAudit.event_type == "consent_granted",
            )
            .order_by(ConsentAudit.occurred_at.desc())
            .limit(1)
        )
        consent = result.scalar_one_or_none()

        if not consent:
            raise HTTPException(
                status_code=403,
                detail="Guardian consent required to access learner data",
            )

        # Check if consent has been revoked
        result = await self.session.execute(
            select(ConsentAudit)
            .where(
                ConsentAudit.pseudonym_id == learner_id,
                ConsentAudit.event_type == "consent_revoked",
            )
            .order_by(ConsentAudit.occurred_at.desc())
            .limit(1)
        )
        revoked = result.scalar_one_or_none()

        if revoked and revoked.occurred_at > consent.occurred_at:
            raise HTTPException(
                status_code=403,
                detail="Guardian consent has been revoked",
            )