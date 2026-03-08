"""
Tests for slug collision handling (Change 8, P2).

Problem.save() already handles slug collisions with a counter loop.
ProblemSet, Course, and ProblemCategory do NOT — they'll get IntegrityError
on duplicate slugs.
"""

import pytest

from tests.factories import (
    CourseFactory,
    CourseInstructorFactory,
    EiplProblemFactory,
    ProblemCategoryFactory,
    ProblemSetFactory,
    UserFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestProblemSlugCollision:
    """Regression: Problem.save() already handles collisions."""

    def test_auto_slug_collision_appends_counter(self):
        p1 = EiplProblemFactory(title="Same Title", slug="")
        p2 = EiplProblemFactory(title="Same Title", slug="")
        assert p1.slug == "same-title"
        assert p2.slug == "same-title-1"
        assert p1.slug != p2.slug

    def test_three_way_collision(self):
        p1 = EiplProblemFactory(title="Collision Test", slug="")
        p2 = EiplProblemFactory(title="Collision Test", slug="")
        p3 = EiplProblemFactory(title="Collision Test", slug="")
        slugs = {p1.slug, p2.slug, p3.slug}
        assert len(slugs) == 3


class TestProblemSetSlugCollision:
    """Bug-proving: ProblemSet.save() does NOT handle slug collisions."""

    def test_duplicate_title_no_integrity_error(self):
        """After fix: two problem sets with the same title get distinct slugs."""
        ps1 = ProblemSetFactory(title="Duplicate PS Title", slug="")
        ps2 = ProblemSetFactory(title="Duplicate PS Title", slug="")
        assert ps1.slug != ps2.slug

    def test_explicit_slug_preserved(self):
        """Regression: explicit slug is not overwritten."""
        ps = ProblemSetFactory(title="Some Title", slug="custom-slug")
        assert ps.slug == "custom-slug"


class TestCourseSlugCollision:
    """Bug-proving: Course.save() does NOT handle slug collisions."""

    def test_duplicate_course_id_slug_collision(self):
        """After fix: two courses whose course_id slugifies identically get distinct slugs.

        Note: course_id is unique, but slug is derived from course_id via slugify().
        Two different course_ids can produce the same slug (e.g. 'CS 101' and 'CS-101').
        """
        c1 = CourseFactory(course_id="CS 101", slug="")
        CourseInstructorFactory(course=c1, user=UserFactory(), role="primary")
        c2 = CourseFactory(course_id="CS-101", slug="")
        CourseInstructorFactory(course=c2, user=UserFactory(), role="primary")
        assert c1.slug != c2.slug


class TestProblemCategorySlugCollision:
    """Bug-proving: ProblemCategory.save() does NOT handle slug collisions."""

    def test_duplicate_name_slug_collision(self):
        """After fix: two categories whose names slugify identically get distinct slugs.

        ProblemCategory.name is unique, but different names can produce the same slug
        (e.g. via Unicode normalization or special characters).
        Since name is unique, we test with names that are different strings but
        produce the same slug.
        """
        # "Loops & Arrays" and "Loops  Arrays" both slugify to "loops-arrays"
        # But name is unique=True, so we need different names that slugify the same
        c1 = ProblemCategoryFactory(name="Loops & Arrays", slug="")
        c2 = ProblemCategoryFactory(name="Loops - Arrays", slug="")
        # Both slugify to "loops-arrays"
        assert c1.slug != c2.slug
