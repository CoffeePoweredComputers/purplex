"""
Service layer for the new submission system.
Handles all business logic for submissions.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import timedelta
from django.db import transaction
from django.contrib.auth.models import User
import logging

from .models import (
    Submission,
    TestExecution,
    HintActivation,
    CodeVariation,
    SegmentationAnalysis,
    SubmissionFeedback
)
from purplex.problems_app.services import ProgressService
from .grading_service import GradingService

logger = logging.getLogger(__name__)


class SubmissionService:
    """
    Central service for all submission operations.
    """

    @classmethod
    def _create_submission_no_transaction(
        cls,
        user: User,
        problem: 'Problem',
        raw_input: str,
        submission_type: str,
        problem_set: Optional['ProblemSet'] = None,
        course: Optional['Course'] = None,
        time_spent: Optional[timedelta] = None,
        activated_hints: Optional[List[Dict]] = None,
    ) -> Submission:
        """
        Create submission WITHOUT @transaction.atomic decorator.

        This method is designed for use within larger atomic blocks (e.g., pipeline tasks)
        where the caller manages the transaction boundary. Using this prevents nested
        transactions which can cause performance issues and savepoint overhead.

        For standalone submission creation, use create_submission() instead.

        Transaction Management Pattern:
        - create_submission() = Wraps this method with @transaction.atomic
        - _create_submission_no_transaction() = Raw operation, caller manages transaction
        """
        # Create main submission
        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            raw_input=raw_input,
            submission_type=submission_type,
            time_spent=time_spent,
            execution_status='pending',
            # Explicitly set defaults for new grading fields
            comprehension_level='not_evaluated',
            is_correct=False
        )

        # Track hint activations
        if activated_hints:
            from purplex.problems_app.models import ProblemHint

            for order, hint_data in enumerate(activated_hints):
                # Support both hint_id and hint_type
                if 'hint_id' in hint_data:
                    # Direct hint ID provided
                    hint_id = hint_data['hint_id']
                elif 'hint_type' in hint_data:
                    # Look up hint by type for this problem
                    try:
                        hint = ProblemHint.objects.get(
                            problem=problem,
                            hint_type=hint_data['hint_type']
                        )
                        hint_id = hint.id
                    except ProblemHint.DoesNotExist:
                        logger.warning(f"Hint type {hint_data['hint_type']} not found for problem {problem.slug}")
                        continue
                else:
                    logger.warning("Hint data missing both hint_id and hint_type")
                    continue

                HintActivation.objects.create(
                    submission=submission,
                    hint_id=hint_id,
                    activation_order=order,
                    trigger_type=hint_data.get('trigger_type', 'manual'),
                    viewed_duration_seconds=hint_data.get('duration_seconds')
                )

        logger.info(f"Created submission {submission.submission_id} for user {user.username}")

        return submission

    @classmethod
    @transaction.atomic
    def create_submission(
        cls,
        user: User,
        problem: 'Problem',
        raw_input: str,
        submission_type: str,
        problem_set: Optional['ProblemSet'] = None,
        course: Optional['Course'] = None,
        time_spent: Optional[timedelta] = None,
        activated_hints: Optional[List[Dict]] = None,
    ) -> Submission:
        """
        Create a new submission with all related data.

        Args:
            user: The user making the submission
            problem: The problem being submitted for
            raw_input: The user's input (code or natural language)
            submission_type: Type of submission ('direct_code', 'eipl', 'function_redef')
            problem_set: Optional problem set context
            course: Optional course context
            time_spent: Time spent on this attempt
            activated_hints: List of dicts with hint_id and trigger_type

        Returns:
            Created Submission instance
        """
        return cls._create_submission_no_transaction(
            user=user,
            problem=problem,
            raw_input=raw_input,
            submission_type=submission_type,
            problem_set=problem_set,
            course=course,
            time_spent=time_spent,
            activated_hints=activated_hints
        )

    @classmethod
    @transaction.atomic
    def record_test_results(
        cls,
        submission: Submission,
        test_results: List[Dict],
        processed_code: str,
        execution_time_ms: Optional[int] = None,
        memory_used_mb: Optional[float] = None
    ) -> None:
        """
        Record all test execution results for a submission.

        Args:
            submission: The submission to update
            test_results: List of test result dictionaries
            processed_code: The final code that was executed
            execution_time_ms: Total execution time
            memory_used_mb: Peak memory usage
        """
        submission.processed_code = processed_code
        submission.execution_time_ms = execution_time_ms
        submission.memory_used_mb = memory_used_mb

        passed_count = 0
        total_count = len(test_results)

        for order, result in enumerate(test_results):
            test_execution = TestExecution.objects.create(
                submission=submission,
                test_case_id=result['test_case_id'],
                execution_order=order,
                passed=result['passed'],
                input_values=result['inputs'],
                expected_output=result['expected'],
                actual_output=result.get('actual'),
                error_type=result.get('error_type', 'none'),
                error_message=result.get('error_message'),
                error_traceback=result.get('traceback'),
                execution_time_ms=result.get('execution_time_ms'),
                memory_used_kb=result.get('memory_used_kb')
            )

            if test_execution.passed:
                passed_count += 1

        # Update submission with results
        submission.score = int((passed_count / total_count * 100) if total_count > 0 else 0)
        submission.passed_all_tests = (passed_count == total_count)
        submission.is_correct = submission.passed_all_tests  # Set new field
        submission.execution_status = 'completed'

        # Determine completion status using new GradingService
        grade = GradingService.calculate_grade(submission)

        # Map grade to legacy completion_status for backward compatibility
        submission.completion_status = cls._map_grade_to_completion_status(grade)

        submission.save()

        # Update progress using unified ProgressService
        ProgressService.process_submission(submission)

        logger.info(f"Recorded {total_count} test results for submission {submission.submission_id}, score: {submission.score}%")

    @classmethod
    @transaction.atomic
    def record_eipl_variations(
        cls,
        submission: Submission,
        variations: List[Dict]
    ) -> CodeVariation:
        """
        Record code variations for EiPL submissions.

        Args:
            submission: The submission to update
            variations: List of variation data dictionaries

        Returns:
            The best CodeVariation instance
        """
        best_score = 0
        best_variation = None

        for idx, var_data in enumerate(variations):
            variation = CodeVariation.objects.create(
                submission=submission,
                variation_index=idx,
                generated_code=var_data['code'],
                tests_passed=var_data.get('tests_passed', 0),
                tests_total=var_data.get('tests_total', 0),
                score=var_data.get('score', 0),
                model_used=var_data.get('model', 'gpt-4o-mini'),
                prompt_tokens=var_data.get('prompt_tokens'),
                completion_tokens=var_data.get('completion_tokens'),
                generation_time_ms=var_data.get('generation_time_ms')
            )

            if variation.score > best_score:
                best_score = variation.score
                best_variation = variation

        # Mark best variation
        if best_variation:
            best_variation.is_selected = True
            best_variation.save()

        logger.info(f"Recorded {len(variations)} code variations for submission {submission.submission_id}")

        return best_variation

    @classmethod
    def _record_eipl_test_results_no_transaction(
        cls,
        submission: Submission,
        variations_with_tests: List[Dict]
    ) -> None:
        """
        Record EiPL test results WITHOUT @transaction.atomic decorator.

        PERFORMANCE OPTIMIZED: Uses bulk_create to reduce ~90% of INSERT operations.
        Instead of ~30 individual test execution inserts, performs 1 bulk operation.

        This method is designed for use within larger atomic blocks (e.g., pipeline tasks).
        For standalone usage, use record_eipl_test_results() instead.

        Transaction Management Pattern:
        - record_eipl_test_results() = Wraps this method with @transaction.atomic
        - _record_eipl_test_results_no_transaction() = Raw operation, caller manages transaction
        """
        total_passed = 0
        total_tests = 0
        execution_order = 0

        # PERFORMANCE: Collect all test executions for bulk create
        all_test_executions = []
        variation_updates = []

        for var_data in variations_with_tests:
            variation = var_data['variation']
            test_results = var_data['test_results']

            var_passed = 0
            var_total = len(test_results)

            for test_result in test_results:
                is_passed = test_result['passed']

                # Create test execution object (not saved yet)
                test_execution = TestExecution(
                    submission=submission,
                    test_case_id=test_result['test_case_id'],
                    code_variation=variation,  # Link to specific variation
                    execution_order=execution_order,
                    passed=is_passed,
                    input_values=test_result['inputs'],
                    expected_output=test_result['expected'],
                    actual_output=test_result.get('actual'),
                    error_type=test_result.get('error_type', 'none'),
                    error_message=test_result.get('error_message'),
                    error_traceback=test_result.get('traceback'),
                    execution_time_ms=test_result.get('execution_time_ms'),
                    memory_used_kb=test_result.get('memory_used_kb')
                )
                all_test_executions.append(test_execution)
                execution_order += 1

                if is_passed:
                    var_passed += 1
                    total_passed += 1

            # Store variation update data
            variation_updates.append({
                'variation': variation,
                'passed': var_passed,
                'total': var_total
            })

            total_tests += var_total

        # PERFORMANCE: Bulk create all test executions in ONE query
        # This replaces ~30 individual INSERT statements with 1
        if all_test_executions:
            TestExecution.objects.bulk_create(all_test_executions)

        # Update all variations with test counts
        for var_update in variation_updates:
            variation = var_update['variation']
            variation.tests_passed = var_update['passed']
            variation.tests_total = var_update['total']
            variation.score = int((var_update['passed'] / var_update['total'] * 100) if var_update['total'] > 0 else 0)
            variation.save()

        # Update submission with overall results
        submission.score = int((total_passed / total_tests * 100) if total_tests > 0 else 0)
        submission.passed_all_tests = (total_passed == total_tests)
        submission.is_correct = submission.passed_all_tests  # Set new field
        submission.execution_status = 'completed'

        # Determine completion status using new GradingService
        # Note: For EiPL with segmentation, this will be updated after segmentation
        grade = GradingService.calculate_grade(submission)

        # Map grade to legacy completion_status for backward compatibility
        submission.completion_status = cls._map_grade_to_completion_status(grade)

        submission.save()

        # Update progress using unified ProgressService
        ProgressService.process_submission(submission)

        logger.info(f"Recorded {total_tests} test results across {len(variations_with_tests)} variations for submission {submission.submission_id}")

    @classmethod
    @transaction.atomic
    def record_eipl_test_results(
        cls,
        submission: Submission,
        variations_with_tests: List[Dict]
    ) -> None:
        """
        Record test results for all EiPL variations.

        Args:
            submission: The submission to update
            variations_with_tests: List of dicts with 'variation' (CodeVariation) and 'test_results' (list of test data)
        """
        cls._record_eipl_test_results_no_transaction(submission, variations_with_tests)

    @classmethod
    def _record_segmentation_no_transaction(
        cls,
        submission: Submission,
        segmentation_data: Dict
    ) -> SegmentationAnalysis:
        """
        Record segmentation analysis WITHOUT @transaction.atomic decorator.

        This method is designed for use within larger atomic blocks (e.g., pipeline tasks).
        For standalone usage, use record_segmentation() instead.

        Transaction Management Pattern:
        - record_segmentation() = Wraps this method with @transaction.atomic
        - _record_segmentation_no_transaction() = Raw operation, caller manages transaction
        """
        # Calculate passed status based on threshold
        # Get threshold from submission's problem config or use default
        threshold = 2  # Default threshold
        if submission.problem and hasattr(submission.problem, 'segmentation_config'):
            threshold = submission.problem.segmentation_config.get('threshold', 2)

        # Use passed from segmentation_data if available, otherwise calculate
        passed = segmentation_data.get('passed', segmentation_data['segment_count'] <= threshold)

        analysis = SegmentationAnalysis.objects.create(
            submission=submission,
            segment_count=segmentation_data['segment_count'],
            comprehension_level=segmentation_data['comprehension_level'],
            segments=segmentation_data['segments'],
            code_mappings=segmentation_data.get('code_mappings', {}),
            confidence_score=segmentation_data.get('confidence', 0.0),
            processing_time_ms=segmentation_data.get('processing_time_ms', 0),
            model_used=segmentation_data.get('model', 'gpt-4o-mini'),
            feedback_message=segmentation_data.get('feedback', ''),
            suggested_improvements=segmentation_data.get('improvements', []),
            passed=passed
        )

        # Update submission's comprehension level
        if segmentation_data['comprehension_level'] == 'relational':
            submission.comprehension_level = 'high-level'
        else:
            submission.comprehension_level = 'low-level'

        # Update submission completion using new GradingService
        grade = GradingService.calculate_grade(submission)

        # Map grade to legacy completion_status for backward compatibility
        submission.completion_status = cls._map_grade_to_completion_status(grade)

        submission.save()

        # PERFORMANCE: Final progress update - this is the last step in the pipeline
        # Update progress using unified ProgressService (full update with all dimensions)
        ProgressService.process_submission(submission)

        logger.info(f"Recorded segmentation analysis for submission {submission.submission_id}: {analysis.comprehension_level}")

        return analysis

    @classmethod
    @transaction.atomic
    def record_segmentation(
        cls,
        submission: Submission,
        segmentation_data: Dict
    ) -> SegmentationAnalysis:
        """
        Record segmentation analysis for EiPL submissions.

        Args:
            submission: The submission to update
            segmentation_data: Segmentation analysis data

        Returns:
            Created SegmentationAnalysis instance
        """
        return cls._record_segmentation_no_transaction(submission, segmentation_data)

    @classmethod
    def get_submission_details(cls, submission_id: str) -> Dict:
        """
        Get complete submission details for display.

        Args:
            submission_id: UUID of the submission

        Returns:
            Dictionary with complete submission details
        """
        from django.db.models import Prefetch
        from purplex.utils.query_monitor import query_counter

        with query_counter("get_submission_details", warning_threshold=5):
            # Optimized prefetch strategy to eliminate N+1 queries
            submission = Submission.objects.select_related(
                'user', 'problem', 'problem_set', 'course', 'segmentation'
            ).prefetch_related(
                'test_executions__test_case',
                'hint_activations__hint',
                # Use Prefetch for better control over nested prefetching
                Prefetch('code_variations',
                         queryset=CodeVariation.objects.prefetch_related('test_executions__test_case')),
                Prefetch('feedback',
                         queryset=SubmissionFeedback.objects.select_related('provided_by').filter(is_visible_to_student=True))
            ).get(submission_id=submission_id)

            details = {
                'submission_id': str(submission.submission_id),
                'user': submission.user.username,
                'problem': {
                    'slug': submission.problem.slug,
                    'title': submission.problem.title
                },
                'problem_set': {
                    'slug': submission.problem_set.slug,
                    'title': submission.problem_set.title
                } if submission.problem_set else None,
                'course': {
                    'id': submission.course.course_id,
                    'name': submission.course.name
                } if submission.course else None,
                'submitted_at': submission.submitted_at.isoformat(),
                'submission_type': submission.submission_type,
                'score': submission.score,
                'passed_all_tests': submission.passed_all_tests,
                'completion_status': submission.completion_status,
                'execution_status': submission.execution_status,
                'execution_time_ms': submission.execution_time_ms,
                'memory_used_mb': submission.memory_used_mb,
                'time_spent': submission.time_spent.total_seconds() if submission.time_spent else None,
                'raw_input': submission.raw_input,
                'processed_code': submission.processed_code,
            }

            # Add test results
            details['test_results'] = [
            {
                'test_case_id': te.test_case.id,
                'description': te.test_case.description,
                'passed': te.passed,
                'inputs': te.input_values,
                'expected': te.expected_output,
                'actual': te.actual_output,
                'error_type': te.error_type,
                'error_message': te.error_message,
                'execution_time_ms': te.execution_time_ms,
                'is_hidden': te.test_case.is_hidden
            }
                for te in submission.test_executions.all()
            ]

            # Add hints used
            details['hints_activated'] = [
            {
                'hint_id': ha.hint.id,
                'hint_type': ha.hint.hint_type,
                'activated_at': ha.activated_at.isoformat(),
                'trigger_type': ha.trigger_type,
                'viewed_duration_seconds': ha.viewed_duration_seconds
            }
                for ha in submission.hint_activations.all()
            ]

            # Add segmentation if exists
            if hasattr(submission, 'segmentation'):
                seg = submission.segmentation
                details['segmentation'] = {
                'comprehension_level': seg.comprehension_level,
                'segment_count': seg.segment_count,
                'segments': seg.segments,
                'feedback_message': seg.feedback_message,
                'suggested_improvements': seg.suggested_improvements,
                'confidence_score': seg.confidence_score
            }

            # Add code variations for EiPL
            if submission.submission_type == 'eipl':
                details['code_variations'] = []
                for cv in submission.code_variations.all():
                    # Get test results for this specific variation
                    variation_test_results = [
                    {
                        'test_case_id': te.test_case.id,
                        'description': te.test_case.description,
                        'passed': te.passed,
                        'isSuccessful': te.passed,  # For frontend compatibility
                        'inputs': te.input_values,
                        'expected': te.expected_output,
                        'expected_output': te.expected_output,  # For frontend compatibility
                        'actual': te.actual_output,
                        'actual_output': te.actual_output,  # For frontend compatibility
                        'error_type': te.error_type,
                        'error_message': te.error_message,
                        'error': te.error_message,  # For frontend compatibility
                        'execution_time_ms': te.execution_time_ms,
                        'is_hidden': te.test_case.is_hidden
                    }
                        for te in cv.test_executions.all()
                    ]

                    details['code_variations'].append({
                    'index': cv.variation_index,
                    'score': cv.score,
                    'tests_passed': cv.tests_passed,
                    'tests_total': cv.tests_total,
                    'is_selected': cv.is_selected,
                    'code': cv.generated_code,
                    'test_results': variation_test_results  # Add per-variation test results
                })

            # Add feedback
            details['feedback'] = [
            {
                'type': fb.feedback_type,
                'message': fb.message,
                'provided_by': fb.provided_by.username if fb.provided_by else None,
                'is_automated': fb.is_automated,
                'created_at': fb.created_at.isoformat()
            }
                for fb in submission.feedback.all()  # Already filtered in Prefetch
            ]

        return details

    @classmethod
    def get_user_submission_stats(
        cls,
        user: User,
        problem: Optional['Problem'] = None,
        course: Optional['Course'] = None
    ) -> Dict:
        """
        Get aggregated submission statistics for a user.

        Args:
            user: The user to get stats for
            problem: Optional problem to filter by
            course: Optional course to filter by

        Returns:
            Dictionary with submission statistics
        """
        from django.db.models import Count, Avg, Max, Q

        qs = Submission.objects.filter(user=user)

        if problem:
            qs = qs.filter(problem=problem)
        if course:
            qs = qs.filter(course=course)

        stats = qs.aggregate(
            total_submissions=Count('id'),
            best_score=Max('score'),
            avg_score=Avg('score'),
            completed_count=Count('id', filter=Q(completion_status='complete')),
            partial_count=Count('id', filter=Q(completion_status='partial')),
            eipl_count=Count('id', filter=Q(submission_type='eipl')),
            direct_code_count=Count('id', filter=Q(submission_type='direct_code'))
        )

        # Get hint usage stats
        hint_stats = HintActivation.objects.filter(
            submission__user=user
        )
        if problem:
            hint_stats = hint_stats.filter(submission__problem=problem)
        if course:
            hint_stats = hint_stats.filter(submission__course=course)

        hint_usage = hint_stats.values('hint__hint_type').annotate(
            usage_count=Count('id')
        )

        stats['hint_usage'] = {h['hint__hint_type']: h['usage_count'] for h in hint_usage}

        # Get segmentation stats for EiPL submissions
        seg_stats = SegmentationAnalysis.objects.filter(
            submission__user=user,
            submission__submission_type='eipl'
        )
        if problem:
            seg_stats = seg_stats.filter(submission__problem=problem)
        if course:
            seg_stats = seg_stats.filter(submission__course=course)

        comprehension_stats = seg_stats.values('comprehension_level').annotate(
            count=Count('id')
        )

        stats['comprehension'] = {c['comprehension_level']: c['count'] for c in comprehension_stats}

        return stats

    @staticmethod
    def _map_grade_to_completion_status(grade: str) -> str:
        """
        Map grade to legacy completion_status for backward compatibility.

        Args:
            grade: Grade string from GradingService ('complete', 'partial', 'incomplete')

        Returns:
            Completion status string for the submission model
        """
        if grade == 'complete':
            return 'complete'
        elif grade == 'partial':
            return 'partial'
        else:
            return 'incomplete'
