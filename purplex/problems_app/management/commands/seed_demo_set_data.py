"""
Management command to seed the problem-demo-set course.

Creates 3 EiPL + 3 Prompt problems, test cases, hints,
a problem set, a new course, and links them together.

Designed for Paul Denny's graduate course demo at University of Auckland
starting 2026-04-20.

Idempotent: safe to run multiple times via get_or_create.
"""

from django.core.management.base import BaseCommand

from purplex.config.environment import config


class Command(BaseCommand):
    help = "Seeds the problem-demo-set course with 3 EiPL + 3 Prompt problems"

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
                    "Demo set seed data can only be created in "
                    "development environment.\n"
                    "Use --force to override this check."
                )
            )
            return

        if not config.is_development:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: Seeding demo set data in non-development environment!"
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
            EiplProblem,
            ProblemCategory,
            ProblemHint,
            ProblemSet,
            ProblemSetMembership,
            PromptProblem,
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
        cat_lists, created = ProblemCategory.objects.get_or_create(
            slug="lists",
            defaults={
                "name": "Lists",
                "description": "Problems focused on list processing in Python",
            },
        )
        self._report("ProblemCategory", "Lists", created)

        # ==================================================================
        # 2. EiPL Problems (easy, medium, hard)
        # ==================================================================

        # --- EiPL 1: Sum of Squares (easy) ---
        eipl_sum_sq, created = EiplProblem.objects.get_or_create(
            slug="demo-sum-of-squares",
            defaults={
                "title": "Code Reading A",
                "description": (
                    "Read the function below and explain what it does "
                    "in plain language."
                ),
                "function_signature": "def func_a(numbers: list[int]) -> int",
                "function_name": "func_a",
                "reference_solution": (
                    "def func_a(numbers):\n"
                    "    result = 0\n"
                    "    for n in numbers:\n"
                    "        result += n * n\n"
                    "    return result"
                ),
                "difficulty": "easy",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "demo-sum-of-squares", created)
        eipl_sum_sq.categories.add(cat_lists)

        # --- EiPL 2: Check if Sorted (medium) ---
        eipl_sorted, created = EiplProblem.objects.get_or_create(
            slug="demo-check-sorted",
            defaults={
                "title": "Code Reading B",
                "description": (
                    "Read the function below and explain what it does "
                    "in plain language."
                ),
                "function_signature": "def func_b(lst: list[int]) -> bool",
                "function_name": "func_b",
                "reference_solution": (
                    "def func_b(lst):\n"
                    "    for i in range(len(lst) - 1):\n"
                    "        if lst[i] > lst[i + 1]:\n"
                    "            return False\n"
                    "    return True"
                ),
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "demo-check-sorted", created)
        eipl_sorted.categories.add(cat_lists)

        # --- EiPL 3: Longest Consecutive Run (hard) ---
        eipl_run, created = EiplProblem.objects.get_or_create(
            slug="demo-longest-run",
            defaults={
                "title": "Code Reading C",
                "description": (
                    "Read the function below and explain what it does "
                    "in plain language."
                ),
                "function_signature": "def func_c(lst: list[int]) -> int",
                "function_name": "func_c",
                "reference_solution": (
                    "def func_c(lst):\n"
                    "    if not lst:\n"
                    "        return 0\n"
                    "    best = 1\n"
                    "    run = 1\n"
                    "    for i in range(1, len(lst)):\n"
                    "        if lst[i] == lst[i - 1]:\n"
                    "            run += 1\n"
                    "            if run > best:\n"
                    "                best = run\n"
                    "        else:\n"
                    "            run = 1\n"
                    "    return best"
                ),
                "difficulty": "advanced",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "demo-longest-run", created)
        eipl_run.categories.add(cat_lists)

        eipl_problems = [eipl_sum_sq, eipl_sorted, eipl_run]

        # ==================================================================
        # 3. Prompt Problems (function_table display mode)
        # ==================================================================

        # --- Prompt 1: Count Negatives (beginner) ---
        prompt_negatives, created = PromptProblem.objects.get_or_create(
            slug="demo-count-negatives",
            defaults={
                "title": "List I",
                "description": (
                    "Study the function call table below. "
                    "Explain what process_list does in plain language."
                ),
                "function_signature": "def process_list(lst: list[int]) -> int",
                "function_name": "process_list",
                "reference_solution": (
                    "def process_list(lst):\n"
                    "    count = 0\n"
                    "    for x in lst:\n"
                    "        if x < 0:\n"
                    "            count += 1\n"
                    "    return count"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {
                            "args": [[13, -2, -53, 32, -23, -1, 0]],
                            "return_value": 4,
                        },
                        {"args": [[1, 2, 3, 4, 5]], "return_value": 0},
                        {"args": [[-1, -2, -3]], "return_value": 3},
                    ],
                },
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "demo-count-negatives", created)
        prompt_negatives.categories.add(cat_lists)

        # --- Prompt 2: Count Fixed Points (intermediate) ---
        prompt_fixed, created = PromptProblem.objects.get_or_create(
            slug="demo-count-fixed-points",
            defaults={
                "title": "List III",
                "description": (
                    "Study the function call table below. "
                    "Explain what process_list does in plain language."
                ),
                "function_signature": "def process_list(lst: list[int]) -> int",
                "function_name": "process_list",
                "reference_solution": (
                    "def process_list(lst):\n"
                    "    count = 0\n"
                    "    for i in range(len(lst)):\n"
                    "        if lst[i] == i:\n"
                    "            count += 1\n"
                    "    return count"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {"args": [[0, 1, 2, 3]], "return_value": 4},
                        {"args": [[1, 0, 3, 2]], "return_value": 0},
                        {"args": [[0, 5, 2, 7]], "return_value": 2},
                    ],
                },
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "demo-count-fixed-points", created)
        prompt_fixed.categories.add(cat_lists)

        # --- Prompt 3: Sort Sublist (intermediate) ---
        prompt_sort_sub, created = PromptProblem.objects.get_or_create(
            slug="demo-sort-sublist",
            defaults={
                "title": "List IV",
                "description": (
                    "Study the function call table below. "
                    "Explain what process_list does in plain language."
                ),
                "function_signature": (
                    "def process_list(lst: list[int], start: int, end: int) "
                    "-> list[int]"
                ),
                "function_name": "process_list",
                "reference_solution": (
                    "def process_list(lst, start, end):\n"
                    "    result = lst[:]\n"
                    "    result[start:end + 1] = sorted(result[start:end + 1])\n"
                    "    return result"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {
                            "args": [[7, 9, 3, 6, 1], 1, 3],
                            "return_value": [7, 3, 6, 9, 1],
                        },
                        {
                            "args": [[4, 3, 2, 2, 1], 1, 4],
                            "return_value": [4, 1, 2, 2, 3],
                        },
                        {
                            "args": [[3, 7, 1], 0, 2],
                            "return_value": [1, 3, 7],
                        },
                    ],
                },
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "demo-sort-sublist", created)
        prompt_sort_sub.categories.add(cat_lists)

        prompt_problems = [prompt_negatives, prompt_fixed, prompt_sort_sub]
        all_problems = eipl_problems + prompt_problems

        # ==================================================================
        # 4. Test Cases
        # ==================================================================

        test_case_data = {
            eipl_sum_sq: [
                {
                    "inputs": [[1, 2, 3]],
                    "expected_output": 14,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_a([1, 2, 3]) = 14",
                },
                {
                    "inputs": [[0, 5]],
                    "expected_output": 25,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_a([0, 5]) = 25",
                },
                {
                    "inputs": [[]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_a([]) = 0",
                },
                {
                    "inputs": [[-2, 3]],
                    "expected_output": 13,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_a([-2, 3]) = 13",
                },
            ],
            eipl_sorted: [
                {
                    "inputs": [[1, 2, 3, 4]],
                    "expected_output": True,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_b([1, 2, 3, 4]) = True",
                },
                {
                    "inputs": [[3, 1, 2]],
                    "expected_output": False,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_b([3, 1, 2]) = False",
                },
                {
                    "inputs": [[1]],
                    "expected_output": True,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_b([1]) = True",
                },
                {
                    "inputs": [[1, 1, 2]],
                    "expected_output": True,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_b([1, 1, 2]) = True",
                },
            ],
            eipl_run: [
                {
                    "inputs": [[1, 1, 2, 2, 2, 3]],
                    "expected_output": 3,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_c([1, 1, 2, 2, 2, 3]) = 3",
                },
                {
                    "inputs": [[1, 2, 3]],
                    "expected_output": 1,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_c([1, 2, 3]) = 1",
                },
                {
                    "inputs": [[5, 5, 5, 5]],
                    "expected_output": 4,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_c([5, 5, 5, 5]) = 4",
                },
                {
                    "inputs": [[]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_c([]) = 0",
                },
            ],
            prompt_negatives: [
                {
                    "inputs": [[13, -2, -53, 32, -23, -1, 0]],
                    "expected_output": 4,
                    "is_sample": True,
                    "order": 0,
                    "description": "process_list([13, -2, -53, 32, -23, -1, 0]) = 4",
                },
                {
                    "inputs": [[1, 2, 3, 4, 5]],
                    "expected_output": 0,
                    "is_sample": True,
                    "order": 1,
                    "description": "process_list([1, 2, 3, 4, 5]) = 0",
                },
                {
                    "inputs": [[-1, -2, -3]],
                    "expected_output": 3,
                    "is_sample": False,
                    "order": 2,
                    "description": "process_list([-1, -2, -3]) = 3",
                },
                {
                    "inputs": [[0]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 3,
                    "description": "process_list([0]) = 0",
                },
            ],
            prompt_fixed: [
                {
                    "inputs": [[0, 1, 2, 3]],
                    "expected_output": 4,
                    "is_sample": True,
                    "order": 0,
                    "description": "process_list([0, 1, 2, 3]) = 4",
                },
                {
                    "inputs": [[1, 0, 3, 2]],
                    "expected_output": 0,
                    "is_sample": True,
                    "order": 1,
                    "description": "process_list([1, 0, 3, 2]) = 0",
                },
                {
                    "inputs": [[0, 5, 2, 7]],
                    "expected_output": 2,
                    "is_sample": False,
                    "order": 2,
                    "description": "process_list([0, 5, 2, 7]) = 2",
                },
                {
                    "inputs": [[3, 3, 3, 3]],
                    "expected_output": 1,
                    "is_sample": False,
                    "order": 3,
                    "description": "process_list([3, 3, 3, 3]) = 1",
                },
            ],
            prompt_sort_sub: [
                {
                    "inputs": [[7, 9, 3, 6, 1], 1, 3],
                    "expected_output": [7, 3, 6, 9, 1],
                    "is_sample": True,
                    "order": 0,
                    "description": "process_list([7,9,3,6,1], 1, 3) = [7,3,6,9,1]",
                },
                {
                    "inputs": [[4, 3, 2, 2, 1], 1, 4],
                    "expected_output": [4, 1, 2, 2, 3],
                    "is_sample": True,
                    "order": 1,
                    "description": "process_list([4,3,2,2,1], 1, 4) = [4,1,2,2,3]",
                },
                {
                    "inputs": [[3, 7, 1], 0, 2],
                    "expected_output": [1, 3, 7],
                    "is_sample": False,
                    "order": 2,
                    "description": "process_list([3,7,1], 0, 2) = [1,3,7]",
                },
                {
                    "inputs": [[5, 2, 8, 1], 0, 1],
                    "expected_output": [2, 5, 8, 1],
                    "is_sample": False,
                    "order": 3,
                    "description": "process_list([5,2,8,1], 0, 1) = [2,5,8,1]",
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
        # 5. Hints (all 3 types for each EiPL problem)
        # ==================================================================

        hint_data = {
            eipl_sum_sq: {
                "variable_fade": {
                    "mappings": [
                        {"from": "result", "to": "running total"},
                        {"from": "n", "to": "current element"},
                    ]
                },
                "subgoal_highlight": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 1,
                            "title": "Initialize",
                            "explanation": "Start a running total at zero.",
                        },
                        {
                            "line_start": 2,
                            "line_end": 3,
                            "title": "Accumulate squares",
                            "explanation": (
                                "Walk through each element, square it, "
                                "and add it to the running total."
                            ),
                        },
                        {
                            "line_start": 4,
                            "line_end": 4,
                            "title": "Return result",
                            "explanation": "Return the accumulated total.",
                        },
                    ]
                },
                "suggested_trace": {
                    "suggested_call": "func_a([1, 2, 3])",
                },
            },
            eipl_sorted: {
                "variable_fade": {
                    "mappings": [
                        {"from": "i", "to": "current position"},
                        {"from": "lst[i]", "to": "current element"},
                        {"from": "lst[i + 1]", "to": "next element"},
                    ]
                },
                "subgoal_highlight": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 3,
                            "title": "Check adjacent pairs",
                            "explanation": (
                                "Walk through each pair of neighboring elements. "
                                "If any pair is out of order, stop and report it."
                            ),
                        },
                        {
                            "line_start": 4,
                            "line_end": 4,
                            "title": "Return default",
                            "explanation": (
                                "If no out-of-order pair was found, "
                                "report that everything is in order."
                            ),
                        },
                    ]
                },
                "suggested_trace": {
                    "suggested_call": "func_b([1, 3, 2])",
                },
            },
            eipl_run: {
                "variable_fade": {
                    "mappings": [
                        {"from": "best", "to": "longest run found so far"},
                        {"from": "run", "to": "current run length"},
                        {"from": "i", "to": "current position"},
                    ]
                },
                "subgoal_highlight": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 2,
                            "title": "Handle empty input",
                            "explanation": (
                                "If the list is empty, there are no runs."
                            ),
                        },
                        {
                            "line_start": 3,
                            "line_end": 4,
                            "title": "Initialize counters",
                            "explanation": (
                                "The minimum run length for a non-empty list "
                                "is 1 (the first element by itself)."
                            ),
                        },
                        {
                            "line_start": 5,
                            "line_end": 11,
                            "title": "Scan and track runs",
                            "explanation": (
                                "Walk through the list comparing each element "
                                "to the previous. Extend the current run when "
                                "they match; reset it when they differ. Track "
                                "the longest run seen."
                            ),
                        },
                        {
                            "line_start": 12,
                            "line_end": 12,
                            "title": "Return result",
                            "explanation": "Return the longest run length.",
                        },
                    ]
                },
                "suggested_trace": {
                    "suggested_call": "func_c([1, 1, 2, 2, 2, 3])",
                },
            },
        }

        hint_count = 0
        for problem, hints in hint_data.items():
            for hint_type, content in hints.items():
                _, created = ProblemHint.objects.get_or_create(
                    problem=problem,
                    hint_type=hint_type,
                    defaults={
                        "is_enabled": True,
                        "min_attempts": 2,
                        "content": content,
                    },
                )
                if created:
                    hint_count += 1
                self._report(
                    "ProblemHint",
                    f"{hint_type} for {problem.slug}",
                    created,
                )

        # ==================================================================
        # 6. Problem Set
        # ==================================================================
        ps_demo, created = ProblemSet.objects.get_or_create(
            slug="demo-problems",
            defaults={
                "title": "Demo Problems",
                "description": (
                    "A mix of EiPL (explain the code) and Prompt (explain from "
                    "input-output examples) problems covering list processing."
                ),
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "demo-problems", created)

        for idx, problem in enumerate(all_problems):
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_demo,
                problem=problem,
                defaults={"order": idx},
            )
            self._report("ProblemSetMembership", problem.slug, created)

        # ==================================================================
        # 7. Course
        # ==================================================================
        course, created = Course.all_objects.get_or_create(
            course_id="problem-demo-set",
            defaults={
                "name": "Prompt Programming Demo",
                "description": (
                    "Demo course for exploring EiPL and Prompt problem types "
                    "with list processing exercises."
                ),
                "is_active": True,
                "enrollment_open": True,
            },
        )
        self._report("Course", "problem-demo-set", created)

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
            f"{instructor.username} -> problem-demo-set",
            created,
        )

        # Link problem set to course — due 2026-04-27 (one week after demo)
        due_date = timezone.make_aware(datetime(2026, 4, 27, 23, 59, 59))
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
        self._report("CourseProblemSet", "demo-problems -> problem-demo-set", created)

        # ==================================================================
        # Summary
        # ==================================================================
        self.stdout.write(
            self.style.SUCCESS(
                "\nDemo set seed data ready!\n"
                f"  Category: 1 (Lists)\n"
                f"  EiPL problems: {len(eipl_problems)}\n"
                f"  Prompt problems: {len(prompt_problems)}\n"
                f"  Test cases: {tc_count} new\n"
                f"  Hints: {hint_count} new\n"
                f"  Problem set: demo-problems ({len(all_problems)} problems)\n"
                f"  Course: problem-demo-set\n"
                f"  Due date: 2026-04-27 23:59:59"
            )
        )

    def _report(self, model_name: str, identifier: str, created: bool):
        """Print whether an object was created or already existed."""
        if created:
            self.stdout.write(f"  Created {model_name}: {identifier}")
        else:
            self.stdout.write(f"  Skipped {model_name}: {identifier} (already exists)")
