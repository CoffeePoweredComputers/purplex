"""
Management command to seed the Question Types Sampler course.

Creates one problem of each of four question types, a category, a problem
set, a course, and links them together:

  - EiPL          (EiplProblem)         : read code, explain it in plain language
  - Prompt        (PromptProblem)       : infer behavior from a function-call table
  - Probeable Code(ProbeableCodeProblem): probe a hidden oracle, then write code
  - Refute        (RefuteProblem)       : find an input that disproves a claim

All four target beginner Python (integers and lists) so the course works as
a quick showcase of the platform's question modalities.

Notes:
  - Probing the Probeable Code problem tracks state in Redis, so Redis must be
    running to probe. Grading (EiPL, Prompt, Probeable Code) runs student /
    generated code in Docker. Refute grades deterministically via a predicate
    and needs neither.
  - EiPL/Prompt turn a natural-language explanation into code via an
    OpenAI-compatible API (OPENAI_API_KEY / OPENAI_BASE_URL) at grade time.

Idempotent: safe to run multiple times via get_or_create.
"""

from django.core.management.base import BaseCommand

from purplex.config.environment import config


class Command(BaseCommand):
    help = (
        "Seeds the Question Types Sampler course with one EiPL, one Prompt, "
        "one Probeable Code, and one Refute problem"
    )

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
                    "Sampler seed data can only be created in "
                    "development environment.\n"
                    "Use --force to override this check."
                )
            )
            return

        if not config.is_development:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: Seeding sampler data in non-development environment!"
                )
            )

        from django.contrib.auth.models import User

        from purplex.problems_app.models import (
            Course,
            CourseInstructor,
            CourseInstructorRole,
            CourseProblemSet,
            EiplProblem,
            ProbeableCodeProblem,
            ProblemCategory,
            ProblemSet,
            ProblemSetMembership,
            PromptProblem,
            RefuteProblem,
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
                    "Create the user first (e.g. `python manage.py create_test_users`) "
                    "or pass --instructor <username>."
                )
            )
            return

        # ------------------------------------------------------------------
        # 1. Category
        # ------------------------------------------------------------------
        cat_sampler, created = ProblemCategory.objects.get_or_create(
            slug="sampler",
            defaults={
                "name": "Sampler",
                "description": (
                    "One problem of each question type, for a quick tour of the "
                    "platform's question modalities."
                ),
            },
        )
        self._report("ProblemCategory", "Sampler", created)

        # ==================================================================
        # 2. EiPL problem (read code -> explain in plain language)
        # ==================================================================
        eipl, created = EiplProblem.objects.get_or_create(
            slug="sampler-eipl-sum-evens",
            defaults={
                "title": "EiPL: Explain the Even-Number Sum",
                "description": (
                    "Read the function below and explain, in plain language, "
                    "what it computes. Your explanation will be turned into code "
                    "and tested."
                ),
                "function_signature": "def sum_evens(numbers: list[int]) -> int",
                "function_name": "sum_evens",
                "reference_solution": (
                    "def sum_evens(numbers):\n"
                    "    total = 0\n"
                    "    for n in numbers:\n"
                    "        if n % 2 == 0:\n"
                    "            total += n\n"
                    "    return total"
                ),
                # Prompt segmentation analysis: few-shot examples that teach the
                # grader what a high-level (relational) vs. line-by-line
                # (multi-structural) explanation of sum_evens looks like. Segment
                # text must be a verbatim substring of its example prompt, and
                # code_lines are 1-indexed with no overlap across segments.
                "segmentation_config": {
                    "enabled": True,
                    "threshold": 2,
                    "examples": {
                        "relational": {
                            "prompt": (
                                "Adds up all the even numbers in the list and "
                                "returns the total."
                            ),
                            "segments": [
                                "Adds up all the even numbers in the list and "
                                "returns the total."
                            ],
                            "code_lines": [[1, 2, 3, 4, 5, 6]],
                        },
                        "multi_structural": {
                            "prompt": (
                                "Starts a total at zero. Loops over each number "
                                "in the list. Checks if the number is even. If it "
                                "is even, adds it to the total. Finally returns "
                                "the total."
                            ),
                            "segments": [
                                "Starts a total at zero.",
                                "Loops over each number in the list.",
                                "Checks if the number is even.",
                                "If it is even, adds it to the total.",
                                "Finally returns the total.",
                            ],
                            "code_lines": [[2], [3], [4], [5], [6]],
                        },
                    },
                },
                "segmentation_threshold": 2,
                "requires_highlevel_comprehension": True,
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "sampler-eipl-sum-evens", created)
        eipl.categories.add(cat_sampler)

        # ==================================================================
        # 3. Prompt problem (infer behavior from a function-call table)
        # ==================================================================
        prompt, created = PromptProblem.objects.get_or_create(
            slug="sampler-prompt-count-positives",
            defaults={
                "title": "Prompt: Read the Function Call Table",
                "description": (
                    "Study the function call table below. Explain, in plain "
                    "language, what process_list does. You never see the code - "
                    "infer the rule from the examples."
                ),
                "function_signature": "def process_list(lst: list[int]) -> int",
                "function_name": "process_list",
                "reference_solution": (
                    "def process_list(lst):\n"
                    "    count = 0\n"
                    "    for x in lst:\n"
                    "        if x > 0:\n"
                    "            count += 1\n"
                    "    return count"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {"args": [[3, -1, 4, 0, -5]], "return_value": 2},
                        {"args": [[1, 2, 3]], "return_value": 3},
                        {"args": [[-2, -7, 0]], "return_value": 0},
                        {"args": [[]], "return_value": 0},
                    ],
                },
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "sampler-prompt-count-positives", created)
        prompt.categories.add(cat_sampler)

        # ==================================================================
        # 4. Probeable Code problem (probe hidden oracle -> write code)
        # ==================================================================
        probeable, created = ProbeableCodeProblem.objects.get_or_create(
            slug="sampler-probeable-code-divide",
            defaults={
                "title": "Probe & Code: Integer Divide",
                "description": (
                    "Implement a function that divides two numbers: `divide(a, b)` "
                    "returns `a` divided by `b`. Sounds simple — but the exact "
                    "behavior has edge cases the description does not spell out. "
                    "Probe the hidden function with your own inputs to discover how "
                    "it handles the tricky cases (What happens when you divide by "
                    "zero? Does it round, and which way?), then write code that "
                    "reproduces it exactly."
                ),
                "function_signature": "def divide(a: int, b: int) -> int",
                "function_name": "divide",
                "reference_solution": (
                    "def divide(a, b):\n"
                    "    if b == 0:\n"
                    "        return 0\n"
                    "    return a // b"
                ),
                "show_function_signature": True,
                "probe_mode": "explore",
                "max_probes": 10,
                "cooldown_attempts": 3,
                "cooldown_refill": 5,
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report(
            "ProbeableCodeProblem", "sampler-probeable-code-divide", created
        )
        probeable.categories.add(cat_sampler)

        # ==================================================================
        # 5. Refute problem (find an input that disproves a claim)
        # ==================================================================
        refute, created = RefuteProblem.objects.get_or_create(
            slug="sampler-refute-abs-positive",
            defaults={
                "title": "Refute: Is abs_val Always Positive?",
                "description": (
                    "The claim below is false. Find one integer input for which "
                    "it does not hold."
                ),
                "question_text": (
                    "Claim: for every integer x, abs_val(x) returns a positive "
                    "number. Enter an integer x that disproves this."
                ),
                "grading_mode": "deterministic",
                "claim_text": (
                    "For every integer x, abs_val(x) returns a positive number."
                ),
                # True while the claim holds; a counterexample makes this False.
                "claim_predicate": "result > 0",
                "function_signature": "def abs_val(x: int) -> int",
                "reference_solution": (
                    "def abs_val(x):\n    if x >= 0:\n        return x\n    return -x"
                ),
                # x=0 -> abs_val(0) == 0, which is not > 0 (0 is not positive).
                "expected_counterexample": {"x": 0},
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("RefuteProblem", "sampler-refute-abs-positive", created)
        refute.categories.add(cat_sampler)

        # Order matters for display: EiPL, Prompt, Probeable, Refute.
        all_problems = [eipl, prompt, probeable, refute]

        # ==================================================================
        # 6. Test Cases (Refute grades via predicate, so it needs none)
        # ==================================================================
        test_case_data = {
            eipl: [
                {
                    "inputs": [[1, 2, 3, 4]],
                    "expected_output": 6,
                    "is_sample": True,
                    "order": 0,
                    "description": "sum_evens([1, 2, 3, 4]) = 6",
                },
                {
                    "inputs": [[2, 4, 6]],
                    "expected_output": 12,
                    "is_sample": True,
                    "order": 1,
                    "description": "sum_evens([2, 4, 6]) = 12",
                },
                {
                    "inputs": [[1, 3, 5]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 2,
                    "description": "sum_evens([1, 3, 5]) = 0",
                },
                {
                    "inputs": [[]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 3,
                    "description": "sum_evens([]) = 0",
                },
            ],
            prompt: [
                {
                    "inputs": [[3, -1, 4, 0, -5]],
                    "expected_output": 2,
                    "is_sample": True,
                    "order": 0,
                    "description": "process_list([3, -1, 4, 0, -5]) = 2",
                },
                {
                    "inputs": [[1, 2, 3]],
                    "expected_output": 3,
                    "is_sample": True,
                    "order": 1,
                    "description": "process_list([1, 2, 3]) = 3",
                },
                {
                    "inputs": [[-2, -7, 0]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 2,
                    "description": "process_list([-2, -7, 0]) = 0",
                },
                {
                    "inputs": [[]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 3,
                    "description": "process_list([]) = 0",
                },
            ],
            probeable: [
                {
                    "inputs": [6, 2],
                    "expected_output": 3,
                    "is_sample": True,
                    "order": 0,
                    "description": "divide(6, 2) = 3 (clean division)",
                },
                {
                    "inputs": [20, 4],
                    "expected_output": 5,
                    "is_sample": True,
                    "order": 1,
                    "description": "divide(20, 4) = 5 (clean division)",
                },
                {
                    "inputs": [7, 2],
                    "expected_output": 3,
                    "is_sample": False,
                    "order": 2,
                    "description": "divide(7, 2) = 3 (edge: floor division, not 3.5)",
                },
                {
                    "inputs": [-7, 2],
                    "expected_output": -4,
                    "is_sample": False,
                    "order": 3,
                    "description": (
                        "divide(-7, 2) = -4 (edge: floor rounds toward negative "
                        "infinity)"
                    ),
                },
                {
                    "inputs": [5, 0],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 4,
                    "description": "divide(5, 0) = 0 (edge: divide by zero returns 0)",
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
        # 7. Problem Set
        # ==================================================================
        ps_sampler, created = ProblemSet.objects.get_or_create(
            slug="question-types-sampler",
            defaults={
                "title": "Question Types Sampler",
                "description": (
                    "One problem of each type: Explain in Plain Language, Prompt, "
                    "Probeable Code, and Refute."
                ),
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "question-types-sampler", created)

        for idx, problem in enumerate(all_problems):
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_sampler,
                problem=problem,
                defaults={"order": idx},
            )
            self._report("ProblemSetMembership", problem.slug, created)

        # ==================================================================
        # 8. Course
        # ==================================================================
        course, created = Course.all_objects.get_or_create(
            course_id="SAMPLER-2026",
            defaults={
                "name": "Question Types Sampler",
                "description": (
                    "A demo course with one example of each question type: "
                    "EiPL (explain code), Prompt (read a call table), Probeable "
                    "Code (probe then code), and Refute (find a counterexample)."
                ),
                "is_active": True,
                "enrollment_open": True,
            },
        )
        self._report("Course", "SAMPLER-2026", created)

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
            self._report("Course", "SAMPLER-2026 (revived soft-deleted)", True)

        # Add instructor to course as primary.
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
            f"{instructor.username} -> SAMPLER-2026",
            created,
        )

        # Link problem set to course (no deadline for a sampler).
        _, created = CourseProblemSet.objects.update_or_create(
            course=course,
            problem_set=ps_sampler,
            defaults={
                "order": 1,
                "deadline_type": "none",
                "is_required": True,
            },
        )
        self._report(
            "CourseProblemSet", "SAMPLER-2026 -> question-types-sampler", created
        )

        # ==================================================================
        # Summary
        # ==================================================================
        self.stdout.write(
            self.style.SUCCESS(
                "\nQuestion Types Sampler seed data ready!\n"
                "  Category: 1 (Sampler)\n"
                "  Problems: 4 (EiPL, Prompt, Probeable Code, Refute)\n"
                f"  Test cases: {tc_count} new\n"
                "  Problem set: question-types-sampler (4 problems)\n"
                "  Course: SAMPLER-2026\n"
                "\nNote: probing needs Redis; EiPL/Prompt need an "
                "OpenAI-compatible API to grade explanations."
            )
        )

    def _report(self, model_name: str, identifier: str, created: bool):
        """Print whether an object was created or already existed."""
        if created:
            self.stdout.write(f"  Created {model_name}: {identifier}")
        else:
            self.stdout.write(f"  Skipped {model_name}: {identifier} (already exists)")
