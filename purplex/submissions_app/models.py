from django.db import models
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, Course
from datetime import timedelta

class PromptSubmission(models.Model):
    # Core relationships - INCLUDING COURSE
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, related_name='submissions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    
    # Submission data
    prompt = models.TextField()
    score = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True, null=True)
    
    # EiPL specific fields (stored as separate columns for efficiency)
    code_variations = models.JSONField(default=list, help_text="List of generated code variations")
    test_results = models.JSONField(default=list, help_text="Test results for each variation")
    passing_variations = models.IntegerField(default=0, help_text="Number of variations that passed all tests")
    total_variations = models.IntegerField(default=0, help_text="Total number of variations generated")
    
    # Performance tracking
    execution_time = models.FloatField(null=True, blank=True, help_text="Total execution time in seconds")
    time_spent = models.DurationField(null=True, blank=True, help_text="Time user spent on this attempt")

    class Meta:
        indexes = [
            models.Index(fields=['user', 'problem', 'course', '-submitted_at']),
            models.Index(fields=['user', 'problem_set', 'course', '-submitted_at']),
            models.Index(fields=['course', 'problem_set', 'problem', '-score']),
        ]
        ordering = ['-submitted_at']
    
    def __str__(self):
        course_context = f" ({self.course.course_id})" if self.course else ""
        return f"{self.user.username} - {self.problem_set.title}{course_context} - {self.problem.title} - {self.score}%"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Trigger progress update after saving
        from purplex.problems_app.models import UserProgress, UserProblemSetProgress
        
        # Update user progress with course context
        progress, created = UserProgress.objects.get_or_create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course,  # Now properly included
            defaults={'problem_version': self.problem.version}
        )
        progress.update_from_submission(self, time_spent=self.time_spent)
        
        # Update problem set progress
        UserProblemSetProgress.update_from_progress(progress)
