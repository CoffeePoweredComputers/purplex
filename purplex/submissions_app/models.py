from django.db import models
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet
from datetime import timedelta

class PromptSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='app_submissions')
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, related_name='submissions', null=True)
    score = models.IntegerField()
    time = models.DateTimeField(auto_now_add=True)
    prompt = models.TextField()
    user_solution = models.JSONField(default=dict, blank=True)
    firebase_uid = models.CharField(max_length=255, blank=True)
    submitted_by = models.CharField(max_length=255, blank=True, help_text="Username of the person who submitted this solution")

    
    # Additional fields for progress tracking
    execution_time = models.FloatField(null=True, blank=True, help_text="Execution time in seconds")
    passed_test_ids = models.JSONField(default=list, blank=True, help_text="IDs of test cases that passed")
    time_spent = models.DurationField(null=True, blank=True, help_text="Time user spent on this attempt")
    feedback = models.TextField(blank=True, help_text="Detailed feedback from test results")

    def __str__(self):
        problem_set_name = self.problem_set.title if self.problem_set else "Unknown Set"
        return f"{self.user} - {problem_set_name} - {self.problem.title} - {self.score}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Trigger progress update after saving
        from purplex.problems_app.models import UserProgress, UserProblemSetProgress
        
        # Update user progress with problem set context
        # Note: course context needs to be passed from the submission endpoint
        progress, created = UserProgress.objects.get_or_create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=getattr(self, '_course', None),  # Course will be set by view
            defaults={'problem_version': self.problem.version}
        )
        progress.update_from_submission(self, time_spent=self.time_spent)
        
        # Update problem set progress
        UserProblemSetProgress.update_from_progress(progress)
