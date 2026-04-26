"""
EduBoost SA — Study Plan Service Unit Tests

Tests for study plan generation algorithm, prioritization logic,
and schedule distribution.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.services.study_plan_service import StudyPlanService
from app.api.models.db_models import Learner, SubjectMastery, StudyPlan


class TestStudyPlanGeneration:
    """Test suite for study plan generation algorithm."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def study_plan_service(self, mock_session):
        """Create a StudyPlanService instance with mocked session."""
        return StudyPlanService(mock_session)

    @pytest.fixture
    def mock_learner(self):
        """Create a mock learner."""
        learner = MagicMock(spec=Learner)
        learner.learner_id = uuid4()
        learner.grade = 3
        learner.home_language = "eng"
        learner.overall_mastery = 0.65
        learner.streak_days = 5
        learner.total_xp = 350
        learner.created_at = datetime.now()
        learner.last_active_at = datetime.now()
        return learner

    @pytest.mark.asyncio
    async def test_generate_plan_with_valid_learner(self, study_plan_service, mock_session, mock_learner):
        """Test generating a plan for a valid learner."""
        # Setup
        learner_id = mock_learner.learner_id
        mock_session.get.return_value = mock_learner
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        subjects_mastery = {
            "MATH": 0.6,
            "ENG": 0.7,
            "NS": 0.5,
        }
        knowledge_gaps = ["fractions", "division", "volume"]

        # Execute
        result = await study_plan_service.generate_plan(
            learner_id=learner_id,
            grade=3,
            subjects_mastery=subjects_mastery,
            knowledge_gaps=knowledge_gaps,
            gap_ratio=0.4,
        )

        # Assert
        assert result is not None
        assert result["learner_id"] == str(learner_id)
        assert result["grade"] == 3
        assert "schedule" in result
        assert result["gap_ratio"] == 0.4
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_plan_learner_not_found(self, study_plan_service, mock_session):
        """Test generating a plan for a non-existent learner."""
        # Setup
        learner_id = uuid4()
        mock_session.get.return_value = None

        # Execute & Assert
        with pytest.raises(ValueError, match="not found"):
            await study_plan_service.generate_plan(
                learner_id=learner_id,
                grade=3,
                subjects_mastery={"MATH": 0.6},
                knowledge_gaps=[],
            )

    def test_prioritize_subjects_high_gap_first(self, study_plan_service):
        """Test that subjects with higher gaps are prioritized."""
        subjects_mastery = {
            "MATH": 0.3,  # Lowest mastery = highest gap
            "ENG": 0.8,   # Highest mastery = lowest gap
            "NS": 0.5,
        }

        # Execute
        prioritized = study_plan_service._prioritize_subjects(subjects_mastery)

        # Assert
        # MATH should be first (lowest score)
        assert prioritized[0] == "MATH"
        # ENG should be last (highest score)
        assert prioritized[-1] == "ENG"

    def test_generate_remediation_tasks_creates_gap_specific_tasks(self, study_plan_service):
        """Test that remediation tasks target specific knowledge gaps."""
        knowledge_gaps = ["fractions", "division", "volume"]

        # Execute
        remediation_tasks = study_plan_service._generate_remediation_tasks(
            knowledge_gaps=knowledge_gaps,
            grade=3,
            grade_band="R-3",
        )

        # Assert
        assert len(remediation_tasks) > 0
        task_str = str(remediation_tasks)
        # At least some tasks should mention the gaps
        assert any(gap in task_str for gap in knowledge_gaps)

    def test_generate_grade_tasks_creates_advancement_tasks(self, study_plan_service):
        """Test that grade-level tasks are created for advancement."""
        focus_subjects = ["MATH", "ENG"]

        # Execute
        grade_tasks = study_plan_service._generate_grade_tasks(
            focus_subjects=focus_subjects,
            grade=3,
            grade_band="R-3",
        )

        # Assert
        assert len(grade_tasks) > 0
        # Tasks should be assigned to focus subjects
        task_str = str(grade_tasks)
        assert any(subject in task_str for subject in focus_subjects)

    def test_generate_weekly_schedule_distribution(self, study_plan_service):
        """Test that weekly schedule distributes tasks across days."""
        subjects_mastery = {"MATH": 0.5, "ENG": 0.6}
        knowledge_gaps = ["reading", "addition"]

        # Execute
        schedule = study_plan_service._generate_weekly_schedule(
            grade=2,
            grade_band="R-3",
            subjects_mastery=subjects_mastery,
            knowledge_gaps=knowledge_gaps,
            gap_ratio=0.4,
        )

        # Assert
        assert "monday" in schedule
        assert "sunday" in schedule
        
        # Count total tasks
        total_tasks = sum(len(tasks) for tasks in schedule.values())
        assert total_tasks > 0
        
        # Weekdays should have more tasks than weekends
        weekday_tasks = sum(len(schedule[day]) for day in ["monday", "tuesday", "wednesday", "thursday", "friday"])
        weekend_tasks = sum(len(schedule[day]) for day in ["saturday", "sunday"])
        assert weekday_tasks >= weekend_tasks

    def test_gap_ratio_affects_remediation_distribution(self, study_plan_service):
        """Test that gap_ratio properly affects task distribution."""
        subjects_mastery = {"MATH": 0.4, "ENG": 0.7}
        knowledge_gaps = ["counting", "shapes"]

        # Execute with high remediation ratio
        schedule_high_gap = study_plan_service._generate_weekly_schedule(
            grade=1,
            grade_band="R-3",
            subjects_mastery=subjects_mastery,
            knowledge_gaps=knowledge_gaps,
            gap_ratio=0.6,  # 60% remediation
        )

        # Execute with low remediation ratio
        schedule_low_gap = study_plan_service._generate_weekly_schedule(
            grade=1,
            grade_band="R-3",
            subjects_mastery=subjects_mastery,
            knowledge_gaps=knowledge_gaps,
            gap_ratio=0.2,  # 20% remediation
        )

        # Assert
        # Both should produce schedules
        assert schedule_high_gap is not None
        assert schedule_low_gap is not None
        
        # Schedule structure should be consistent
        assert set(schedule_high_gap.keys()) == set(schedule_low_gap.keys())

    def test_grade_band_determines_focus_areas(self, study_plan_service):
        """Test that grade band (R-3 vs 4-7) determines focus areas."""
        # Junior level (R-3)
        junior_schedule = study_plan_service._generate_weekly_schedule(
            grade=2,
            grade_band="R-3",
            subjects_mastery={"MATH": 0.5},
            knowledge_gaps=["counting"],
            gap_ratio=0.4,
        )

        # Senior level (4-7)
        senior_schedule = study_plan_service._generate_weekly_schedule(
            grade=5,
            grade_band="4-7",
            subjects_mastery={"MATH": 0.5},
            knowledge_gaps=["fractions"],
            gap_ratio=0.4,
        )

        # Both should produce valid schedules
        assert junior_schedule is not None
        assert senior_schedule is not None

    def test_determine_week_focus_from_gaps(self, study_plan_service):
        """Test that week focus is determined from knowledge gaps."""
        knowledge_gaps = ["fractions", "decimals"]
        subjects_mastery = {"MATH": 0.3, "ENG": 0.8}

        # Execute
        week_focus = study_plan_service._determine_week_focus(
            knowledge_gaps=knowledge_gaps,
            subjects_mastery=subjects_mastery,
        )

        # Assert
        assert week_focus is not None
        # Focus should include math (lowest mastery)
        assert "MATH" in str(week_focus).upper()


class TestStudyPlanValidation:
    """Test input validation and error handling."""

    @pytest.fixture
    def study_plan_service(self):
        """Create a StudyPlanService with mock session."""
        return StudyPlanService(AsyncMock())

    def test_gap_ratio_validation_bounds(self, study_plan_service):
        """Test that gap_ratio is validated within bounds."""
        # Gap ratio should be between 0.3 and 0.6
        
        # Valid ratios should pass
        valid_ratios = [0.3, 0.4, 0.5, 0.6]
        for ratio in valid_ratios:
            # Should not raise
            schedule = study_plan_service._generate_weekly_schedule(
                grade=3,
                grade_band="R-3",
                subjects_mastery={"MATH": 0.5},
                knowledge_gaps=["addition"],
                gap_ratio=ratio,
            )
            assert schedule is not None

    def test_schedule_has_all_days(self, study_plan_service):
        """Test that generated schedule includes all 7 days."""
        schedule = study_plan_service._generate_weekly_schedule(
            grade=3,
            grade_band="R-3",
            subjects_mastery={"MATH": 0.5},
            knowledge_gaps=["addition"],
            gap_ratio=0.4,
        )

        expected_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in expected_days:
            assert day in schedule


class TestStudyPlanAlgorithmQuality:
    """Test quality characteristics of the algorithm."""

    @pytest.fixture
    def study_plan_service(self):
        """Create a StudyPlanService with mock session."""
        return StudyPlanService(AsyncMock())

    def test_consistent_task_distribution(self, study_plan_service):
        """Test that tasks are distributed consistently across days."""
        schedule = study_plan_service._generate_weekly_schedule(
            grade=3,
            grade_band="R-3",
            subjects_mastery={"MATH": 0.5, "ENG": 0.6},
            knowledge_gaps=["addition", "reading"],
            gap_ratio=0.4,
        )

        # Get task counts per day
        day_counts = [len(tasks) for tasks in schedule.values()]
        
        # Standard deviation should be low (relatively balanced)
        if day_counts:
            mean = sum(day_counts) / len(day_counts)
            variance = sum((x - mean) ** 2 for x in day_counts) / len(day_counts)
            std_dev = variance ** 0.5
            
            # Expect relatively even distribution (std dev < 2 tasks)
            assert std_dev < 2.0

    def test_no_empty_schedules(self, study_plan_service):
        """Test that generated schedules are never completely empty."""
        schedule = study_plan_service._generate_weekly_schedule(
            grade=3,
            grade_band="R-3",
            subjects_mastery={"MATH": 0.5},
            knowledge_gaps=["addition"],
            gap_ratio=0.4,
        )

        total_tasks = sum(len(tasks) for tasks in schedule.values())
        assert total_tasks > 0, "Schedule should never be completely empty"

    def test_prioritization_ranks_subjects_logically(self, study_plan_service):
        """Test that subject prioritization makes logical sense."""
        subjects_mastery = {
            "MATH": 0.2,    # Weakest
            "NS": 0.5,      # Middle
            "ENG": 0.9,     # Strongest
        }

        prioritized = study_plan_service._prioritize_subjects(subjects_mastery)

        # Weakest should be first, strongest last
        assert prioritized.index("MATH") < prioritized.index("NS")
        assert prioritized.index("NS") < prioritized.index("ENG")
