from django.db import models
from django.contrib.auth.models import User

class ProblemSet(models.Model):

    sid = models.CharField(max_length=10, unique=True, primary_key=True)
    title = models.CharField(max_length=100, unique=True)
    problems = models.ManyToManyField('Problem', related_name='problem_sets')
    icon = models.ImageField(upload_to='problem_set_icons/', null=False)

    def __str__(self):
        return self.name

class Problem(models.Model):

    qid = models.CharField(max_length=100, unique=True, primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    solution = models.TextField()
    test_case_file = models.FileField(upload_to='testcases/')

    def __str__(self):
        return f"{self.qid}: {self.title}"
    
class PromptSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    score = models.IntegerField()
    time = models.DateTimeField(auto_now_add=True)
    prompt = models.TextField()

    def __str__(self):
        return f"{self.user} - {self.problem} - {self.score}"
    