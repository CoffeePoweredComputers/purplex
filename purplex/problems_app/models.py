from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError
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
    description = models.TextField()
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