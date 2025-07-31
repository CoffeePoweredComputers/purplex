from django.contrib import admin
from django.utils.html import format_html
from .models import PromptSubmission, SegmentationResult

@admin.register(PromptSubmission)
class PromptSubmissionAdmin(admin.ModelAdmin):
    list_display = ['get_submission_info', 'score', 'passing_variations', 'total_variations', 'has_segmentation', 'submitted_at']
    list_filter = ['score', 'submitted_at', 'problem__difficulty', 'course']
    search_fields = ['user__username', 'problem__title', 'problem_set__title']
    readonly_fields = ['submitted_at', 'execution_time']
    date_hierarchy = 'submitted_at'
    
    def get_submission_info(self, obj):
        course_context = f" ({obj.course.course_id})" if obj.course else ""
        return f"{obj.user.username} - {obj.problem.title}{course_context}"
    get_submission_info.short_description = "Submission"
    
    def has_segmentation(self, obj):
        if hasattr(obj, 'segmentation'):
            level = obj.segmentation.comprehension_level
            color = {
                'relational': 'green',
                'transitional': 'orange', 
                'multi_structural': 'red'
            }.get(level, 'gray')
            return format_html(
                '<span style="color: {};">● {}</span>',
                color, level.title()
            )
        return format_html('<span style="color: gray;">No analysis</span>')
    has_segmentation.short_description = "Segmentation"

@admin.register(SegmentationResult)
class SegmentationResultAdmin(admin.ModelAdmin):
    list_display = ['get_submission_info', 'segment_count', 'get_comprehension_level', 'get_processing_time', 'created_at']
    list_filter = ['comprehension_level', 'segment_count', 'created_at']
    search_fields = ['submission__user__username', 'submission__problem__title']
    readonly_fields = ['submission', 'analysis', 'created_at', 'get_segments_display', 'get_feedback']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('submission', 'segment_count', 'comprehension_level', 'created_at')
        }),
        ('Analysis Data', {
            'fields': ('get_segments_display', 'get_feedback', 'analysis'),
            'classes': ('collapse',)
        }),
    )
    
    def get_submission_info(self, obj):
        return f"{obj.submission.user.username} - {obj.submission.problem.title}"
    get_submission_info.short_description = "Submission"
    
    def get_comprehension_level(self, obj):
        colors = {
            'relational': 'green',
            'transitional': 'orange',
            'multi_structural': 'red'
        }
        color = colors.get(obj.comprehension_level, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, obj.comprehension_level.replace('_', ' ').title()
        )
    get_comprehension_level.short_description = "Level"
    
    def get_processing_time(self, obj):
        time = obj.get_processing_time()
        return f"{time:.2f}s" if time else "N/A"
    get_processing_time.short_description = "Processing Time"
    
    def get_segments_display(self, obj):
        segments = obj.get_segments()
        if not segments:
            return "No segments"
        
        display = []
        for i, segment in enumerate(segments[:5], 1):  # Show first 5 segments
            text = segment.get('text', '')[:50] + ('...' if len(segment.get('text', '')) > 50 else '')
            display.append(f"{i}. {text}")
        
        if len(segments) > 5:
            display.append(f"... and {len(segments) - 5} more segments")
            
        return format_html('<br>'.join(display))
    get_segments_display.short_description = "Segments Preview"
    
    def get_feedback(self, obj):
        feedback = obj.get_feedback()
        return feedback if feedback else "No feedback available"
    get_feedback.short_description = "Feedback Message"