from django.db import models
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem

class PromptSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='app_submissions')
    score = models.IntegerField()
    time = models.DateTimeField(auto_now_add=True)
    prompt = models.TextField()

    def __str__(self):
        return f"{self.user} - {self.problem} - {self.score}"