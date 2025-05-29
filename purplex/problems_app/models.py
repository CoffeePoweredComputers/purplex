from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Avg, Min, Max
from django.utils import timezone
from datetime import timedelta
import json

class ProblemCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField()
    icon = models.ImageField(upload_to='category_icons/', null=True, blank=True)
    color = models.CharField(max_length=7, default='#6366f1', help_text='Hex color code')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Problem Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Problem(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    PROBLEM_TYPE_CHOICES = [
        ('eipl', 'Explain in Plain Language (EiPL)'),
        ('function_redefinition', 'Function Redefinition'),
    ]
    
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    problem_type = models.CharField(max_length=30, choices=PROBLEM_TYPE_CHOICES, default='eipl')
    title = models.CharField(max_length=200)
    description = models.TextField(help_text='Problem description in markdown format')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    categories = models.ManyToManyField(ProblemCategory, related_name='problems', blank=True)
    function_name = models.CharField(max_length=50, help_text='Name of the function students implement')
    function_signature = models.TextField(help_text='Function signature with parameter names and types')
    reference_solution = models.TextField(help_text='Reference implementation')
    hints = models.TextField(blank=True, help_text='Optional hints for students')
    time_limit = models.PositiveIntegerField(default=30, help_text='Time limit in seconds')
    memory_limit = models.PositiveIntegerField(default=128, help_text='Memory limit in MB')
    estimated_time = models.PositiveIntegerField(default=15, help_text='Estimated solve time in minutes')
    tags = models.JSONField(default=list, blank=True, help_text='Array of tag strings')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    
    # Completion configuration
    completion_threshold = models.IntegerField(default=80, help_text='Minimum score required for completion')
    completion_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON object defining completion requirements"
    )
    
    # Educational metadata
    max_attempts = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum attempts allowed (null = unlimited)"
    )
    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='unlocks',
        blank=True
    )

    class Meta:
        ordering = ['difficulty', 'title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def clean(self):
        if self.function_name and not self.function_name.isidentifier():
            raise ValidationError('Function name must be a valid Python identifier')
        
        if self.tags and not isinstance(self.tags, list):
            raise ValidationError('Tags must be a list of strings')

    @property
    def test_cases_count(self):
        return self.test_cases.count()

    @property
    def visible_test_cases_count(self):
        return self.test_cases.filter(is_hidden=False).count()

    def __str__(self):
        return f"{self.title} ({self.difficulty})"

class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    inputs = models.JSONField(help_text='Array of input arguments')
    expected_output = models.JSONField(help_text='Expected output value')
    description = models.CharField(max_length=200, blank=True, help_text='Optional description for this test case')
    is_hidden = models.BooleanField(default=False, help_text='Hidden test cases are not shown to students')
    is_sample = models.BooleanField(default=False, help_text='Sample test cases are shown in problem description')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['problem', 'order']

    def clean(self):
        if not isinstance(self.inputs, list):
            raise ValidationError('Inputs must be a list of arguments')
        
        try:
            json.dumps(self.expected_output)
        except (TypeError, ValueError):
            raise ValidationError('Expected output must be JSON serializable')

    def __str__(self):
        inputs_str = ', '.join(str(arg) for arg in self.inputs)
        return f"{self.problem.title} - Test {self.order}: f({inputs_str}) -> {self.expected_output}"

class ProblemSet(models.Model):
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    problems = models.ManyToManyField(Problem, through='ProblemSetMembership', related_name='problem_sets', blank=True)
    icon = models.ImageField(upload_to='problem_set_icons/', null=True, blank=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def problems_count(self):
        return self.problems.count()

    def __str__(self):
        return self.title

class ProblemSetMembership(models.Model):
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['problem_set', 'problem']

    def __str__(self):
        return f"{self.problem_set.title} - {self.problem.title}"


class UserProgress(models.Model):
    """Tracks user progress on individual problems within a specific problem set context"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, null=True)
    problem_version = models.PositiveIntegerField(default=1)
    
    # Status with more granular states
    status = models.CharField(max_length=20, choices=[
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),  # Started but < 50%
        ('struggling', 'Struggling'),     # Multiple attempts, low scores
        ('advancing', 'Advancing'),       # 50-79% score
        ('completed', 'Completed'),       # Met completion criteria
        ('mastered', 'Mastered')         # Perfect score or multiple completions
    ], default='not_started')
    
    # Scoring and attempts
    best_score = models.IntegerField(default=0)
    average_score = models.FloatField(default=0)
    attempts = models.IntegerField(default=0)
    successful_attempts = models.IntegerField(default=0)
    
    # Timing
    first_attempt = models.DateTimeField(null=True, blank=True)
    last_attempt = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_time_spent = models.DurationField(default=timedelta(0))
    
    # Learning metrics
    hints_used = models.IntegerField(default=0)
    consecutive_successes = models.IntegerField(default=0)
    days_to_complete = models.IntegerField(null=True, blank=True)
    
    # Cached aggregates for performance
    is_completed = models.BooleanField(default=False, db_index=True)
    completion_percentage = models.IntegerField(default=0, db_index=True)
    
    class Meta:
        unique_together = ['user', 'problem', 'problem_set']
        indexes = [
            models.Index(fields=['user', 'problem_set', 'is_completed']),
            models.Index(fields=['user', 'problem_set', 'status']),
            models.Index(fields=['problem', 'problem_set', 'status']),
            models.Index(fields=['user', 'problem_set', '-last_attempt']),  # Recent activity
        ]
    
    def update_from_submission(self, submission, time_spent=None):
        """Update progress based on new submission with intelligent status calculation"""
        self.attempts += 1
        self.last_attempt = submission.time
        
        if not self.first_attempt:
            self.first_attempt = submission.time
        
        # Update scores
        if submission.score > self.best_score:
            self.best_score = submission.score
        
        # Update average score
        self.average_score = (
            (self.average_score * (self.attempts - 1) + submission.score) / self.attempts
        )
        
        # Update time tracking
        if time_spent:
            self.total_time_spent += time_spent
        
        # Intelligent status calculation
        self._update_status(submission)
        
        # Update completion
        if self._check_completion(submission):
            if not self.completed_at:
                self.completed_at = submission.time
                self.days_to_complete = (submission.time - self.first_attempt).days
            self.is_completed = True
            self.consecutive_successes += 1
        else:
            self.consecutive_successes = 0
        
        self.completion_percentage = self._calculate_completion_percentage()
        self.save()
    
    def _update_status(self, submission):
        """Intelligent status determination based on performance patterns"""
        completion_threshold = self.problem.completion_threshold or 80
        
        if self.best_score >= 100:
            self.status = 'mastered'
        elif self.best_score >= completion_threshold:
            self.status = 'completed'
        elif self.best_score >= 50:
            self.status = 'advancing'
        elif self.attempts > 5 and self.average_score < 30:
            self.status = 'struggling'
        else:
            self.status = 'in_progress'
    
    def _check_completion(self, submission):
        """Flexible completion checking supporting multiple criteria"""
        completion_criteria = self.problem.completion_criteria or {}
        
        # Default to threshold-based completion
        if not completion_criteria:
            return submission.score >= (self.problem.completion_threshold or 80)
        
        if 'min_score' in completion_criteria:
            if submission.score < completion_criteria['min_score']:
                return False
        
        if 'required_test_cases' in completion_criteria:
            # Check specific test cases passed
            passed_tests = set(getattr(submission, 'passed_test_ids', []) or [])
            required = set(completion_criteria['required_test_cases'])
            if not required.issubset(passed_tests):
                return False
        
        if 'time_limit' in completion_criteria:
            execution_time = getattr(submission, 'execution_time', None)
            if execution_time and execution_time > completion_criteria['time_limit']:
                return False
        
        return True
    
    def _calculate_completion_percentage(self):
        """Calculate nuanced completion percentage"""
        if self.status == 'mastered':
            return 100
        elif self.status == 'completed':
            return 90 + (self.best_score - 80) // 2  # 90-100%
        else:
            # Scale 0-89% based on best score and attempts
            base = min(self.best_score, 89)
            # Penalty for excessive attempts indicating struggle
            attempt_penalty = max(0, (self.attempts - 10) * 2)
            return max(0, base - attempt_penalty)
    
    def __str__(self):
        return f"{self.user.username} - {self.problem_set.title} - {self.problem.title} ({self.status})"


class UserProblemSetProgress(models.Model):
    """Cached aggregate progress for problem sets"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    
    total_problems = models.IntegerField(default=0)
    completed_problems = models.IntegerField(default=0)
    partially_complete_problems = models.IntegerField(default=0)
    average_score = models.FloatField(default=0)
    
    first_attempt = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    completion_percentage = models.IntegerField(default=0, db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        unique_together = ['user', 'problem_set']
        indexes = [
            models.Index(fields=['user', '-last_activity']),
            models.Index(fields=['problem_set', '-completion_percentage']),
        ]
    
    @classmethod
    def update_from_progress(cls, user_progress):
        """Update problem set progress when individual problem progress changes"""
        # Only update the specific problem set that the progress belongs to
        set_progress, created = cls.objects.get_or_create(
            user=user_progress.user,
            problem_set=user_progress.problem_set
        )
        
        # Recalculate aggregates for this specific problem set
        problem_progresses = UserProgress.objects.filter(
            user=user_progress.user,
            problem_set=user_progress.problem_set
        )
        
        stats = problem_progresses.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(is_completed=True)),
            partially_complete=Count('id', filter=~Q(status='not_started')),
            avg_score=Avg('best_score'),
            first_attempt=Min('first_attempt'),
            last_activity=Max('last_attempt')
        )
        
        set_progress.total_problems = user_progress.problem_set.problems.count()
        set_progress.completed_problems = stats['completed'] or 0
        set_progress.partially_complete_problems = stats['partially_complete'] or 0
        set_progress.average_score = stats['avg_score'] or 0
        set_progress.first_attempt = stats['first_attempt']
        set_progress.last_activity = stats['last_activity']
        
        set_progress.completion_percentage = int(
            (set_progress.completed_problems / set_progress.total_problems * 100)
            if set_progress.total_problems > 0 else 0
        )
        set_progress.is_completed = (
            set_progress.completed_problems == set_progress.total_problems
        )
        
        if set_progress.is_completed and not set_progress.completed_at:
            set_progress.completed_at = timezone.now()
        
        set_progress.save()
    
    def __str__(self):
        return f"{self.user.username} - {self.problem_set.title} ({self.completion_percentage}%)"


class ProgressSnapshot(models.Model):
    """Historical snapshots for tracking progress over time"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, null=True, blank=True)
    
    snapshot_date = models.DateField(auto_now_add=True)
    completion_percentage = models.IntegerField()
    problems_completed = models.IntegerField()
    average_score = models.FloatField()
    time_spent_today = models.DurationField(default=timedelta(0))
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-snapshot_date']),
            models.Index(fields=['user', 'problem', '-snapshot_date']),
        ]
        unique_together = ['user', 'problem', 'problem_set', 'snapshot_date']
    
    def __str__(self):
        target = self.problem.title if self.problem else self.problem_set.title
        return f"{self.user.username} - {target} - {self.snapshot_date}"