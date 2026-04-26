"""
EduBoost SA — Diagnostic Benchmarking Service

Monitors and tracks diagnostic engine performance metrics including:
- Estimation accuracy (theta estimates)
- Response time (diagnostic session duration)
- Item calibration quality
- Gap detection accuracy
"""
import time
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.db_models import DiagnosticSession, DiagnosticResponse


@dataclass
class BenchmarkMetrics:
    """Container for benchmark metrics."""
    avg_session_duration_ms: float
    min_session_duration_ms: float
    max_session_duration_ms: float
    p95_session_duration_ms: float
    
    avg_accuracy: float
    min_accuracy: float
    max_accuracy: float
    
    avg_theta_sem: float  # Standard error of measurement
    avg_items_administered: int
    
    total_sessions: int
    sessions_in_period: int
    period_days: int
    
    targets_met: bool
    violations: List[str]


class DiagnosticBenchmarkService:
    """Service for tracking and analyzing diagnostic engine performance."""
    
    # SLO targets
    SLO_AVG_SESSION_TIME_MS = 600  # Average session should be < 600ms
    SLO_P95_SESSION_TIME_MS = 1200  # 95th percentile should be < 1200ms
    SLO_MAX_SEM = 0.8  # Standard error of measurement should be low
    SLO_MIN_ACCURACY = 0.80  # Minimum accuracy threshold
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_benchmark_metrics(self, days: int = 30) -> BenchmarkMetrics:
        """
        Calculate benchmark metrics for the diagnostic engine.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            BenchmarkMetrics object with performance data
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all diagnostic sessions in the period
        result = await self.session.execute(
            select(DiagnosticSession).where(
                DiagnosticSession.completed_at >= cutoff_date
            )
        )
        sessions = result.scalars().all()
        total_sessions = len(sessions)
        
        if total_sessions == 0:
            # No data, return empty metrics
            return BenchmarkMetrics(
                avg_session_duration_ms=0,
                min_session_duration_ms=0,
                max_session_duration_ms=0,
                p95_session_duration_ms=0,
                avg_accuracy=0,
                min_accuracy=0,
                max_accuracy=0,
                avg_theta_sem=0,
                avg_items_administered=0,
                total_sessions=0,
                sessions_in_period=0,
                period_days=days,
                targets_met=False,
                violations=[],
            )
        
        # Calculate session duration statistics
        session_durations = []
        accuracy_scores = []
        sems = []
        items_administered_list = []
        
        for session in sessions:
            # Calculate session duration
            if session.started_at and session.completed_at:
                duration = (session.completed_at - session.started_at).total_seconds() * 1000
                session_durations.append(duration)
            
            # Calculate accuracy (items correct / items administered)
            if session.items_administered > 0:
                accuracy = session.items_correct / session.items_administered
                accuracy_scores.append(accuracy)
            
            # Track SEM
            sems.append(session.sem)
            items_administered_list.append(session.items_administered)
        
        # Calculate percentiles
        session_durations.sort()
        if session_durations:
            avg_duration = statistics.mean(session_durations)
            min_duration = min(session_durations)
            max_duration = max(session_durations)
            p95_duration = session_durations[int(len(session_durations) * 0.95) - 1] if len(session_durations) > 1 else session_durations[0]
        else:
            avg_duration = min_duration = max_duration = p95_duration = 0
        
        # Calculate accuracy metrics
        if accuracy_scores:
            avg_accuracy = statistics.mean(accuracy_scores)
            min_accuracy = min(accuracy_scores)
            max_accuracy = max(accuracy_scores)
        else:
            avg_accuracy = min_accuracy = max_accuracy = 0
        
        # Calculate other metrics
        avg_sem = statistics.mean(sems) if sems else 0
        avg_items = int(statistics.mean(items_administered_list)) if items_administered_list else 0
        
        # Check SLO violations
        violations = []
        if avg_duration > self.SLO_AVG_SESSION_TIME_MS:
            violations.append(f"Average session duration {avg_duration:.0f}ms exceeds SLO of {self.SLO_AVG_SESSION_TIME_MS}ms")
        
        if p95_duration > self.SLO_P95_SESSION_TIME_MS:
            violations.append(f"P95 session duration {p95_duration:.0f}ms exceeds SLO of {self.SLO_P95_SESSION_TIME_MS}ms")
        
        if avg_sem > self.SLO_MAX_SEM:
            violations.append(f"Average SEM {avg_sem:.2f} exceeds SLO of {self.SLO_MAX_SEM}")
        
        if avg_accuracy < self.SLO_MIN_ACCURACY:
            violations.append(f"Average accuracy {avg_accuracy:.2%} below SLO of {self.SLO_MIN_ACCURACY:.2%}")
        
        targets_met = len(violations) == 0
        
        return BenchmarkMetrics(
            avg_session_duration_ms=avg_duration,
            min_session_duration_ms=min_duration,
            max_session_duration_ms=max_duration,
            p95_session_duration_ms=p95_duration,
            avg_accuracy=avg_accuracy,
            min_accuracy=min_accuracy,
            max_accuracy=max_accuracy,
            avg_theta_sem=avg_sem,
            avg_items_administered=avg_items,
            total_sessions=total_sessions,
            sessions_in_period=len([s for s in sessions if s.completed_at and s.completed_at >= cutoff_date]),
            period_days=days,
            targets_met=targets_met,
            violations=violations,
        )
    
    async def get_accuracy_by_subject(self, days: int = 30) -> Dict[str, Dict]:
        """
        Get accuracy metrics broken down by subject.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with accuracy metrics per subject
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = await self.session.execute(
            select(DiagnosticSession).where(
                DiagnosticSession.completed_at >= cutoff_date
            )
        )
        sessions = result.scalars().all()
        
        # Group by subject
        by_subject = {}
        for session in sessions:
            subject = session.subject_code
            if subject not in by_subject:
                by_subject[subject] = {
                    "sessions": [],
                    "accuracies": [],
                    "durations": [],
                }
            
            by_subject[subject]["sessions"].append(session)
            
            # Calculate accuracy
            if session.items_administered > 0:
                accuracy = session.items_correct / session.items_administered
                by_subject[subject]["accuracies"].append(accuracy)
            
            # Calculate duration
            if session.started_at and session.completed_at:
                duration = (session.completed_at - session.started_at).total_seconds() * 1000
                by_subject[subject]["durations"].append(duration)
        
        # Calculate per-subject metrics
        result_dict = {}
        for subject, data in by_subject.items():
            if data["accuracies"]:
                avg_accuracy = statistics.mean(data["accuracies"])
            else:
                avg_accuracy = 0
            
            if data["durations"]:
                avg_duration = statistics.mean(data["durations"])
            else:
                avg_duration = 0
            
            result_dict[subject] = {
                "sessions_count": len(data["sessions"]),
                "avg_accuracy": avg_accuracy,
                "min_accuracy": min(data["accuracies"]) if data["accuracies"] else 0,
                "max_accuracy": max(data["accuracies"]) if data["accuracies"] else 0,
                "avg_duration_ms": avg_duration,
            }
        
        return result_dict
    
    async def get_accuracy_by_grade(self, days: int = 30) -> Dict[int, Dict]:
        """
        Get accuracy metrics broken down by grade level.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with accuracy metrics per grade
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = await self.session.execute(
            select(DiagnosticSession).where(
                DiagnosticSession.completed_at >= cutoff_date
            )
        )
        sessions = result.scalars().all()
        
        # Group by grade
        by_grade = {}
        for session in sessions:
            grade = session.grade_level
            if grade not in by_grade:
                by_grade[grade] = {
                    "sessions": [],
                    "accuracies": [],
                    "theta_estimates": [],
                }
            
            by_grade[grade]["sessions"].append(session)
            
            # Calculate accuracy
            if session.items_administered > 0:
                accuracy = session.items_correct / session.items_administered
                by_grade[grade]["accuracies"].append(accuracy)
            
            # Track theta estimates
            by_grade[grade]["theta_estimates"].append(session.theta_estimate)
        
        # Calculate per-grade metrics
        result_dict = {}
        for grade, data in by_grade.items():
            if data["accuracies"]:
                avg_accuracy = statistics.mean(data["accuracies"])
            else:
                avg_accuracy = 0
            
            if data["theta_estimates"]:
                avg_theta = statistics.mean(data["theta_estimates"])
            else:
                avg_theta = 0
            
            result_dict[grade] = {
                "sessions_count": len(data["sessions"]),
                "avg_accuracy": avg_accuracy,
                "avg_theta": avg_theta,
                "theta_range": (min(data["theta_estimates"]), max(data["theta_estimates"])) if data["theta_estimates"] else (0, 0),
            }
        
        return result_dict
    
    async def generate_benchmark_report(self, days: int = 30) -> Dict:
        """
        Generate a comprehensive benchmark report.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with complete benchmark report
        """
        metrics = await self.get_benchmark_metrics(days)
        by_subject = await self.get_accuracy_by_subject(days)
        by_grade = await self.get_accuracy_by_grade(days)
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "period_days": days,
            "overall_metrics": {
                "total_sessions": metrics.total_sessions,
                "sessions_in_period": metrics.sessions_in_period,
                "avg_session_duration_ms": round(metrics.avg_session_duration_ms, 2),
                "p95_session_duration_ms": round(metrics.p95_session_duration_ms, 2),
                "avg_accuracy": round(metrics.avg_accuracy, 4),
                "avg_theta_sem": round(metrics.avg_theta_sem, 4),
                "avg_items_administered": metrics.avg_items_administered,
            },
            "slo_status": {
                "targets_met": metrics.targets_met,
                "violations": metrics.violations if metrics.violations else ["None - all targets met!"],
            },
            "slo_targets": {
                "max_avg_session_time_ms": self.SLO_AVG_SESSION_TIME_MS,
                "max_p95_session_time_ms": self.SLO_P95_SESSION_TIME_MS,
                "max_theta_sem": self.SLO_MAX_SEM,
                "min_accuracy": self.SLO_MIN_ACCURACY,
            },
            "by_subject": by_subject,
            "by_grade": by_grade,
        }
