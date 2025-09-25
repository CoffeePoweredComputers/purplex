"""
Repository for UserProblemSetProgress model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta

from purplex.problems_app.models import UserProblemSetProgress, ProblemSet, Course, UserProgress
from .base_repository import BaseRepository


class UserProblemSetProgressRepository(BaseRepository):
    """
    Repository for all UserProblemSetProgress-related database queries.
    
    This repository handles all data access for aggregate progress tracking
    at the problem set level with course context support.
    """
    
    model_class = UserProblemSetProgress
    
    @classmethod
    def get_user_problem_set_progress(cls, user: User, problem_set: ProblemSet,
                                     course: Optional[Course] = None) -> Optional[UserProblemSetProgress]:
        """Get progress for a specific user-problem set combination."""
        return UserProblemSetProgress.objects.filter(
            user=user,
            problem_set=problem_set,
            course=course
        ).first()
    
    @classmethod
    def get_or_create_progress(cls, user: User, problem_set: ProblemSet,
                              course: Optional[Course] = None) -> tuple:
        """Get or create progress record for a user-problem set combination."""
        return UserProblemSetProgress.objects.get_or_create(
            user=user,
            problem_set=problem_set,
            course=course,
            defaults={
                'total_problems': problem_set.problems.count(),
                'completed_problems': 0,
                'in_progress_problems': 0,
                'average_score': 0.0,
                'completion_percentage': 0,
                'is_completed': False
            }
        )
    
    @classmethod
    def get_user_all_progress(cls, user: User, course: Optional[Course] = None) -> List:
        """Get all problem set progress for a user."""
        filters = {'user': user}
        if course:
            filters['course'] = course
        
        return list(UserProblemSetProgress.objects.filter(**filters).select_related(
            'problem_set', 'course'
        ).order_by('-last_activity'))
    
    @classmethod
    def get_completed_problem_sets(cls, user: User, 
                                  course: Optional[Course] = None) -> List:
        """Get all completed problem sets for a user."""
        filters = {'user': user, 'is_completed': True}
        if course:
            filters['course'] = course
        
        return list(UserProblemSetProgress.objects.filter(**filters).select_related(
            'problem_set', 'course'
        ).order_by('-completed_at'))
    
    @classmethod
    def get_in_progress_problem_sets(cls, user: User,
                                    course: Optional[Course] = None) -> List:
        """Get all in-progress problem sets for a user."""
        filters = {
            'user': user,
            'in_progress_problems__gt': 0,
            'is_completed': False
        }
        if course:
            filters['course'] = course
        
        return list(UserProblemSetProgress.objects.filter(**filters).select_related(
            'problem_set', 'course'
        ).order_by('-last_activity'))
    
    @classmethod
    def get_course_progress_summary(cls, user: User, course: Course) -> Dict[str, Any]:
        """Get comprehensive progress summary for a user in a course."""
        progress_records = UserProblemSetProgress.objects.filter(
            user=user,
            course=course
        )
        
        summary = progress_records.aggregate(
            total_problem_sets=Count('id'),
            completed_problem_sets=Count('id', filter=Q(is_completed=True)),
            total_problems=Sum('total_problems'),
            completed_problems=Sum('completed_problems'),
            in_progress_problems=Sum('in_progress_problems'),
            average_score=Avg('average_score'),
            first_activity=Min('first_attempt'),
            last_activity=Max('last_activity')
        )
        
        # Calculate overall completion rate
        total_problems = summary['total_problems'] or 0
        completed_problems = summary['completed_problems'] or 0
        summary['overall_completion_rate'] = (
            (completed_problems / total_problems * 100) if total_problems > 0 else 0
        )
        
        # Calculate problem set completion rate
        total_sets = summary['total_problem_sets'] or 0
        completed_sets = summary['completed_problem_sets'] or 0
        summary['problem_set_completion_rate'] = (
            (completed_sets / total_sets * 100) if total_sets > 0 else 0
        )
        
        return summary
    
    @classmethod
    def get_problem_set_leaderboard(cls, problem_set: ProblemSet,
                                   course: Optional[Course] = None,
                                   limit: int = 10) -> List:
        """Get top performers for a problem set."""
        filters = {'problem_set': problem_set}
        if course:
            filters['course'] = course
        
        return list(UserProblemSetProgress.objects.filter(**filters).select_related(
            'user'
        ).order_by(
            '-completion_percentage', 
            '-average_score', 
            'completed_at'
        )[:limit])
    
    @classmethod
    def get_problem_set_statistics(cls, problem_set: ProblemSet,
                                  course: Optional[Course] = None) -> Dict[str, Any]:
        """Get statistics for a problem set across all users."""
        filters = {'problem_set': problem_set}
        if course:
            filters['course'] = course
        
        stats = UserProblemSetProgress.objects.filter(**filters).aggregate(
            total_users=Count('user', distinct=True),
            completed_users=Count('user', filter=Q(is_completed=True)),
            average_completion=Avg('completion_percentage'),
            average_score=Avg('average_score'),
            min_completion_time=Min('completed_at'),
            max_completion_time=Max('completed_at')
        )
        
        # Calculate completion rate
        total = stats['total_users'] or 0
        completed = stats['completed_users'] or 0
        stats['completion_rate'] = (completed / total * 100) if total > 0 else 0
        
        return stats
    
    @classmethod
    def update_from_user_progress(cls, user_progress: UserProgress) -> UserProblemSetProgress:
        """Update problem set progress based on individual problem progress."""
        # This calls the class method from the model
        UserProblemSetProgress.update_from_progress(user_progress)
        
        # Return the updated progress record
        return cls.get_user_problem_set_progress(
            user_progress.user,
            user_progress.problem_set,
            user_progress.course
        )
    
    @classmethod
    def recalculate_progress(cls, user: User, problem_set: ProblemSet,
                            course: Optional[Course] = None) -> UserProblemSetProgress:
        """Recalculate problem set progress from individual problem progress."""
        set_progress, created = cls.get_or_create_progress(user, problem_set, course)
        
        # Get all individual problem progress for this set
        individual_progress = UserProgress.objects.filter(
            user=user,
            problem_set=problem_set,
            course=course
        )
        
        if individual_progress.exists():
            stats = individual_progress.aggregate(
                completed=Count('id', filter=Q(is_completed=True)),
                in_progress=Count('id', filter=Q(status='in_progress')),
                avg_score=Avg('best_score'),
                first_attempt=Min('first_attempt'),
                last_activity=Max('last_attempt')
            )
            
            set_progress.total_problems = problem_set.problems.count()
            set_progress.completed_problems = stats['completed'] or 0
            set_progress.in_progress_problems = stats['in_progress'] or 0
            set_progress.average_score = stats['avg_score'] or 0
            set_progress.first_attempt = stats['first_attempt']
            set_progress.last_activity = stats['last_activity']
            
            # Calculate completion percentage
            if set_progress.total_problems > 0:
                set_progress.completion_percentage = int(
                    (set_progress.completed_problems / set_progress.total_problems * 100)
                )
            else:
                set_progress.completion_percentage = 0
            
            # Update completion status
            set_progress.is_completed = (
                set_progress.completed_problems == set_progress.total_problems
            )
            
            if set_progress.is_completed and not set_progress.completed_at:
                set_progress.completed_at = timezone.now()
            
            set_progress.save()
        
        return set_progress
    
    @classmethod
    def bulk_recalculate_progress(cls, problem_set: ProblemSet,
                                 course: Optional[Course] = None) -> int:
        """Recalculate progress for all users in a problem set."""
        filters = {'problem_set': problem_set}
        if course:
            filters['course'] = course
        
        # Get all users who have progress in this problem set
        users_with_progress = UserProgress.objects.filter(**filters).values_list(
            'user', flat=True
        ).distinct()
        
        updated_count = 0
        for user_id in users_with_progress:
            user = User.objects.get(id=user_id)
            cls.recalculate_progress(user, problem_set, course)
            updated_count += 1
        
        return updated_count
    
    @classmethod
    def get_recent_completions(cls, problem_set: ProblemSet,
                              days: int = 30,
                              course: Optional[Course] = None) -> List:
        """Get recent completions for a problem set."""
        since_date = timezone.now() - timedelta(days=days)
        filters = {
            'problem_set': problem_set,
            'is_completed': True,
            'completed_at__gte': since_date
        }
        if course:
            filters['course'] = course
        
        return list(UserProblemSetProgress.objects.filter(**filters).select_related(
            'user'
        ).order_by('-completed_at'))
    
    @classmethod
    def get_struggling_users(cls, problem_set: ProblemSet,
                            max_completion_rate: int = 30,
                            min_days_active: int = 7,
                            course: Optional[Course] = None) -> List:
        """Get users who are struggling with a problem set."""
        since_date = timezone.now() - timedelta(days=min_days_active)
        filters = {
            'problem_set': problem_set,
            'completion_percentage__lte': max_completion_rate,
            'first_attempt__lte': since_date,
            'is_completed': False
        }
        if course:
            filters['course'] = course
        
        return list(UserProblemSetProgress.objects.filter(**filters).select_related(
            'user'
        ).order_by('completion_percentage', 'first_attempt'))
    
    @classmethod
    def get_progress_distribution(cls, problem_set: ProblemSet,
                                 course: Optional[Course] = None) -> Dict[str, int]:
        """Get distribution of completion percentages for a problem set."""
        filters = {'problem_set': problem_set}
        if course:
            filters['course'] = course
        
        progress_records = UserProblemSetProgress.objects.filter(**filters)
        
        distribution = {
            '0-20%': 0,
            '21-40%': 0,
            '41-60%': 0,
            '61-80%': 0,
            '81-99%': 0,
            '100%': 0
        }
        
        for progress in progress_records:
            completion = progress.completion_percentage
            if completion == 100:
                distribution['100%'] += 1
            elif completion > 80:
                distribution['81-99%'] += 1
            elif completion > 60:
                distribution['61-80%'] += 1
            elif completion > 40:
                distribution['41-60%'] += 1
            elif completion > 20:
                distribution['21-40%'] += 1
            else:
                distribution['0-20%'] += 1
        
        return distribution
    
    @classmethod
    def get_completion_time_analysis(cls, problem_set: ProblemSet,
                                    course: Optional[Course] = None) -> Dict[str, Any]:
        """Analyze completion times for a problem set."""
        filters = {
            'problem_set': problem_set,
            'is_completed': True,
            'first_attempt__isnull': False,
            'completed_at__isnull': False
        }
        if course:
            filters['course'] = course
        
        completed_progress = UserProblemSetProgress.objects.filter(**filters)
        
        if not completed_progress.exists():
            return {
                'average_days': None,
                'median_days': None,
                'min_days': None,
                'max_days': None,
                'total_completed': 0
            }
        
        completion_times = []
        for progress in completed_progress:
            if progress.first_attempt and progress.completed_at:
                delta = progress.completed_at - progress.first_attempt
                completion_times.append(delta.days)
        
        if completion_times:
            completion_times.sort()
            n = len(completion_times)
            
            return {
                'average_days': sum(completion_times) / n,
                'median_days': completion_times[n // 2] if n % 2 == 1 else 
                              (completion_times[n // 2 - 1] + completion_times[n // 2]) / 2,
                'min_days': min(completion_times),
                'max_days': max(completion_times),
                'total_completed': n
            }
        
        return {
            'average_days': None,
            'median_days': None,
            'min_days': None,
            'max_days': None,
            'total_completed': 0
        }
    
    @classmethod
    def get_user_ranking(cls, user: User, problem_set: ProblemSet,
                        course: Optional[Course] = None) -> Dict[str, Any]:
        """Get a user's ranking within a problem set."""
        filters = {'problem_set': problem_set}
        if course:
            filters['course'] = course
        
        user_progress = cls.get_user_problem_set_progress(user, problem_set, course)
        if not user_progress:
            return {'rank': None, 'total_users': 0, 'percentile': None}
        
        # Count users with better completion percentage
        better_users = UserProblemSetProgress.objects.filter(
            **filters,
            completion_percentage__gt=user_progress.completion_percentage
        ).count()
        
        # Count users with same completion percentage but better average score
        same_completion_better_score = UserProblemSetProgress.objects.filter(
            **filters,
            completion_percentage=user_progress.completion_percentage,
            average_score__gt=user_progress.average_score
        ).count()
        
        total_users = UserProblemSetProgress.objects.filter(**filters).count()
        rank = better_users + same_completion_better_score + 1
        
        percentile = ((total_users - rank + 1) / total_users * 100) if total_users > 0 else 0
        
        return {
            'rank': rank,
            'total_users': total_users,
            'percentile': round(percentile, 1)
        }
    
    @classmethod
    def cleanup_stale_progress(cls, days_inactive: int = 90) -> int:
        """Clean up progress records for users who have been inactive."""
        cutoff_date = timezone.now() - timedelta(days=days_inactive)
        
        deleted, _ = UserProblemSetProgress.objects.filter(
            last_activity__lt=cutoff_date,
            is_completed=False,
            completion_percentage=0
        ).delete()
        
        return deleted