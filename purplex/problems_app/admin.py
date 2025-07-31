from django.contrib import admin
from django.utils.html import format_html
from .models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership

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
    extra = 1
    fields = ['inputs', 'expected_output', 'description', 'is_hidden', 'is_sample', 'order']
    ordering = ['order']

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'difficulty', 'function_name', 'is_active', 'test_cases_count', 'created_at']
    list_filter = ['difficulty', 'is_active', 'categories', 'created_at']
    search_fields = ['title', 'slug', 'description', 'function_name']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['categories']
    readonly_fields = ['created_at', 'updated_at', 'test_cases_count', 'visible_test_cases_count']
    inlines = [TestCaseInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'difficulty', 'categories', 'tags')
        }),
        ('Function Details', {
            'fields': ('function_name', 'function_signature', 'reference_solution', 'hints')
        }),
        ('Segmentation Settings', {
            'fields': ('segmentation_config',),
            'classes': ('collapse',),
            'description': 'Configure prompt segmentation for EiPL problems. JSON format with enabled, threshold, and examples.'
        }),
        ('Settings', {
            'fields': ('memory_limit', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'version', 'test_cases_count', 'visible_test_cases_count'),
            'classes': ('collapse',)
        })
    )
    
    def test_cases_count(self, obj):
        return obj.test_cases.count()
    test_cases_count.short_description = 'Test Cases'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

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