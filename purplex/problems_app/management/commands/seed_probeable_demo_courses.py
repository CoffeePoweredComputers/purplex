"""
Management command to seed the probeable-demo course.

Creates one ProbeableCodeProblem + one ProbeableSpecProblem (the two
"probeable" problem types), their test cases, a problem set, a course,
and links them together.

Both problem types let the student discover a hidden function's behavior
by probing an oracle (the reference_solution) with inputs:
  - Probeable Code: probe, then WRITE CODE implementing the behavior.
  - Probeable Spec: probe, then EXPLAIN the behavior in plain language
    (the EiPL pipeline turns the explanation into code).

The two problems intentionally use different probe modes ("explore" and
"cooldown") so the demo exercises both mechanics.

Notes:
  - Probe state is tracked in Redis, so Redis must be running to probe.
  - The Probeable Spec problem needs an OpenAI-compatible API
    (OPENAI_API_KEY / OPENAI_BASE_URL) to grade the explanation. Probing
    and the Probeable Code problem work without it.

Idempotent: safe to run multiple times via get_or_create.
"""

from django.core.management.base import BaseCommand

from purplex.config.environment import config


class Command(BaseCommand):
    help = "Seeds the probeable-demo course with one Probeable Code + one Probeable Spec problem"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation even in non-development environment",
        )
        parser.add_argument(
            "--instructor",
            default="instructor",
            help="Username of the instructor who owns the problems",
        )

    def handle(self, *args, **options):
        if not config.is_development and not options["force"]:
            self.stdout.write(
                self.style.ERROR(
                    "Probeable demo seed data can only be created in "
                    "development environment.\n"
                    "Use --force to override this check."
                )
            )
            return

        if not config.is_development:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: Seeding probeable demo data in non-development "
                    "environment!"
                )
            )

        from datetime import datetime

        from django.contrib.auth.models import User
        from django.utils import timezone

        from purplex.problems_app.models import (
            Course,
            CourseInstructor,
            CourseInstructorRole,
            CourseProblemSet,
            ProbeableCodeProblem,
            ProbeableSpecProblem,
            ProblemCategory,
            ProblemSet,
            ProblemSetMembership,
            TestCase,
        )

        # ------------------------------------------------------------------
        # Look up instructor
        # ------------------------------------------------------------------
        try:
            instructor = User.objects.get(username=options["instructor"])
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"User '{options['instructor']}' not found. "
                    "Create the user first or pass --instructor <username>."
                )
            )
            return

        # ------------------------------------------------------------------
        # 1. Category
        # ------------------------------------------------------------------
        cat_probeable, created = ProblemCategory.objects.get_or_create(
            slug="probeable",
            defaults={
                "name": "Probeable",
                "description": (
                    "Problems where you discover a hidden function's behavior "
                    "by probing it with inputs."
                ),
            },
        )
        self._report("ProblemCategory", "Probeable", created)

        # ==================================================================
        # 2. Probeable Code problem (probe -> write code)
        # ==================================================================
        probe_code, created = ProbeableCodeProblem.objects.get_or_create(
            slug="demo-probeable-code-transform",
            defaults={
                "title": "Probe & Code: Mystery Transform",
                "description": (
                    "A hidden function `transform` takes a list of integers and "
                    "returns a new list. You can't see its body. Probe it with "
                    "inputs of your choice to discover what it does, then write "
                    "code that reproduces the same behavior."
                ),
                "function_signature": "def transform(lst: list[int]) -> list[int]",
                "function_name": "transform",
                "reference_solution": (
                    "def transform(lst):\n    return [x * 2 for x in lst if x > 0]"
                ),
                "show_function_signature": True,
                "probe_mode": "explore",
                "max_probes": 10,
                "cooldown_attempts": 3,
                "cooldown_refill": 5,
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("ProbeableCodeProblem", "demo-probeable-code-transform", created)
        probe_code.categories.add(cat_probeable)

        # ==================================================================
        # 3. Probeable Spec problem (probe -> explain in plain language)
        # ==================================================================
        probe_spec, created = ProbeableSpecProblem.objects.get_or_create(
            slug="demo-probeable-spec-classify",
            defaults={
                "title": "Probe & Explain: Mystery Classify",
                "description": (
                    "A hidden function `classify` takes a single integer and "
                    "returns a string. Probe it with inputs of your choice to "
                    "discover the rule, then explain in plain language what it "
                    "does. Your explanation is turned into code and tested."
                ),
                "function_signature": "def classify(n: int) -> str",
                "function_name": "classify",
                "reference_solution": (
                    "def classify(n):\n"
                    "    if n % 15 == 0:\n"
                    "        return 'fizzbuzz'\n"
                    "    if n % 3 == 0:\n"
                    "        return 'fizz'\n"
                    "    if n % 5 == 0:\n"
                    "        return 'buzz'\n"
                    "    return str(n)"
                ),
                "show_function_signature": True,
                "probe_mode": "cooldown",
                "max_probes": 10,
                "cooldown_attempts": 3,
                "cooldown_refill": 5,
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("ProbeableSpecProblem", "demo-probeable-spec-classify", created)
        probe_spec.categories.add(cat_probeable)

        all_problems = [probe_code, probe_spec]

        # ==================================================================
        # 4. Test Cases
        # ==================================================================
        test_case_data = {
            probe_code: [
                {
                    "inputs": [[1, -2, 3]],
                    "expected_output": [2, 6],
                    "is_sample": True,
                    "order": 0,
                    "description": "transform([1, -2, 3]) = [2, 6]",
                },
                {
                    "inputs": [[-5, -1]],
                    "expected_output": [],
                    "is_sample": True,
                    "order": 1,
                    "description": "transform([-5, -1]) = []",
                },
                {
                    "inputs": [[0, 2, -3, 5]],
                    "expected_output": [4, 10],
                    "is_sample": False,
                    "order": 2,
                    "description": "transform([0, 2, -3, 5]) = [4, 10]",
                },
                {
                    "inputs": [[]],
                    "expected_output": [],
                    "is_sample": False,
                    "order": 3,
                    "description": "transform([]) = []",
                },
            ],
            probe_spec: [
                {
                    "inputs": [15],
                    "expected_output": "fizzbuzz",
                    "is_sample": True,
                    "order": 0,
                    "description": "classify(15) = 'fizzbuzz'",
                },
                {
                    "inputs": [9],
                    "expected_output": "fizz",
                    "is_sample": True,
                    "order": 1,
                    "description": "classify(9) = 'fizz'",
                },
                {
                    "inputs": [10],
                    "expected_output": "buzz",
                    "is_sample": True,
                    "order": 2,
                    "description": "classify(10) = 'buzz'",
                },
                {
                    "inputs": [7],
                    "expected_output": "7",
                    "is_sample": False,
                    "order": 3,
                    "description": "classify(7) = '7'",
                },
                {
                    "inputs": [30],
                    "expected_output": "fizzbuzz",
                    "is_sample": False,
                    "order": 4,
                    "description": "classify(30) = 'fizzbuzz'",
                },
            ],
        }

        tc_count = 0
        for problem, cases in test_case_data.items():
            for tc in cases:
                _, created = TestCase.objects.get_or_create(
                    problem=problem,
                    inputs=tc["inputs"],
                    expected_output=tc["expected_output"],
                    defaults={
                        "is_sample": tc["is_sample"],
                        "is_hidden": not tc["is_sample"],
                        "order": tc["order"],
                        "description": tc["description"],
                    },
                )
                if created:
                    tc_count += 1
                self._report("TestCase", tc["description"], created)

        # ==================================================================
        # 5. Problem Set
        # ==================================================================
        ps_demo, created = ProblemSet.objects.get_or_create(
            slug="probeable-demo",
            defaults={
                "title": "Probeable Problems",
                "description": (
                    "Discover a hidden function by probing it with inputs, then "
                    "either write the code (Probeable Code) or explain it in "
                    "plain language (Probeable Spec)."
                ),
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "probeable-demo", created)

        for idx, problem in enumerate(all_problems):
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_demo,
                problem=problem,
                defaults={"order": idx},
            )
            self._report("ProblemSetMembership", problem.slug, created)

        # ==================================================================
        # 6. Course
        # ==================================================================
        course, created = Course.all_objects.get_or_create(
            course_id="probeable-demo",
            defaults={
                "name": "Probeable Problems Demo",
                "description": (
                    "Demo course showcasing the two probeable problem types: "
                    "Probeable Code (probe then write code) and Probeable Spec "
                    "(probe then explain in plain language)."
                ),
                "is_active": True,
                "enrollment_open": True,
            },
        )
        self._report("Course", "probeable-demo", created)

        # Revive the course if a previous run left it soft-deleted.
        if not created and course.is_deleted:
            course.is_deleted = False
            course.deleted_at = None
            course.is_active = True
            course.enrollment_open = True
            course.save(
                update_fields=[
                    "is_deleted",
                    "deleted_at",
                    "is_active",
                    "enrollment_open",
                ]
            )
            self._report("Course", "probeable-demo (revived soft-deleted)", True)

        # Add instructor to course
        _, created = CourseInstructor.objects.get_or_create(
            course=course,
            user=instructor,
            defaults={
                "role": CourseInstructorRole.PRIMARY,
                "added_by": instructor,
            },
        )
        self._report(
            "CourseInstructor",
            f"{instructor.username} -> probeable-demo",
            created,
        )

        # Link problem set to course — due one week out (soft deadline).
        due_date = timezone.make_aware(datetime(2026, 6, 23, 23, 59, 59))
        _, created = CourseProblemSet.objects.update_or_create(
            course=course,
            problem_set=ps_demo,
            defaults={
                "order": 1,
                "due_date": due_date,
                "deadline_type": "soft",
                "is_required": True,
            },
        )
        self._report("CourseProblemSet", "probeable-demo -> probeable-demo", created)

        # ==================================================================
        # Summary
        # ==================================================================
        self.stdout.write(
            self.style.SUCCESS(
                "\nProbeable demo seed data ready!\n"
                f"  Category: 1 (Probeable)\n"
                f"  Probeable Code problems: 1 (explore mode)\n"
                f"  Probeable Spec problems: 1 (cooldown mode)\n"
                f"  Test cases: {tc_count} new\n"
                f"  Problem set: probeable-demo ({len(all_problems)} problems)\n"
                f"  Course: probeable-demo\n"
                f"  Due date: 2026-06-23 23:59:59\n"
                "\nNote: probing needs Redis; the Probeable Spec problem needs "
                "an OpenAI-compatible API to grade explanations."
            )
        )

    def _report(self, model_name: str, identifier: str, created: bool):
        """Print whether an object was created or already existed."""
        if created:
            self.stdout.write(f"  Created {model_name}: {identifier}")
        else:
            self.stdout.write(f"  Skipped {model_name}: {identifier} (already exists)")
