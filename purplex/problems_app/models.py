from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Avg, Min, Max
from django.utils import timezone
from datetime import timedelta
import json

# Constants
DEFAULT_COMPLETION_THRESHOLD = 100

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
    
    # NOTE: Problem types are extensible via the activity type system.
    # Each type has a handler in problems_app/handlers/ and frontend components
    # in client/src/components/activities/
    PROBLEM_TYPE_CHOICES = [
        ('eipl', 'Explain in Plain Language (EiPL)'),
        ('mcq', 'Multiple Choice Question'),
    ]
    
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    problem_type = models.CharField(max_length=30, choices=PROBLEM_TYPE_CHOICES, default='eipl')
    title = models.CharField(max_length=200)
    # NOTE: Description field is deprecated - students never see it, only the code
    description = models.TextField(blank=True, null=True, default='', help_text='DEPRECATED - Not shown to students')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    categories = models.ManyToManyField(ProblemCategory, related_name='problems', blank=True)
    # NOTE: function_name is auto-extracted from reference_solution, function_signature is required for test case parsing
    function_name = models.CharField(max_length=50, blank=True, default='', help_text='Auto-extracted from reference solution')
    function_signature = models.TextField(help_text='Function signature with type hints for test case parsing')
    reference_solution = models.TextField(help_text='Reference implementation')
    memory_limit = models.PositiveIntegerField(default=128, help_text='Memory limit in MB')
    tags = models.JSONField(default=list, blank=True, help_text='Array of tag strings')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    
    # Completion configuration
    completion_threshold = models.IntegerField(default=100, help_text='Minimum score required for completion')
    completion_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON object defining completion requirements"
    )
    
    # Prompt segmentation for EiPL problems
    segmentation_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete segmentation configuration including threshold, examples, and settings"
    )

    # MCQ-specific configuration
    mcq_options = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of {id, text, is_correct} objects for MCQ problems"
    )

    # Direct grading configuration fields (for GRADING_PIPELINE.md implementation)
    segmentation_threshold = models.PositiveIntegerField(
        default=2,
        help_text="Maximum number of segments for high-level comprehension in EiPL problems"
    )
    requires_highlevel_comprehension = models.BooleanField(
        default=True,
        help_text="Whether EiPL problems require high-level comprehension for full credit"
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
        # Only validate function_name if it's provided (it's now auto-extracted)
        if self.function_name and self.function_name.strip() and not self.function_name.isidentifier():
            raise ValidationError('Function name must be a valid Python identifier')

        if self.tags and not isinstance(self.tags, list):
            raise ValidationError('Tags must be a list of strings')

    @property
    def test_cases_count(self):
        return self.test_cases.count()

    @property
    def visible_test_cases_count(self):
        return self.test_cases.filter(is_hidden=False).count()

    # Segmentation helper methods
    @property
    def segmentation_enabled(self):
        """Check if segmentation is enabled for this EiPL problem"""
        # Check both new field and legacy JSON config
        return (self.problem_type == 'eipl' and
                self.requires_highlevel_comprehension and
                self.segmentation_config.get('enabled', True))

    @property
    def get_segmentation_threshold(self):
        """Get the segmentation threshold for this problem"""
        # Use new field if set, otherwise fall back to JSON config
        if self.segmentation_threshold and self.segmentation_threshold > 0:
            return self.segmentation_threshold
        return self.segmentation_config.get('threshold', 2)

    def get_segmentation_examples(self):
        """Get segmentation examples for this problem"""
        return self.segmentation_config.get('examples', {})

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
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def problems_count(self):
        return self.problems.count()
    
    def increment_version(self):
        """Call when problem membership changes"""
        self.version = models.F('version') + 1
        self.save(update_fields=['version'])

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
    """Tracks user progress on individual problems within a specific problem set and course context"""
    # CRITICAL: Use SET_NULL for user to preserve analytics data even if account deleted
    # Use PROTECT for problem/set/course to prevent deletion of content with progress data
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.PROTECT, null=True)
    course = models.ForeignKey('Course', on_delete=models.PROTECT, null=True, blank=True)
    problem_version = models.PositiveIntegerField(default=1)
    
    # Simplified status: just completed or not completed
    status = models.CharField(max_length=20, choices=[
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),       # Met completion criteria
    ], default='not_started')

    # Grade per GRADING_PIPELINE.md specification
    grade = models.CharField(
        max_length=20,
        choices=[
            ('incomplete', 'Incomplete'),
            ('partial', 'Partially Complete'),
            ('complete', 'Complete')
        ],
        default='incomplete',
        help_text="Grade based on correctness and high-levelness dimensions",
        db_index=True
    )
    
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
        unique_together = ['user', 'problem', 'problem_set', 'course']
        indexes = [
            models.Index(fields=['user', 'problem_set', 'is_completed']),
            models.Index(fields=['user', 'problem_set', 'status']),
            models.Index(fields=['problem', 'problem_set', 'status']),
            models.Index(fields=['user', 'problem_set', '-last_attempt']),  # Recent activity
            models.Index(fields=['user', 'course', 'problem_set', 'is_completed']),
        ]
    def __str__(self):
        return f"{self.user.username} - {self.problem_set.title} - {self.problem.title} ({self.status})"


class UserProblemSetProgress(models.Model):
    """Cached aggregate progress for problem sets with course context"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, null=True, blank=True)
    
    total_problems = models.IntegerField(default=0)
    completed_problems = models.IntegerField(default=0)
    in_progress_problems = models.IntegerField(default=0)
    average_score = models.FloatField(default=0)
    
    first_attempt = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    completion_percentage = models.IntegerField(default=0, db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        unique_together = ['user', 'problem_set', 'course']
        indexes = [
            models.Index(fields=['user', 'course', '-last_activity']),
            models.Index(fields=['problem_set', 'course', '-completion_percentage']),
        ]
    
    @classmethod
    def update_from_progress(cls, user_progress):
        """
        Update problem set progress when individual problem progress changes.

        LOCK-FREE: Uses atomic update_or_create() to avoid blocking greenlets.
        Independent grading operations don't need coordination - each recalculates
        from source of truth (UserProgress table).
        """
        # Recalculate aggregates from UserProgress (source of truth)
        stats = UserProgress.objects.filter(
            user=user_progress.user,
            problem_set=user_progress.problem_set,
            course=user_progress.course
        ).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(is_completed=True)),
            in_progress=Count('id', filter=Q(status='in_progress')),
            avg_score=Avg('best_score'),
            first_attempt=Min('first_attempt'),
            last_activity=Max('last_attempt')
        )

        # Calculate completion metrics
        total_problems = user_progress.problem_set.problems.count()
        completed = stats['completed'] or 0
        completion_pct = int((completed / total_problems * 100) if total_problems > 0 else 0)
        is_completed = (completed == total_problems) if total_problems > 0 else False

        # Atomic update_or_create with all fields in defaults
        # This is a single atomic operation - no locks needed
        set_progress, created = cls.objects.update_or_create(
            user=user_progress.user,
            problem_set=user_progress.problem_set,
            course=user_progress.course,
            defaults={
                'total_problems': total_problems,
                'completed_problems': completed,
                'in_progress_problems': stats['in_progress'] or 0,
                'average_score': stats['avg_score'] or 0,
                'first_attempt': stats['first_attempt'],
                'last_activity': stats['last_activity'],
                'completion_percentage': completion_pct,
                'is_completed': is_completed,
                # Preserve existing completed_at value - will be set below if needed
                'completed_at': models.F('completed_at')
            }
        )

        # If just became completed and completed_at wasn't set, update it
        if is_completed and not created and not set_progress.completed_at:
            set_progress.completed_at = timezone.now()
            set_progress.save(update_fields=['completed_at'])
    
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


class Course(models.Model):
    """Course model for organizing problem sets into courses"""
    course_id = models.CharField(max_length=50, unique=True, help_text="User-defined course ID (e.g., CS101-FALL2024)")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # CRITICAL: Changed from CASCADE to PROTECT to prevent accidental data loss
    # Deleting an instructor should not cascade-delete all their courses and student data
    instructor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='instructed_courses')
    problem_sets = models.ManyToManyField(ProblemSet, through='CourseProblemSet', related_name='courses')
    is_active = models.BooleanField(default=True)
    enrollment_open = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course_id']),
            models.Index(fields=['instructor', 'is_active']),
            models.Index(fields=['is_deleted', 'is_active']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.course_id)
        super().save(*args, **kwargs)
    
    def soft_delete(self):
        """Soft delete the course"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.is_active = False
        self.enrollment_open = False
        self.save()
    
    def __str__(self):
        return f"{self.course_id} - {self.name}"


class CourseProblemSet(models.Model):
    """Through model for Course-ProblemSet relationship with ordering"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    is_required = models.BooleanField(default=True)
    # Track the version of problem set membership when added
    problem_set_version = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['order']
        unique_together = ['course', 'problem_set']
    
    def __str__(self):
        return f"{self.course.course_id} - {self.problem_set.title} (Order: {self.order})"


class CourseEnrollment(models.Model):
    """Track student enrollment in courses"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['course', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} enrolled in {self.course.course_id}"


class ProblemHint(models.Model):
    """Hint configuration for problems to support research on educational interventions"""
    HINT_TYPE_CHOICES = [
        ('variable_fade', 'Variable Fade'),
        ('subgoal_highlight', 'Subgoal Highlighting'),
        ('suggested_trace', 'Suggested Trace')
    ]
    
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='hints')
    hint_type = models.CharField(max_length=20, choices=HINT_TYPE_CHOICES)
    is_enabled = models.BooleanField(default=False)
    min_attempts = models.IntegerField(default=3, help_text="Minimum attempts before hint is available")
    content = models.JSONField(default=dict, help_text="Hint-specific configuration")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['problem', 'hint_type']
        ordering = ['hint_type']
    
    def clean(self):
        """Validate content structure based on hint type"""
        if self.hint_type == 'variable_fade':
            if 'mappings' not in self.content:
                raise ValidationError('Variable fade hint must contain mappings')
            if not isinstance(self.content.get('mappings'), list):
                raise ValidationError('Mappings must be a list')
            for mapping in self.content.get('mappings', []):
                if not isinstance(mapping, dict) or 'from' not in mapping or 'to' not in mapping:
                    raise ValidationError('Each mapping must have "from" and "to" fields')
        
        elif self.hint_type == 'subgoal_highlight':
            if 'subgoals' not in self.content:
                raise ValidationError('Subgoal highlight hint must contain subgoals')
            if not isinstance(self.content.get('subgoals'), list):
                raise ValidationError('Subgoals must be a list')
            for subgoal in self.content.get('subgoals', []):
                required_fields = ['line_start', 'line_end', 'title', 'explanation']
                if not all(field in subgoal for field in required_fields):
                    raise ValidationError(f'Each subgoal must have: {", ".join(required_fields)}')
        
        elif self.hint_type == 'suggested_trace':
            if 'suggested_call' not in self.content:
                raise ValidationError('Suggested trace hint must contain suggested_call')
            if not isinstance(self.content.get('suggested_call'), str):
                raise ValidationError('Suggested call must be a string')
    
    def __str__(self):
        return f"{self.problem.title} - {self.get_hint_type_display()}"