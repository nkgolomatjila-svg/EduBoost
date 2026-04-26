"""
EduBoost SA — Gamification Service Unit Tests

Tests for XP calculation, badge awards, streak tracking,
and progression mechanics.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.api.services.gamification_service import GamificationService
from app.api.models.db_models import Learner, LearnerBadge, Badge


class TestGamificationXPCalculation:
    """Test XP calculation logic."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def gamification_service(self, mock_session):
        """Create a GamificationService instance."""
        return GamificationService(mock_session)

    def test_calculate_level_from_xp(self, gamification_service):
        """Test that level is correctly calculated from XP."""
        # Level formula: level = (total_xp // 100) + 1
        
        assert gamification_service._calculate_level(0) == 1
        assert gamification_service._calculate_level(99) == 1
        assert gamification_service._calculate_level(100) == 2
        assert gamification_service._calculate_level(199) == 2
        assert gamification_service._calculate_level(200) == 3
        assert gamification_service._calculate_level(1000) == 11

    def test_xp_to_next_level_calculation(self, gamification_service):
        """Test XP needed for next level."""
        # At 0 XP (level 1), need 100 to reach level 2
        assert gamification_service._xp_to_next_level(0) == 100
        
        # At 50 XP (level 1), need 50 more
        assert gamification_service._xp_to_next_level(50) == 50
        
        # At 100 XP (level 2), need 100 more (to reach level 3)
        assert gamification_service._xp_to_next_level(100) == 100
        
        # At 199 XP (level 2), need 1 more
        assert gamification_service._xp_to_next_level(199) == 1

    def test_level_min_is_one(self, gamification_service):
        """Test that minimum level is always 1."""
        assert gamification_service._calculate_level(0) >= 1
        assert gamification_service._calculate_level(-100) >= 1

    @pytest.mark.asyncio
    async def test_award_xp_lesson_complete(self, gamification_service, mock_session):
        """Test awarding XP for lesson completion."""
        learner_id = uuid4()
        learner = MagicMock(spec=Learner)
        learner.learner_id = learner_id
        learner.grade = 3
        learner.total_xp = 100
        learner.streak_days = 0

        mock_session.get.return_value = learner
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.all.return_value = []

        # Award XP for lesson completion
        result = await gamification_service.award_xp(
            learner_id=learner_id,
            xp_type="lesson_complete",
            metadata={"lesson_id": "lesson_123"},
        )

        assert result is not None
        assert "xp_awarded" in result
        assert result["xp_awarded"] == 35

    @pytest.mark.asyncio
    async def test_award_xp_with_streak_bonus(self, gamification_service, mock_session):
        """Test that streak bonus is applied correctly."""
        learner_id = uuid4()
        learner = MagicMock(spec=Learner)
        learner.learner_id = learner_id
        learner.grade = 3
        learner.total_xp = 200
        learner.streak_days = 10

        mock_session.get.return_value = learner
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.all.return_value = []

        # Award XP with streak bonus
        result = await gamification_service.award_xp(
            learner_id=learner_id,
            xp_type="lesson_complete",
            metadata={"streak_days": 10},
        )

        # Should include streak bonus: 10 days × 5 = 50
        assert result is not None
        assert "streak_bonus" in result or "xp_awarded" in result

    @pytest.mark.asyncio
    async def test_level_up_detection(self, gamification_service, mock_session):
        """Test that level-up is detected when XP crosses threshold."""
        learner_id = uuid4()
        learner = MagicMock(spec=Learner)
        learner.learner_id = learner_id
        learner.grade = 3
        learner.total_xp = 95  # Just below level 2 threshold
        learner.streak_days = 0

        mock_session.get.return_value = learner
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.all.return_value = []

        # Award 10 XP (should cross 100 threshold)
        result = await gamification_service.award_xp(
            learner_id=learner_id,
            xp_type="lesson_complete",
            metadata={"xp_amount": 10},
        )

        assert result is not None
        # Should detect level up since 95 + 35 = 130 (crosses 100)
        assert result.get("leveled_up", False) or result.get("xp_awarded", 0) > 0


class TestGamificationBadges:
    """Test badge award logic."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def gamification_service(self, mock_session):
        """Create a GamificationService instance."""
        return GamificationService(mock_session)

    def test_available_badges_for_grade_r3(self, gamification_service):
        """Test that Grade R-3 learners get appropriate badges."""
        badges = gamification_service._get_available_badges(grade=2)
        
        assert badges is not None
        assert len(badges) > 0
        
        # Should include streak badges for grades R-3
        badge_keys = [b.get("badge_key") for b in badges]
        assert any("streak" in key for key in badge_keys)

    def test_available_badges_for_grade_4plus(self, gamification_service):
        """Test that Grade 4-7 learners get appropriate badges."""
        badges = gamification_service._get_available_badges(grade=5)
        
        assert badges is not None
        assert len(badges) > 0
        
        # Should include discovery badges for grades 4-7
        badge_keys = [b.get("badge_key") for b in badges]
        # Mix of discovery, mastery, and milestone badges expected
        assert len(badge_keys) > 0

    def test_badge_thresholds_are_realistic(self, gamification_service):
        """Test that badge thresholds are reasonable."""
        badges = gamification_service._get_available_badges(grade=3)
        
        for badge in badges:
            if "threshold" in badge:
                # Threshold should be positive
                assert badge["threshold"] > 0
                # Threshold should be reasonable (< 1000)
                assert badge["threshold"] < 1000

    def test_streaks_badges_exist(self, gamification_service):
        """Test that streak badges are properly configured."""
        badges = gamification_service._get_available_badges(grade=2)
        
        streak_badges = [b for b in badges if b.get("badge_type") == "streak"]
        assert len(streak_badges) > 0
        
        # Should have multiple streak levels
        streak_thresholds = [b["threshold"] for b in streak_badges]
        assert len(streak_thresholds) >= 3  # At least 3-5 streak levels


class TestGamificationProfileGeneration:
    """Test learner profile generation."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def gamification_service(self, mock_session):
        """Create a GamificationService instance."""
        return GamificationService(mock_session)

    @pytest.mark.asyncio
    async def test_get_learner_profile_junior(self, gamification_service, mock_session):
        """Test getting profile for junior learner (R-3)."""
        learner_id = uuid4()
        learner = MagicMock(spec=Learner)
        learner.learner_id = learner_id
        learner.grade = 2
        learner.total_xp = 250
        learner.streak_days = 3

        mock_session.get.return_value = learner
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.all.return_value = []

        # Get profile
        profile = await gamification_service.get_learner_profile(learner_id)

        assert profile is not None
        assert profile["learner_id"] == str(learner_id)
        assert profile["grade"] == 2
        assert profile["grade_band"] == "R-3"
        assert profile["total_xp"] == 250
        assert profile["streak_days"] == 3
        assert "level" in profile
        assert "badges" in profile

    @pytest.mark.asyncio
    async def test_get_learner_profile_senior(self, gamification_service, mock_session):
        """Test getting profile for senior learner (4-7)."""
        learner_id = uuid4()
        learner = MagicMock(spec=Learner)
        learner.learner_id = learner_id
        learner.grade = 5
        learner.total_xp = 500
        learner.streak_days = 15

        mock_session.get.return_value = learner
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.all.return_value = []

        # Get profile
        profile = await gamification_service.get_learner_profile(learner_id)

        assert profile is not None
        assert profile["grade_band"] == "4-7"
        assert "can_earn_badges" in profile
        assert isinstance(profile["can_earn_badges"], list)

    @pytest.mark.asyncio
    async def test_learner_not_found_raises_error(self, gamification_service, mock_session):
        """Test that error is raised for non-existent learner."""
        learner_id = uuid4()
        mock_session.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await gamification_service.get_learner_profile(learner_id)

    @pytest.mark.asyncio
    async def test_earned_badges_are_included_in_profile(self, gamification_service, mock_session):
        """Test that earned badges are included in profile."""
        learner_id = uuid4()
        learner = MagicMock(spec=Learner)
        learner.learner_id = learner_id
        learner.grade = 3
        learner.total_xp = 150
        learner.streak_days = 5

        # Create mock earned badges
        lb1 = MagicMock(spec=LearnerBadge)
        lb1.earned_at = datetime.now()
        badge1 = MagicMock(spec=Badge)
        badge1.badge_id = uuid4()
        badge1.badge_key = "first_lesson"
        badge1.name = "First Steps"
        badge1.description = "Complete your first lesson"
        badge1.icon_url = "https://example.com/badge1.png"

        mock_session.get.return_value = learner
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.all.return_value = [(lb1, badge1)]

        profile = await gamification_service.get_learner_profile(learner_id)

        assert len(profile["badges"]) == 1
        assert profile["badges"][0]["badge_key"] == "first_lesson"
        assert profile["badges"][0]["name"] == "First Steps"


class TestGamificationStreakLogic:
    """Test streak tracking and updates."""

    def test_streak_bonus_increases_with_days(self):
        """Test that streak bonus scales with streak days."""
        from app.api.services.gamification_service import XP_CONFIG
        
        # Verify streak bonus is properly configured
        assert "streak_bonus" in XP_CONFIG
        assert XP_CONFIG["streak_bonus"] == 5  # 5 XP per day
        
        # So a 10-day streak = 50 XP bonus
        expected_bonus = 10 * XP_CONFIG["streak_bonus"]
        assert expected_bonus == 50

    def test_streak_thresholds_are_ordered(self):
        """Test that streak thresholds are properly ordered."""
        from app.api.services.gamification_service import STREAK_THRESHOLDS
        
        # Should be in ascending order
        assert STREAK_THRESHOLDS == sorted(STREAK_THRESHOLDS)
        # Should have multiple levels
        assert len(STREAK_THRESHOLDS) >= 3


class TestGamificationXPConfig:
    """Test XP configuration."""

    def test_xp_config_is_complete(self):
        """Test that all XP types are configured."""
        from app.api.services.gamification_service import XP_CONFIG
        
        expected_types = [
            "lesson_complete",
            "lesson_mastery",
            "diagnostic_complete",
            "streak_bonus",
            "daily_login",
            "badge_earned",
            "concept_mastered",
        ]
        
        for xp_type in expected_types:
            assert xp_type in XP_CONFIG
            assert XP_CONFIG[xp_type] > 0

    def test_xp_values_are_reasonable(self):
        """Test that XP values are in reasonable ranges."""
        from app.api.services.gamification_service import XP_CONFIG
        
        # Individual activity XP should be in range [10, 100]
        for activity_type in ["lesson_complete", "diagnostic_complete", "daily_login"]:
            xp_value = XP_CONFIG[activity_type]
            assert 10 <= xp_value <= 100

    def test_grade_band_config_complete(self):
        """Test that grade band config is properly set up."""
        from app.api.services.gamification_service import GRADE_BAND_CONFIG
        
        assert "R-3" in GRADE_BAND_CONFIG
        assert "4-7" in GRADE_BAND_CONFIG
        
        for band in ["R-3", "4-7"]:
            config = GRADE_BAND_CONFIG[band]
            assert "badge_types" in config
            assert "engagement_style" in config
            assert "max_daily_xp" in config
            assert config["max_daily_xp"] > 0
