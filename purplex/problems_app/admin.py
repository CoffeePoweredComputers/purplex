from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
import csv
from datetime import datetime
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter
from .models import (
    Problem, McqProblem, EiplProblem, PromptProblem,
    ProblemSet, ProblemCategory, TestCase, ProblemSetMembership,
    UserProgress, UserProblemSetProgress
)

@admin.register(ProblemCategory)
class ProblemCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'colored_icon', 'order', 'problems_count']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    
    def colored_icon(self, obj):
        if obj.color:
            return format_html(
                '<span style="color: {};">●</span>',
                obj.color
            )
        return ''
    colored_icon.short_description = 'Color'
    
    def problems_count(self, obj):
        return obj.problems.count()
    problems_count.short_description = 'Problems'

class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0  # No extra empty forms since it's read-only
    fields = ['inputs', 'expected_output', 'description', 'is_hidden', 'is_sample', 'order']
    ordering = ['order']
    can_delete = False  # Disable deletion
    
    def has_add_permission(self, request, obj=None):
        return False  # Disable adding new test cases
    
    def has_change_permission(self, request, obj=None):
        return False  # Make inline read-only

class McqProblemChildAdmin(PolymorphicChildModelAdmin):
    """Admin for MCQ problems (polymorphic child)."""
    base_model = McqProblem
    show_in_index = True

    list_display = ['title', 'slug', 'difficulty', 'is_active', 'allow_multiple', 'created_at']
    search_fields = ['title', 'slug', 'question_text']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'difficulty', 'categories', 'tags', 'is_active')
        }),
        ('MCQ Content', {
            'fields': ('question_text', 'grading_mode', 'options', 'allow_multiple', 'shuffle_options')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'version'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields if f.name not in ['options', 'question_text', 'is_active']] + ['categories']


@admin.register(Problem)
class ProblemAdmin(PolymorphicParentModelAdmin):
    """Polymorphic parent admin for all problem types."""
    base_model = Problem
    child_models = (McqProblem, EiplProblem, PromptProblem)
    polymorphic_list = True

    list_display = ['title', 'slug', 'polymorphic_type_display', 'difficulty', 'is_active', 'test_cases_count', 'created_at', 'edit_link']
    list_filter = [PolymorphicChildModelFilter, 'difficulty', 'is_active', 'categories', 'created_at']
    search_fields = ['title', 'slug', 'description', 'function_name']

    # Make all fields read-only (editing via Vue admin)
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields] + ['categories', 'test_cases_count', 'visible_test_cases_count']

    # Disable add permission (use Vue admin)
    def has_add_permission(self, request):
        return False

    def polymorphic_type_display(self, obj):
        """Display the polymorphic type."""
        return obj.polymorphic_type
    polymorphic_type_display.short_description = 'Type'

    def test_cases_count(self, obj):
        return obj.test_cases.count()
    test_cases_count.short_description = 'Test Cases'

    def edit_link(self, obj):
        if obj.slug:
            url = f'/admin/problems/{obj.slug}/edit'
            return format_html('<a href="{}" target="_blank">Edit in Vue Admin →</a>', url)
        return '-'
    edit_link.short_description = 'Edit'

    # Override change form template to show a notice
    change_form_template = 'admin/problems_app/problem/change_form.html'


@admin.register(McqProblem)
class McqProblemAdmin(admin.ModelAdmin):
    """Standalone admin for MCQ problems."""
    list_display = ['title', 'slug', 'difficulty', 'allow_multiple', 'is_active', 'created_at']
    list_filter = ['difficulty', 'is_active', 'allow_multiple', 'grading_mode']
    search_fields = ['title', 'slug', 'question_text']
    filter_horizontal = ['categories']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'difficulty', 'categories', 'tags', 'is_active')
        }),
        ('MCQ Content', {
            'fields': ('question_text', 'grading_mode', 'options', 'allow_multiple', 'shuffle_options'),
            'description': 'Configure the multiple choice question'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'version'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        # Make most fields read-only, allow editing question content
        readonly = ['slug', 'created_by', 'created_at', 'updated_at', 'version']
        return readonly


@admin.register(EiplProblem)
class EiplProblemAdmin(admin.ModelAdmin):
    """Standalone admin for EiPL problems."""
    list_display = ['title', 'slug', 'difficulty', 'is_active', 'test_cases_count', 'created_at']
    list_filter = ['difficulty', 'is_active', 'requires_highlevel_comprehension']
    search_fields = ['title', 'slug', 'description', 'function_name']
    filter_horizontal = ['categories']
    inlines = [TestCaseInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'difficulty', 'categories', 'tags', 'is_active')
        }),
        ('Code Execution', {
            'fields': ('reference_solution', 'function_signature', 'function_name', 'memory_limit'),
            'description': 'Code execution configuration'
        }),
        ('LLM Configuration', {
            'fields': ('llm_config',),
            'classes': ('collapse',)
        }),
        ('Segmentation', {
            'fields': ('segmentation_config', 'segmentation_threshold', 'requires_highlevel_comprehension'),
            'description': 'Comprehension analysis settings'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'version'),
            'classes': ('collapse',)
        })
    )

    def test_cases_count(self, obj):
        return obj.test_cases.count()
    test_cases_count.short_description = 'Test Cases'

    def get_readonly_fields(self, request, obj=None):
        readonly = ['slug', 'created_by', 'created_at', 'updated_at', 'version']
        return readonly


@admin.register(PromptProblem)
class PromptProblemAdmin(admin.ModelAdmin):
    """Standalone admin for Prompt problems (image-based EiPL)."""
    list_display = ['title', 'slug', 'difficulty', 'is_active', 'test_cases_count', 'created_at']
    list_filter = ['difficulty', 'is_active', 'requires_highlevel_comprehension']
    search_fields = ['title', 'slug', 'description', 'function_name']
    filter_horizontal = ['categories']
    inlines = [TestCaseInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'difficulty', 'categories', 'tags', 'is_active')
        }),
        ('Image Display', {
            'fields': ('image_url', 'image_alt_text'),
            'description': 'Image to display instead of code'
        }),
        ('Code Execution', {
            'fields': ('reference_solution', 'function_signature', 'function_name', 'memory_limit'),
            'description': 'Code execution configuration'
        }),
        ('LLM Configuration', {
            'fields': ('llm_config',),
            'classes': ('collapse',)
        }),
        ('Segmentation', {
            'fields': ('segmentation_config', 'segmentation_threshold', 'requires_highlevel_comprehension'),
            'description': 'Comprehension analysis settings'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'version'),
            'classes': ('collapse',)
        })
    )

    def test_cases_count(self, obj):
        return obj.test_cases.count()
    test_cases_count.short_description = 'Test Cases'

    def get_readonly_fields(self, request, obj=None):
        readonly = ['slug', 'created_by', 'created_at', 'updated_at', 'version']
        return readonly


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'problem', 'order', 'is_hidden', 'is_sample', 'created_at']
    list_filter = ['is_hidden', 'is_sample', 'problem', 'created_at']
    search_fields = ['problem__title', 'description']
    ordering = ['problem', 'order']

class ProblemSetMembershipInline(admin.TabularInline):
    model = ProblemSetMembership
    extra = 1
    autocomplete_fields = ['problem']
    ordering = ['order']

@admin.register(ProblemSet)
class ProblemSetAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_public', 'problems_count', 'created_by', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['title', 'slug', 'description']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'problems_count']
    inlines = [ProblemSetMembershipInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'icon', 'is_public')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'problems_count'),
            'classes': ('collapse',)
        })
    )
    
    def problems_count(self, obj):
        return obj.problems.count()
    problems_count.short_description = 'Problems'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ProblemSetMembership)
class ProblemSetMembershipAdmin(admin.ModelAdmin):
    list_display = ['problem_set', 'problem', 'order', 'created_at']
    list_filter = ['problem_set', 'created_at']
    search_fields = ['problem_set__title', 'problem__title']
    ordering = ['problem_set', 'order']
    autocomplete_fields = ['problem_set', 'problem']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    """Admin interface for individual problem progress tracking."""

    list_display = [
        'user_display',
        'problem_display',
        'problem_set_display',
        'course_display',
        'status_display',
        'grade_display',
        'score_display',
        'attempts',
        'is_completed',
        'last_attempt'
    ]

    list_filter = [
        'status',
        'grade',
        'is_completed',
        'course',
        'problem_set',
        'last_attempt'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'problem__title',
        'problem__slug',
        'problem_set__title'
    ]

    readonly_fields = [
        'user', 'problem', 'problem_set', 'course',
        'first_attempt', 'last_attempt', 'completed_at',
        'best_score', 'average_score', 'attempts'
    ]

    date_hierarchy = 'last_attempt'

    actions = ['export_as_csv']

    def user_display(self, obj):
        return obj.user.username
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__username'

    def problem_display(self, obj):
        return obj.problem.title
    problem_display.short_description = 'Problem'
    problem_display.admin_order_field = 'problem__title'

    def problem_set_display(self, obj):
        return obj.problem_set.title if obj.problem_set else '-'
    problem_set_display.short_description = 'Problem Set'

    def course_display(self, obj):
        return obj.course.course_id if obj.course else '-'
    course_display.short_description = 'Course'

    def status_display(self, obj):
        colors = {
            'not_started': 'gray',
            'in_progress': 'orange',
            'completed': 'green'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def grade_display(self, obj):
        colors = {
            'complete': 'green',
            'partial': 'orange',
            'incomplete': 'red'
        }
        icons = {
            'complete': '✅',
            'partial': '⚠️',
            'incomplete': '❌'
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.grade, 'black'),
            icons.get(obj.grade, ''),
            obj.get_grade_display()
        )
    grade_display.short_description = 'Grade'

    def score_display(self, obj):
        color = 'green' if obj.best_score >= 80 else 'orange' if obj.best_score >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            obj.best_score
        )
    score_display.short_description = 'Best Score'

    def export_as_csv(self, request, queryset):
        """Export selected progress records as CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=user_progress_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        writer = csv.writer(response)

        # Write header
        writer.writerow([
            'Username', 'Email', 'Problem', 'Problem Slug',
            'Problem Set', 'Course', 'Status', 'Grade',
            'Best Score', 'Avg Score', 'Attempts', 'Successful Attempts',
            'Hints Used', 'First Attempt', 'Last Attempt', 'Completed At',
            'Total Time Spent (minutes)', 'Is Completed', 'Completion %'
        ])

        # Write data rows
        for obj in queryset.select_related('user', 'problem_set', 'course'):
            # Convert timedelta to minutes
            time_spent_minutes = None
            if obj.total_time_spent:
                time_spent_minutes = int(obj.total_time_spent.total_seconds() / 60)

            writer.writerow([
                obj.user.username,
                obj.user.email,
                obj.problem.title,
                obj.problem.slug,
                obj.problem_set.title if obj.problem_set else '',
                obj.course.course_id if obj.course else '',
                obj.status,
                obj.grade,
                obj.best_score,
                round(obj.average_score, 2),
                obj.attempts,
                obj.successful_attempts,
                obj.hints_used,
                obj.first_attempt.isoformat() if obj.first_attempt else '',
                obj.last_attempt.isoformat() if obj.last_attempt else '',
                obj.completed_at.isoformat() if obj.completed_at else '',
                time_spent_minutes,
                obj.is_completed,
                obj.completion_percentage
            ])

        return response

    export_as_csv.short_description = "Export selected progress to CSV"


@admin.register(UserProblemSetProgress)
class UserProblemSetProgressAdmin(admin.ModelAdmin):
    """Admin interface for problem set progress tracking."""

    list_display = [
        'user',
        'problem_set',
        'course_display',
        'completion_display',
        'completed_problems',
        'total_problems',
        'average_score',
        'is_completed',
        'last_activity'
    ]

    list_filter = [
        'is_completed',
        'course',
        'problem_set',
        'last_activity'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'problem_set__title'
    ]

    readonly_fields = [
        'user', 'problem_set', 'course',
        'total_problems', 'completed_problems',
        'first_attempt', 'last_activity', 'completed_at'
    ]

    date_hierarchy = 'last_activity'

    actions = ['export_as_csv']

    def course_display(self, obj):
        return obj.course.course_id if obj.course else '-'
    course_display.short_description = 'Course'

    def completion_display(self, obj):
        color = 'green' if obj.completion_percentage >= 80 else 'orange' if obj.completion_percentage >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            obj.completion_percentage
        )
    completion_display.short_description = 'Completion'

    def export_as_csv(self, request, queryset):
        """Export selected problem set progress as CSV."""

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=problem_set_progress_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        writer = csv.writer(response)

        writer.writerow([
            'Username', 'Email', 'Problem Set', 'Course',
            'Total Problems', 'Completed', 'In Progress',
            'Avg Score', 'Completion %', 'Is Completed',
            'First Attempt', 'Last Activity', 'Completed At'
        ])

        for obj in queryset.select_related('user', 'problem_set', 'course'):
            writer.writerow([
                obj.user.username,
                obj.user.email,
                obj.problem_set.title,
                obj.course.course_id if obj.course else '',
                obj.total_problems,
                obj.completed_problems,
                obj.in_progress_problems,
                round(obj.average_score, 2),
                obj.completion_percentage,
                obj.is_completed,
                obj.first_attempt.isoformat() if obj.first_attempt else '',
                obj.last_activity.isoformat() if obj.last_activity else '',
                obj.completed_at.isoformat() if obj.completed_at else ''
            ])

        return response

    export_as_csv.short_description = "Export selected problem set progress to CSV"