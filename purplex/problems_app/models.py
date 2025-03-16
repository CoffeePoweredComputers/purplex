from django.db import models

class ProblemSet(models.Model):
    sid = models.CharField(max_length=10, unique=True, primary_key=True)
    title = models.CharField(max_length=100, unique=True)
    problems = models.ManyToManyField('Problem', related_name='problem_sets', blank=True)
    icon = models.ImageField(upload_to='problem_set_icons/', null=True, blank=True)

    def __str__(self):
        return self.title

class Problem(models.Model):
    qid = models.CharField(max_length=100, unique=True, primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    solution = models.TextField()
    test_case_file = models.FileField(upload_to='testcases/')

    def __str__(self):
        return f"{self.qid}: {self.title}"