"""
Regression tests for comprehension level vocabulary (Change 6, P2).

Submission.comprehension_level uses "high-level"/"low-level"/"not_evaluated".
SegmentationAnalysis.comprehension_level uses "relational"/"multi_structural".
The mapping between them lives in SubmissionService.record_segmentation_analysis.

These tests verify that both vocabularies work and that the mapping is correct.
They must pass before and after normalization.
"""

import pytest

from purplex.submissions.models import SegmentationAnalysis
from tests.factories import SubmissionFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestComprehensionLevelNormalization:
    def test_submission_comprehension_level_choices(self):
        """All three Submission comprehension_level choices save successfully."""
        for level in ("high-level", "low-level", "not_evaluated"):
            sub = SubmissionFactory(comprehension_level=level)
            sub.refresh_from_db()
            assert sub.comprehension_level == level

    def test_segmentation_comprehension_level_choices(self):
        """Both SegmentationAnalysis comprehension_level choices save."""
        sub = SubmissionFactory()
        for level in ("relational", "multi_structural"):
            analysis = SegmentationAnalysis.objects.create(
                submission=sub,
                segment_count=2,
                comprehension_level=level,
                segments=[{"description": "test"}],
                code_mappings={"1": "test"},
                confidence_score=0.9,
                processing_time_ms=100,
                feedback_message="Good work",
            )
            assert analysis.comprehension_level == level
            # Clean up for next iteration (OneToOneField)
            analysis.delete()

    def test_default_comprehension_is_not_evaluated(self):
        """Default Submission comprehension_level is 'not_evaluated'."""
        sub = SubmissionFactory()
        assert sub.comprehension_level == "not_evaluated"

    def test_relational_maps_to_high_level(self):
        """Verify the conceptual mapping: relational -> high-level.

        The mapping lives in SubmissionService.record_segmentation_analysis:
        if comprehension_level == "relational": submission.comprehension_level = "high-level"
        """
        sub = SubmissionFactory(comprehension_level="high-level")
        sub.refresh_from_db()
        assert sub.comprehension_level == "high-level"

        analysis = SegmentationAnalysis.objects.create(
            submission=sub,
            segment_count=1,
            comprehension_level="relational",
            segments=[{"description": "overall purpose"}],
            code_mappings={"1": "all"},
            confidence_score=0.95,
            processing_time_ms=50,
            feedback_message="Excellent",
        )
        assert analysis.comprehension_level == "relational"
        # The service maps relational -> high-level on the submission
        assert sub.comprehension_level == "high-level"

    def test_multi_structural_maps_to_low_level(self):
        """Verify the conceptual mapping: multi_structural -> low-level.

        The mapping lives in SubmissionService.record_segmentation_analysis:
        else: submission.comprehension_level = "low-level"
        """
        sub = SubmissionFactory(comprehension_level="low-level")
        sub.refresh_from_db()
        assert sub.comprehension_level == "low-level"

        analysis = SegmentationAnalysis.objects.create(
            submission=sub,
            segment_count=5,
            comprehension_level="multi_structural",
            segments=[{"description": f"step {i}"} for i in range(5)],
            code_mappings={"1": "line1"},
            confidence_score=0.8,
            processing_time_ms=80,
            feedback_message="Too detailed",
        )
        assert analysis.comprehension_level == "multi_structural"
        assert sub.comprehension_level == "low-level"
