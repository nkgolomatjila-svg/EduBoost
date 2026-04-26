"""
EduBoost SA — Study Plan Generation Service

Generates dynamic CAPS-aligned study plans that blend remediation
and grade-level pacing based on diagnostic output and learner progress.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.db_models import Learner, SubjectMastery, StudyPlan


# CAPS subject codes
CAPS_SUBJECTS = {
    "MATH": {"name": "Mathematics", "weekly_hours": 6},
    "ENG": {"name": "English", "weekly_hours": 5},
    "AFR": {"name": "Afrikaans", "weekly_hours": 4},
    "LIFE": {"name": "Life Skills", "weekly_hours": 4},
    "NS": {"name": "Natural Sciences", "weekly_hours": 3},
    "SS": {"name": "Social Sciences", "weekly_hours": 3},
}

# Grade-level focus areas per subject
GRADE_FOCUS = {
    (0, 3): {
        "MATH": ["counting", "addition", "subtraction", "shapes", "measurement"],
        "ENG": ["phonics", "reading", "writing", "vocabulary"],
        "LIFE": ["health", "safety", "community"],
    },
    (4, 7): {
        "MATH": ["fractions", "multiplication", "geometry", "data", "algebra"],
        "ENG": ["comprehension", "grammar", "writing", "literature"],
        "NS": ["matter", "energy", "life_systems", "earth_science"],
        "SS": ["history", "geography", "civics"],
    },
}


class StudyPlanService:
    """Service for generating and managing study plans."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_plan(
        self,
        learner_id: UUID,
        grade: int,
        knowledge_gaps: list[str] | None = None,
        subjects_mastery: dict | None = None,
        gap_ratio: float = 0.4,
    ) -> dict:
        """
        Generate a weekly study plan for a learner.
        
        Args:
            learner_id: The learner's UUID
            grade: Current grade level (0-7)
            knowledge_gaps: List of concept codes that are weak
            subjects_mastery: Dict of subject_code -> mastery_score
            gap_ratio: Ratio of time for remediation (0.3-0.6)
        
        Returns:
            Study plan dict with schedule and metadata
        """
        # Get learner data
        learner = await self.session.get(Learner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        # Get subject mastery data
        if not subjects_mastery:
            subjects_mastery = await self._get_subject_mastery(learner_id)

        # Get knowledge gaps if not provided
        if not knowledge_gaps:
            knowledge_gaps = await self._get_knowledge_gaps(learner_id)

        # Determine grade band
        grade_band = "R-3" if grade <= 3 else "4-7"

        # Generate weekly schedule
        schedule = self._generate_weekly_schedule(
            grade=grade,
            grade_band=grade_band,
            subjects_mastery=subjects_mastery,
            knowledge_gaps=knowledge_gaps,
            gap_ratio=gap_ratio,
        )

        # Determine week focus
        week_focus = self._determine_week_focus(knowledge_gaps, subjects_mastery)

        # Create study plan record
        week_start = self._get_week_start()
        plan = StudyPlan(
            plan_id=uuid.uuid4(),
            learner_id=learner_id,
            week_start=week_start,
            schedule=schedule,
            gap_ratio=gap_ratio,
            week_focus=week_focus,
            generated_by="ALGORITHM",
        )

        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(plan)

        return {
            "plan_id": str(plan.plan_id),
            "learner_id": str(plan.learner_id),
            "week_start": plan.week_start.isoformat(),
            "schedule": plan.schedule,
            "gap_ratio": plan.gap_ratio,
            "week_focus": plan.week_focus,
            "generated_by": plan.generated_by,
            "created_at": plan.created_at.isoformat(),
        }

    async def _get_subject_mastery(self, learner_id: UUID) -> dict[str, float]:
        """Fetch subject mastery scores for a learner."""
        result = await self.session.execute(
            select(SubjectMastery).where(SubjectMastery.learner_id == learner_id)
        )
        mastery_records = result.scalars().all()

        mastery = {}
        for record in mastery_records:
            mastery[record.subject_code] = record.mastery_score

        return mastery

    async def _get_knowledge_gaps(self, learner_id: UUID) -> list[str]:
        """Fetch knowledge gaps for a learner."""
        result = await self.session.execute(
            select(SubjectMastery).where(SubjectMastery.learner_id == learner_id)
        )
        mastery_records = result.scalars().all()

        gaps = []
        for record in mastery_records:
            if record.knowledge_gaps:
                gaps.extend(record.knowledge_gaps)

        return list(set(gaps))

    def _generate_weekly_schedule(
        self,
        grade: int,
        grade_band: str,
        subjects_mastery: dict[str, float],
        knowledge_gaps: list[str],
        gap_ratio: float,
    ) -> dict:
        """
        Generate a weekly schedule balancing remediation and grade-level content.
        
        Strategy:
        - gap_ratio (e.g., 0.4) of time goes to remediation of weak areas
        - (1 - gap_ratio) of time goes to grade-level advancement
        """
        schedule = {
            "monday": [],
            "tuesday": [],
            "wednesday": [],
            "thursday": [],
            "friday": [],
            "saturday": [],
            "sunday": [],
        }

        # Determine subjects to focus on
        focus_subjects = self._prioritize_subjects(subjects_mastery)

        # Generate daily tasks
        days = list(schedule.keys())
        remediation_tasks = self._generate_remediation_tasks(knowledge_gaps, grade, grade_band)
        grade_tasks = self._generate_grade_tasks(focus_subjects, grade, grade_band)

        # Split tasks between remediation and grade-level
        total_tasks = remediation_tasks + grade_tasks
        remediation_count = int(len(total_tasks) * gap_ratio)
        grade_count = len(total_tasks) - remediation_count

        # Distribute tasks across days
        task_index = 0
        for day_idx, day in enumerate(days):
            # 2-3 tasks per day
            daily_task_count = 2 if day_idx < 5 else 1  # Less on weekends

            for _ in range(daily_task_count):
                if task_index < len(total_tasks):
                    schedule[day].append(total_tasks[task_index])
                    task_index += 1

        return schedule

    def _prioritize_subjects(self, subjects_mastery: dict[str, float]) -> list[tuple[str, float]]:
        """Prioritize subjects by mastery score (lowest first)."""
        prioritized = [
            (subject, score) for subject, score in subjects_mastery.items()
            if score is not None
        ]
        prioritized.sort(key=lambda x: x[1])
        return prioritized

    def _generate_remediation_tasks(
        self,
        knowledge_gaps: list[str],
        grade: int,
        grade_band: str,
    ) -> list[dict]:
        """Generate remediation tasks for knowledge gaps."""
        tasks = []

        for gap in knowledge_gaps[:5]:  # Limit to 5 gaps per week
            tasks.append({
                "task_id": str(uuid.uuid4()),
                "type": "remediation",
                "concept": gap,
                "subject": self._concept_to_subject(gap),
                "title": f"Review: {gap.replace('_', ' ').title()}",
                "duration_minutes": 20,
                "difficulty": "adaptive",
                "is_gap_focus": True,
            })

        return tasks

    def _generate_grade_tasks(
        self,
        focus_subjects: list[tuple[str, float]],
        grade: int,
        grade_band: str,
    ) -> list[dict]:
        """Generate grade-level advancement tasks."""
        tasks = []

        # Get focus areas for grade
        focus_areas = GRADE_FOCUS.get((0, 3) if grade <= 3 else (4, 7), {})

        for subject, _ in focus_subjects[:4]:  # Focus on top 4 subjects
            subject_areas = focus_areas.get(subject, [])
            if subject_areas:
                tasks.append({
                    "task_id": str(uuid.uuid4()),
                    "type": "lesson",
                    "subject": subject,
                    "concept": subject_areas[0],
                    "title": f"{CAPS_SUBJECTS.get(subject, {}).get('name', subject)}: {subject_areas[0].replace('_', ' ').title()}",
                    "duration_minutes": 25,
                    "difficulty": "grade_level",
                    "is_gap_focus": False,
                })

        return tasks

    def _concept_to_subject(self, concept: str) -> str:
        """Map a concept code to a subject code."""
        concept_lower = concept.lower()

        if any(x in concept_lower for x in ["math", "number", "calc", "geom", "algebra"]):
            return "MATH"
        if any(x in concept_lower for x in ["read", "write", "phon", "vocab", "gram"]):
            return "ENG"
        if any(x in concept_lower for x in ["life", "health", "sci", "bio"]):
            return "LIFE"
        if any(x in concept_lower for x in ["nature", "phys", "chem"]):
            return "NS"
        if any(x in concept_lower for x in ["history", "geog", "civic"]):
            return "SS"

        return "MATH"  # Default

    def _determine_week_focus(
        self,
        knowledge_gaps: list[str],
        subjects_mastery: dict[str, float],
    ) -> str:
        """Determine the main focus for the week."""
        if knowledge_gaps:
            top_gap = knowledge_gaps[0]
            return f"Focus on {top_gap.replace('_', ' ').title()} remediation"

        # Find weakest subject
        if subjects_mastery:
            weakest = min(subjects_mastery.items(), key=lambda x: x[1] or 1.0)
            subject_name = CAPS_SUBJECTS.get(weakest[0], {}).get("name", weakest[0])
            return f"Strengthen {subject_name} fundamentals"

        return "General review and advancement"

    def _get_week_start(self) -> datetime:
        """Get the start of the current week (Monday)."""
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)

    async def get_current_plan(self, learner_id: UUID) -> Optional[StudyPlan]:
        """Get the current active study plan for a learner."""
        result = await self.session.execute(
            select(StudyPlan)
            .where(StudyPlan.learner_id == learner_id)
            .order_by(StudyPlan.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def refresh_plan(
        self,
        learner_id: UUID,
        gap_ratio: float = 0.4,
    ) -> dict:
        """Regenerate a study plan with updated data."""
        # Get latest learner data
        learner = await self.session.get(Learner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        # Get subject mastery
        subjects_mastery = await self._get_subject_mastery(learner_id)

        # Get knowledge gaps
        knowledge_gaps = await self._get_knowledge_gaps(learner_id)

        # Generate new plan
        return await self.generate_plan(
            learner_id=learner_id,
            grade=learner.grade,
            knowledge_gaps=knowledge_gaps,
            subjects_mastery=subjects_mastery,
            gap_ratio=gap_ratio,
        )

    def _generate_task_rationale(self, task: dict, subjects_mastery: dict[str, float], knowledge_gaps: list[str]) -> str:
        """
        Generate a human-readable rationale for why a task is in the plan.
        
        This explains to educators and parents WHY each task is included.
        """
        task_type = task.get("type", "unknown")
        subject = task.get("subject", "")
        concept = task.get("concept", "")
        
        if task_type == "remediation":
            # Task is remediating a knowledge gap
            mastery = subjects_mastery.get(subject, 0)
            gap_reason = f"This concept is identified as a knowledge gap (current mastery: {int(mastery*100)}%)"
            
            if mastery < 0.4:
                level = "significant weakness"
            elif mastery < 0.6:
                level = "area for improvement"
            else:
                level = "minor gap"
            
            return f"Remediation task: {concept.replace('_', ' ').title()} is a {level} in {CAPS_SUBJECTS.get(subject, {}).get('name', subject)}. {gap_reason}. Targeted practice will strengthen this foundation."
        
        elif task_type == "lesson":
            # Task is advancing grade-level content
            return f"Grade-level advancement: Introducing {concept.replace('_', ' ').title()} in {CAPS_SUBJECTS.get(subject, {}).get('name', subject)}. This aligns with Grade {task.get('grade', 'current')} CAPS curriculum pacing."
        
        elif task_type == "assessment":
            # Task is a diagnostic/assessment
            return f"Assessment: This diagnostic in {concept} will help us identify your current level and personalize future lessons."
        
        elif task_type == "review":
            # Task is review/consolidation
            return f"Review and consolidation: Reinforcing {concept.replace('_', ' ').title()} to build automaticity and confidence."
        
        else:
            return f"Complete this {concept.replace('_', ' ').title()} task in {subject} to progress in your learning journey."

    async def get_plan_with_rationale(
        self,
        learner_id: UUID,
    ) -> dict:
        """
        Get the current study plan with rationale explanations for each task.
        
        This is useful for educators and parents who need to understand
        why tasks are assigned.
        """
        plan = await self.get_current_plan(learner_id)
        if not plan:
            raise ValueError(f"No active study plan for learner {learner_id}")

        # Get subject mastery for context
        subjects_mastery = await self._get_subject_mastery(learner_id)
        knowledge_gaps = await self._get_knowledge_gaps(learner_id)

        # Add rationale to each task
        schedule_with_rationale = {}
        for day, tasks in (plan.schedule or {}).items():
            schedule_with_rationale[day] = []
            for task in tasks:
                rationale = self._generate_task_rationale(
                    task=task,
                    subjects_mastery=subjects_mastery,
                    knowledge_gaps=knowledge_gaps,
                )
                schedule_with_rationale[day].append({
                    **task,
                    "rationale": rationale,
                })

        return {
            "plan_id": str(plan.plan_id),
            "learner_id": str(learner_id),
            "week_start": plan.week_start.isoformat(),
            "week_focus": plan.week_focus,
            "week_focus_rationale": f"This week focuses on {plan.week_focus.lower()}. This targets your strongest gaps while maintaining grade-level pace.",
            "gap_ratio": plan.gap_ratio,
            "remediation_percentage": int(plan.gap_ratio * 100),
            "advancement_percentage": int((1 - plan.gap_ratio) * 100),
            "schedule_with_rationale": schedule_with_rationale,
            "generated_by": plan.generated_by,
            "created_at": plan.created_at.isoformat(),
        }