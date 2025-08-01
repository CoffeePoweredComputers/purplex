from django.contrib import admin
from django.utils.html import format_html
from .models import PromptSubmission, SegmentationResult

@admin.register(PromptSubmission)
class PromptSubmissionAdmin(admin.ModelAdmin):
    list_display = ['get_submission_info', 'score', 'passing_variations', 'total_variations', 'submitted_at']
    list_filter = ['score', 'submitted_at', 'problem__difficulty', 'course']
    search_fields = ['user__username', 'problem__title', 'problem_set__title']
    readonly_fields = ['submitted_at', 'execution_time']
    date_hierarchy = 'submitted_at'
    
    def get_submission_info(self, obj):
        course_context = f" ({obj.course.course_id})" if obj.course else ""
        return f"{obj.user.username} - {obj.problem.title}{course_context}"
    get_submission_info.short_description = "Submission"


@admin.register(SegmentationResult)
class SegmentationResultAdmin(admin.ModelAdmin):
    list_display = ['get_submission_info', 'segment_count', 'comprehension_level', 'created_at']
    list_filter = ['comprehension_level', 'created_at', 'submission__problem']
    search_fields = ['submission__user__username', 'submission__problem__title']
    readonly_fields = ['submission', 'segment_count', 'comprehension_level', 'created_at', 'get_segments_display', 'get_feedback']
    date_hierarchy = 'created_at'
    
    def get_submission_info(self, obj):
        return f"{obj.submission.user.username} - {obj.submission.problem.title}"
    get_submission_info.short_description = "Submission"
    
    def get_segments_display(self, obj):
        """Display segments in a readable format"""
        segments = obj.get_segments()
        if not segments:
            return "No segments"
        
        html = '<div style="font-family: monospace; white-space: pre-wrap;">'
        for seg in segments:
            lines = ', '.join(str(l) for l in seg.get('code_lines', []))
            html += f'<strong>Segment {seg.get("id", "?")}:</strong> "{seg.get("text", "")}" <em>(lines: {lines})</em><br><br>'
        html += '</div>'
        return format_html(html)
    get_segments_display.short_description = "Segments"
    
    def get_feedback(self, obj):
        """Display feedback message"""
        return obj.get_feedback() or "No feedback"
    get_feedback.short_description = "Feedback"
    
    # Exclude raw analysis field from form view
    exclude = ['analysis']
