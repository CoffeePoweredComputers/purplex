"""
Repository for ProgressSnapshot model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date, timedelta

from purplex.problems_app.models import ProgressSnapshot, Problem, ProblemSet, Course
from .base_repository import BaseRepository


class ProgressSnapshotRepository(BaseRepository):
    """
    Repository for all ProgressSnapshot-related database queries.
    
    This repository handles all data access for historical progress tracking
    and analytics over time.
    """
    
    model_class = ProgressSnapshot
    
    @classmethod
    def get_user_snapshots(cls, user: User, start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> List:
        """Get progress snapshots for a user within a date range."""
        queryset = ProgressSnapshot.objects.filter(user=user)
        
        if start_date:
            queryset = queryset.filter(snapshot_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(snapshot_date__lte=end_date)
        
        return list(queryset.select_related('problem', 'problem_set').order_by('-snapshot_date'))
    
    @classmethod
    def get_problem_snapshots(cls, problem: Problem, start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> List:
        """Get progress snapshots for a specific problem within a date range."""
        queryset = ProgressSnapshot.objects.filter(problem=problem)
        
        if start_date:
            queryset = queryset.filter(snapshot_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(snapshot_date__lte=end_date)
        
        return list(queryset.select_related('user', 'problem_set').order_by('-snapshot_date'))
    
    @classmethod
    def get_problem_set_snapshots(cls, problem_set: ProblemSet, 
                                 start_date: Optional[date] = None,
                                 end_date: Optional[date] = None) -> List:
        """Get progress snapshots for a specific problem set within a date range."""
        queryset = ProgressSnapshot.objects.filter(problem_set=problem_set)
        
        if start_date:
            queryset = queryset.filter(snapshot_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(snapshot_date__lte=end_date)
        
        return list(queryset.select_related('user', 'problem').order_by('-snapshot_date'))
    
    @classmethod
    def create_daily_snapshot(cls, user: User, problem: Optional[Problem] = None,
                             problem_set: Optional[ProblemSet] = None,
                             completion_percentage: int = 0,
                             problems_completed: int = 0,
                             average_score: float = 0.0,
                             time_spent_today: timedelta = None) -> ProgressSnapshot:
        """Create a daily progress snapshot."""
        snapshot_date = timezone.now().date()
        
        # Use get_or_create to avoid duplicate snapshots for the same day
        snapshot, created = ProgressSnapshot.objects.get_or_create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            snapshot_date=snapshot_date,
            defaults={
                'completion_percentage': completion_percentage,
                'problems_completed': problems_completed,
                'average_score': average_score,
                'time_spent_today': time_spent_today or timedelta(0)
            }
        )
        
        if not created:
            # Update existing snapshot with latest values
            snapshot.completion_percentage = completion_percentage
            snapshot.problems_completed = problems_completed
            snapshot.average_score = average_score
            if time_spent_today is not None:
                snapshot.time_spent_today = time_spent_today
            snapshot.save()
        
        return snapshot
    
    @classmethod
    def get_user_progress_trend(cls, user: User, days: int = 30,
                               problem: Optional[Problem] = None,
                               problem_set: Optional[ProblemSet] = None) -> List[Dict[str, Any]]:
        """Get user's progress trend over the specified number of days."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        filters = {
            'user': user,
            'snapshot_date__gte': start_date,
            'snapshot_date__lte': end_date
        }
        
        if problem:
            filters['problem'] = problem
        if problem_set:
            filters['problem_set'] = problem_set
        
        snapshots = ProgressSnapshot.objects.filter(**filters).order_by('snapshot_date')
        
        trend_data = []
        for snapshot in snapshots:
            trend_data.append({
                'date': snapshot.snapshot_date.isoformat(),
                'completion_percentage': snapshot.completion_percentage,
                'problems_completed': snapshot.problems_completed,
                'average_score': snapshot.average_score,
                'time_spent': snapshot.time_spent_today.total_seconds() / 3600  # Convert to hours
            })
        
        return trend_data
    
    @classmethod
    def get_daily_active_users(cls, target_date: date,
                              problem_set: Optional[ProblemSet] = None) -> int:
        """Get count of users who were active on a specific date."""
        filters = {
            'snapshot_date': target_date,
            'time_spent_today__gt': timedelta(0)
        }
        
        if problem_set:
            filters['problem_set'] = problem_set
        
        return ProgressSnapshot.objects.filter(**filters).values('user').distinct().count()
    
    @classmethod
    def get_activity_heatmap_data(cls, user: User, days: int = 90,
                                 problem_set: Optional[ProblemSet] = None) -> Dict[str, float]:
        """Get activity heatmap data for a user over specified days."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        filters = {
            'user': user,
            'snapshot_date__gte': start_date,
            'snapshot_date__lte': end_date
        }
        
        if problem_set:
            filters['problem_set'] = problem_set
        
        snapshots = ProgressSnapshot.objects.filter(**filters).values(
            'snapshot_date', 'time_spent_today'
        )
        
        heatmap_data = {}
        for snapshot in snapshots:
            date_str = snapshot['snapshot_date'].isoformat()
            hours_spent = snapshot['time_spent_today'].total_seconds() / 3600
            heatmap_data[date_str] = hours_spent
        
        return heatmap_data
    
    @classmethod
    def get_weekly_progress_summary(cls, user: User, problem_set: Optional[ProblemSet] = None) -> Dict[str, Any]:
        """Get a weekly summary of user progress."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        filters = {
            'user': user,
            'snapshot_date__gte': start_date,
            'snapshot_date__lte': end_date
        }
        
        if problem_set:
            filters['problem_set'] = problem_set
        
        snapshots = ProgressSnapshot.objects.filter(**filters)
        
        summary = snapshots.aggregate(
            total_time_spent=Sum('time_spent_today'),
            avg_completion=Avg('completion_percentage'),
            max_completion=Max('completion_percentage'),
            total_problems_completed=Max('problems_completed'),
            days_active=Count('snapshot_date', distinct=True)
        )
        
        # Convert time to hours
        total_seconds = summary['total_time_spent'].total_seconds() if summary['total_time_spent'] else 0
        summary['total_hours_spent'] = total_seconds / 3600
        
        return summary
    
    @classmethod
    def get_monthly_progress_summary(cls, user: User, month: int, year: int,
                                    problem_set: Optional[ProblemSet] = None) -> Dict[str, Any]:
        """Get a monthly summary of user progress."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        filters = {
            'user': user,
            'snapshot_date__gte': start_date,
            'snapshot_date__lte': end_date
        }
        
        if problem_set:
            filters['problem_set'] = problem_set
        
        snapshots = ProgressSnapshot.objects.filter(**filters)
        
        summary = snapshots.aggregate(
            total_time_spent=Sum('time_spent_today'),
            avg_completion=Avg('completion_percentage'),
            max_completion=Max('completion_percentage'),
            final_problems_completed=Max('problems_completed'),
            days_active=Count('snapshot_date', distinct=True)
        )
        
        # Calculate progress made during the month
        first_snapshot = snapshots.order_by('snapshot_date').first()
        last_snapshot = snapshots.order_by('-snapshot_date').first()
        
        if first_snapshot and last_snapshot:
            summary['progress_made'] = (
                last_snapshot.completion_percentage - first_snapshot.completion_percentage
            )
            summary['problems_completed_this_month'] = (
                last_snapshot.problems_completed - first_snapshot.problems_completed
            )
        else:
            summary['progress_made'] = 0
            summary['problems_completed_this_month'] = 0
        
        # Convert time to hours
        total_seconds = summary['total_time_spent'].total_seconds() if summary['total_time_spent'] else 0
        summary['total_hours_spent'] = total_seconds / 3600
        
        return summary
    
    @classmethod
    def get_class_progress_distribution(cls, problem_set: ProblemSet, 
                                       snapshot_date: Optional[date] = None) -> Dict[str, int]:
        """Get distribution of completion percentages for a class."""
        if not snapshot_date:
            snapshot_date = timezone.now().date()
        
        snapshots = ProgressSnapshot.objects.filter(
            problem_set=problem_set,
            snapshot_date=snapshot_date
        )
        
        # Create completion percentage ranges
        distribution = {
            '0-20%': 0,
            '21-40%': 0,
            '41-60%': 0,
            '61-80%': 0,
            '81-100%': 0
        }
        
        for snapshot in snapshots:
            completion = snapshot.completion_percentage
            if completion <= 20:
                distribution['0-20%'] += 1
            elif completion <= 40:
                distribution['21-40%'] += 1
            elif completion <= 60:
                distribution['41-60%'] += 1
            elif completion <= 80:
                distribution['61-80%'] += 1
            else:
                distribution['81-100%'] += 1
        
        return distribution
    
    @classmethod
    def cleanup_old_snapshots(cls, days_to_keep: int = 365) -> int:
        """Clean up old snapshot records to manage database size."""
        cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)
        deleted, _ = ProgressSnapshot.objects.filter(
            snapshot_date__lt=cutoff_date
        ).delete()
        return deleted
    
    @classmethod
    def get_streak_data(cls, user: User, problem_set: Optional[ProblemSet] = None) -> Dict[str, Any]:
        """Calculate user's activity streak data."""
        filters = {'user': user}
        if problem_set:
            filters['problem_set'] = problem_set
        
        snapshots = ProgressSnapshot.objects.filter(**filters).filter(
            time_spent_today__gt=timedelta(0)
        ).order_by('-snapshot_date').values_list('snapshot_date', flat=True)
        
        if not snapshots:
            return {'current_streak': 0, 'longest_streak': 0}
        
        # Calculate current streak
        current_streak = 0
        today = timezone.now().date()
        current_date = today
        
        for snapshot_date in snapshots:
            if snapshot_date == current_date or snapshot_date == current_date - timedelta(days=1):
                current_streak += 1
                current_date = snapshot_date - timedelta(days=1)
            else:
                break
        
        # Calculate longest streak
        longest_streak = 0
        temp_streak = 0
        prev_date = None
        
        for snapshot_date in reversed(list(snapshots)):
            if prev_date is None or snapshot_date == prev_date + timedelta(days=1):
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
            prev_date = snapshot_date
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'total_active_days': len(snapshots)
        }
    
    @classmethod
    def get_comparative_progress(cls, user: User, problem_set: ProblemSet,
                                comparison_date: date) -> Dict[str, Any]:
        """Compare user's progress to class average on a specific date."""
        user_snapshot = ProgressSnapshot.objects.filter(
            user=user,
            problem_set=problem_set,
            snapshot_date=comparison_date
        ).first()
        
        class_stats = ProgressSnapshot.objects.filter(
            problem_set=problem_set,
            snapshot_date=comparison_date
        ).aggregate(
            avg_completion=Avg('completion_percentage'),
            avg_score=Avg('average_score'),
            total_students=Count('user', distinct=True)
        )
        
        if not user_snapshot:
            return {
                'user_completion': 0,
                'user_score': 0,
                'class_avg_completion': class_stats['avg_completion'] or 0,
                'class_avg_score': class_stats['avg_score'] or 0,
                'total_students': class_stats['total_students'] or 0,
                'user_percentile': None
            }
        
        # Calculate user's percentile
        users_below = ProgressSnapshot.objects.filter(
            problem_set=problem_set,
            snapshot_date=comparison_date,
            completion_percentage__lt=user_snapshot.completion_percentage
        ).count()
        
        total_students = class_stats['total_students'] or 1
        percentile = (users_below / total_students) * 100 if total_students > 0 else 0
        
        return {
            'user_completion': user_snapshot.completion_percentage,
            'user_score': user_snapshot.average_score,
            'class_avg_completion': class_stats['avg_completion'] or 0,
            'class_avg_score': class_stats['avg_score'] or 0,
            'total_students': total_students,
            'user_percentile': round(percentile, 1)
        }