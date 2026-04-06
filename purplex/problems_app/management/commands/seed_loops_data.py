"""
Management command to seed a Python Loops problem set.

Creates 8 loop-focused problems (4 EiPL + 4 Prompt), test cases, hints,
a problem set, a new course, and links them together.

Idempotent: safe to run multiple times via get_or_create.
"""

from django.core.management.base import BaseCommand

from purplex.config.environment import config


class Command(BaseCommand):
    help = "Seeds a Python Loops problem set with 4 EiPL + 4 Prompt problems"

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
                    "Loops seed data can only be created in development environment.\n"
                    "Use --force to override this check (not recommended)."
                )
            )
            return

        if not config.is_development:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: Seeding loops data in non-development environment!"
                )
            )

        from datetime import timedelta

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
        cat_loops, created = ProblemCategory.objects.get_or_create(
            slug="loops",
            defaults={
                "name": "Loops",
                "description": "Problems focused on for-loops and while-loops in Python",
            },
        )
        self._report("ProblemCategory", "Loops", created)

        # ==================================================================
        # 2. EiPL Problems
        # ==================================================================

        # --- EiPL 1: Count Even Numbers ---
        eipl_count_evens, created = EiplProblem.objects.get_or_create(
            slug="loops-count-evens",
            defaults={
                "title": "Code Reading E",
                "description": (
                    "Read the function below and explain what it does "
                    "in plain language."
                ),
                "function_signature": "def func_e(numbers: list[int]) -> int",
                "function_name": "func_e",
                "reference_solution": (
                    "def func_e(numbers):\n"
                    "    count = 0\n"
                    "    for n in numbers:\n"
                    "        if n % 2 == 0:\n"
                    "            count += 1\n"
                    "    return count"
                ),
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "loops-count-evens", created)
        eipl_count_evens.categories.add(cat_loops)

        # --- EiPL 2: Find the Maximum ---
        eipl_find_max, created = EiplProblem.objects.get_or_create(
            slug="loops-find-max",
            defaults={
                "title": "Code Reading F",
                "description": (
                    "Read the function below and explain what it does "
                    "in plain language."
                ),
                "function_signature": "def func_f(numbers: list[int]) -> int",
                "function_name": "func_f",
                "reference_solution": (
                    "def func_f(numbers):\n"
                    "    biggest = numbers[0]\n"
                    "    for n in numbers:\n"
                    "        if n > biggest:\n"
                    "            biggest = n\n"
                    "    return biggest"
                ),
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "loops-find-max", created)
        eipl_find_max.categories.add(cat_loops)

        # --- EiPL 3: Reverse a String ---
        eipl_reverse, created = EiplProblem.objects.get_or_create(
            slug="loops-reverse-string",
            defaults={
                "title": "Code Reading G",
                "description": (
                    "Read the function below and explain what it does "
                    "in plain language."
                ),
                "function_signature": "def func_g(text: str) -> str",
                "function_name": "func_g",
                "reference_solution": (
                    "def func_g(text):\n"
                    '    result = ""\n'
                    "    for char in text:\n"
                    "        result = char + result\n"
                    "    return result"
                ),
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "loops-reverse-string", created)
        eipl_reverse.categories.add(cat_loops)

        # --- EiPL 4: Sum Until Negative ---
        eipl_sum_neg, created = EiplProblem.objects.get_or_create(
            slug="loops-sum-until-negative",
            defaults={
                "title": "Code Reading H",
                "description": (
                    "Read the function below and explain what it does "
                    "in plain language."
                ),
                "function_signature": ("def func_h(numbers: list[int]) -> int"),
                "function_name": "func_h",
                "reference_solution": (
                    "def func_h(numbers):\n"
                    "    total = 0\n"
                    "    i = 0\n"
                    "    while i < len(numbers) and numbers[i] >= 0:\n"
                    "        total += numbers[i]\n"
                    "        i += 1\n"
                    "    return total"
                ),
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "loops-sum-until-negative", created)
        eipl_sum_neg.categories.add(cat_loops)

        eipl_problems = [eipl_count_evens, eipl_find_max, eipl_reverse, eipl_sum_neg]

        # ==================================================================
        # 3. Prompt Problems
        # ==================================================================

        # --- Prompt 1: Mystery Function A (power) ---
        prompt_power, created = PromptProblem.objects.get_or_create(
            slug="loops-power",
            defaults={
                "title": "Mystery Function A",
                "description": (
                    "Study the input-output examples in the table below. "
                    "Explain what func_a does in plain language."
                ),
                "function_signature": "def func_a(x: int, y: int) -> int",
                "function_name": "func_a",
                "reference_solution": (
                    "def func_a(x, y):\n"
                    "    result = 1\n"
                    "    for i in range(y):\n"
                    "        result *= x\n"
                    "    return result"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {"args": [2, 3], "return_value": 8},
                        {"args": [5, 0], "return_value": 1},
                        {"args": [3, 2], "return_value": 9},
                        {"args": [10, 1], "return_value": 10},
                    ],
                },
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "loops-power", created)
        prompt_power.categories.add(cat_loops)

        # --- Prompt 2: Mystery Function B (countdown) ---
        prompt_countdown, created = PromptProblem.objects.get_or_create(
            slug="loops-countdown",
            defaults={
                "title": "Mystery Function B",
                "description": (
                    "Study the input-output examples in the table below. "
                    "Explain what func_b does in plain language."
                ),
                "function_signature": "def func_b(n: int) -> list[int]",
                "function_name": "func_b",
                "reference_solution": (
                    "def func_b(n):\n"
                    "    result = []\n"
                    "    while n > 0:\n"
                    "        result.append(n)\n"
                    "        n -= 1\n"
                    "    return result"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {"args": [5], "return_value": [5, 4, 3, 2, 1]},
                        {"args": [1], "return_value": [1]},
                        {"args": [0], "return_value": []},
                        {"args": [3], "return_value": [3, 2, 1]},
                    ],
                },
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "loops-countdown", created)
        prompt_countdown.categories.add(cat_loops)

        # --- Prompt 3: Mystery Function C (remove duplicates) ---
        prompt_dedup, created = PromptProblem.objects.get_or_create(
            slug="loops-remove-duplicates",
            defaults={
                "title": "Mystery Function C",
                "description": (
                    "Study the input-output examples in the table below. "
                    "Explain what func_c does in plain language."
                ),
                "function_signature": ("def func_c(items: list[int]) -> list[int]"),
                "function_name": "func_c",
                "reference_solution": (
                    "def func_c(items):\n"
                    "    seen = []\n"
                    "    result = []\n"
                    "    for item in items:\n"
                    "        if item not in seen:\n"
                    "            seen.append(item)\n"
                    "            result.append(item)\n"
                    "    return result"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {"args": [[1, 2, 2, 3, 3, 3]], "return_value": [1, 2, 3]},
                        {"args": [[1, 1, 1]], "return_value": [1]},
                        {"args": [[]], "return_value": []},
                        {"args": [[5, 3, 5, 3, 1]], "return_value": [5, 3, 1]},
                    ],
                },
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "loops-remove-duplicates", created)
        prompt_dedup.categories.add(cat_loops)

        # --- Prompt 4: Mystery Function D (fizzbuzz count) ---
        prompt_fizzbuzz, created = PromptProblem.objects.get_or_create(
            slug="loops-fizzbuzz-count",
            defaults={
                "title": "Mystery Function D",
                "description": (
                    "Study the input-output examples in the table below. "
                    "Explain what func_d does in plain language."
                ),
                "function_signature": "def func_d(n: int) -> int",
                "function_name": "func_d",
                "reference_solution": (
                    "def func_d(n):\n"
                    "    count = 0\n"
                    "    for i in range(1, n + 1):\n"
                    "        if i % 3 == 0 and i % 5 == 0:\n"
                    "            count += 1\n"
                    "    return count"
                ),
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {"args": [15], "return_value": 1},
                        {"args": [30], "return_value": 2},
                        {"args": [1], "return_value": 0},
                        {"args": [45], "return_value": 3},
                    ],
                },
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "loops-fizzbuzz-count", created)
        prompt_fizzbuzz.categories.add(cat_loops)

        prompt_problems = [
            prompt_power,
            prompt_countdown,
            prompt_dedup,
            prompt_fizzbuzz,
        ]
        all_problems = eipl_problems + prompt_problems

        # ==================================================================
        # 4. Test Cases
        # ==================================================================

        test_case_data = {
            eipl_count_evens: [
                {
                    "inputs": [[1, 2, 3, 4]],
                    "expected_output": 2,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_e([1, 2, 3, 4]) = 2",
                },
                {
                    "inputs": [[2, 4, 6]],
                    "expected_output": 3,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_e([2, 4, 6]) = 3",
                },
                {
                    "inputs": [[]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_e([]) = 0",
                },
                {
                    "inputs": [[1, 3, 5]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_e([1, 3, 5]) = 0",
                },
            ],
            eipl_find_max: [
                {
                    "inputs": [[3, 1, 4, 1, 5]],
                    "expected_output": 5,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_f([3, 1, 4, 1, 5]) = 5",
                },
                {
                    "inputs": [[1]],
                    "expected_output": 1,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_f([1]) = 1",
                },
                {
                    "inputs": [[-3, -1, -4]],
                    "expected_output": -1,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_f([-3, -1, -4]) = -1",
                },
                {
                    "inputs": [[7, 7, 7]],
                    "expected_output": 7,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_f([7, 7, 7]) = 7",
                },
            ],
            eipl_reverse: [
                {
                    "inputs": ["hello"],
                    "expected_output": "olleh",
                    "is_sample": True,
                    "order": 0,
                    "description": 'func_g("hello") = "olleh"',
                },
                {
                    "inputs": ["a"],
                    "expected_output": "a",
                    "is_sample": True,
                    "order": 1,
                    "description": 'func_g("a") = "a"',
                },
                {
                    "inputs": [""],
                    "expected_output": "",
                    "is_sample": False,
                    "order": 2,
                    "description": 'func_g("") = ""',
                },
                {
                    "inputs": ["ab"],
                    "expected_output": "ba",
                    "is_sample": False,
                    "order": 3,
                    "description": 'func_g("ab") = "ba"',
                },
            ],
            eipl_sum_neg: [
                {
                    "inputs": [[1, 2, 3, -1, 5]],
                    "expected_output": 6,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_h([1, 2, 3, -1, 5]) = 6",
                },
                {
                    "inputs": [[-1, 2, 3]],
                    "expected_output": 0,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_h([-1, 2, 3]) = 0",
                },
                {
                    "inputs": [[1, 2, 3]],
                    "expected_output": 6,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_h([1, 2, 3]) = 6",
                },
                {
                    "inputs": [[]],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_h([]) = 0",
                },
            ],
            prompt_power: [
                {
                    "inputs": [2, 3],
                    "expected_output": 8,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_a(2, 3) = 8",
                },
                {
                    "inputs": [5, 0],
                    "expected_output": 1,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_a(5, 0) = 1",
                },
                {
                    "inputs": [3, 2],
                    "expected_output": 9,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_a(3, 2) = 9",
                },
                {
                    "inputs": [10, 1],
                    "expected_output": 10,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_a(10, 1) = 10",
                },
            ],
            prompt_countdown: [
                {
                    "inputs": [5],
                    "expected_output": [5, 4, 3, 2, 1],
                    "is_sample": True,
                    "order": 0,
                    "description": "func_b(5) = [5, 4, 3, 2, 1]",
                },
                {
                    "inputs": [1],
                    "expected_output": [1],
                    "is_sample": True,
                    "order": 1,
                    "description": "func_b(1) = [1]",
                },
                {
                    "inputs": [0],
                    "expected_output": [],
                    "is_sample": False,
                    "order": 2,
                    "description": "func_b(0) = []",
                },
                {
                    "inputs": [3],
                    "expected_output": [3, 2, 1],
                    "is_sample": False,
                    "order": 3,
                    "description": "func_b(3) = [3, 2, 1]",
                },
            ],
            prompt_dedup: [
                {
                    "inputs": [[1, 2, 2, 3, 3, 3]],
                    "expected_output": [1, 2, 3],
                    "is_sample": True,
                    "order": 0,
                    "description": "func_c([1, 2, 2, 3, 3, 3]) = [1, 2, 3]",
                },
                {
                    "inputs": [[1, 1, 1]],
                    "expected_output": [1],
                    "is_sample": True,
                    "order": 1,
                    "description": "func_c([1, 1, 1]) = [1]",
                },
                {
                    "inputs": [[]],
                    "expected_output": [],
                    "is_sample": False,
                    "order": 2,
                    "description": "func_c([]) = []",
                },
                {
                    "inputs": [[5, 3, 5, 3, 1]],
                    "expected_output": [5, 3, 1],
                    "is_sample": False,
                    "order": 3,
                    "description": "func_c([5, 3, 5, 3, 1]) = [5, 3, 1]",
                },
            ],
            prompt_fizzbuzz: [
                {
                    "inputs": [15],
                    "expected_output": 1,
                    "is_sample": True,
                    "order": 0,
                    "description": "func_d(15) = 1",
                },
                {
                    "inputs": [30],
                    "expected_output": 2,
                    "is_sample": True,
                    "order": 1,
                    "description": "func_d(30) = 2",
                },
                {
                    "inputs": [1],
                    "expected_output": 0,
                    "is_sample": False,
                    "order": 2,
                    "description": "func_d(1) = 0",
                },
                {
                    "inputs": [45],
                    "expected_output": 3,
                    "is_sample": False,
                    "order": 3,
                    "description": "func_d(45) = 3",
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
            eipl_count_evens: {
                "variable_fade": {
                    "mappings": [
                        {"from": "count", "to": "running tally"},
                        {"from": "n", "to": "current element"},
                    ]
                },
                "subgoal_highlight": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 1,
                            "title": "Initialize",
                            "explanation": "Start a counter at zero.",
                        },
                        {
                            "line_start": 2,
                            "line_end": 4,
                            "title": "Loop and check",
                            "explanation": (
                                "Walk through each element and conditionally "
                                "increment the counter."
                            ),
                        },
                        {
                            "line_start": 5,
                            "line_end": 5,
                            "title": "Return result",
                            "explanation": "Return the final count.",
                        },
                    ]
                },
                "suggested_trace": {
                    "suggested_call": "func_e([1, 2, 3, 4])",
                },
            },
            eipl_find_max: {
                "variable_fade": {
                    "mappings": [
                        {"from": "biggest", "to": "best candidate so far"},
                        {"from": "n", "to": "current element"},
                    ]
                },
                "subgoal_highlight": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 1,
                            "title": "Initialize",
                            "explanation": (
                                "Pick the first element as the starting candidate."
                            ),
                        },
                        {
                            "line_start": 2,
                            "line_end": 4,
                            "title": "Scan and compare",
                            "explanation": (
                                "Walk through each element; if it beats "
                                "the current candidate, replace it."
                            ),
                        },
                        {
                            "line_start": 5,
                            "line_end": 5,
                            "title": "Return result",
                            "explanation": "Return the winning candidate.",
                        },
                    ]
                },
                "suggested_trace": {
                    "suggested_call": "func_f([3, 1, 4, 1, 5])",
                },
            },
            eipl_reverse: {
                "variable_fade": {
                    "mappings": [
                        {"from": "result", "to": "output built so far"},
                        {"from": "char", "to": "current character"},
                    ]
                },
                "subgoal_highlight": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 1,
                            "title": "Initialize",
                            "explanation": "Start with an empty string.",
                        },
                        {
                            "line_start": 2,
                            "line_end": 3,
                            "title": "Build reversed string",
                            "explanation": (
                                "For each character, prepend it to the front "
                                "of the result so the order is flipped."
                            ),
                        },
                        {
                            "line_start": 4,
                            "line_end": 4,
                            "title": "Return result",
                            "explanation": "Return the reversed string.",
                        },
                    ]
                },
                "suggested_trace": {
                    "suggested_call": 'func_g("hello")',
                },
            },
            eipl_sum_neg: {
                "variable_fade": {
                    "mappings": [
                        {"from": "total", "to": "accumulated value"},
                        {"from": "i", "to": "current position"},
                    ]
                },
                "subgoal_highlight": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 2,
                            "title": "Initialize",
                            "explanation": (
                                "Set the sum to zero and start at the first position."
                            ),
                        },
                        {
                            "line_start": 3,
                            "line_end": 5,
                            "title": "Accumulate while non-negative",
                            "explanation": (
                                "Keep adding numbers to the sum as long as "
                                "we haven't gone past the end and the current "
                                "number is not negative."
                            ),
                        },
                        {
                            "line_start": 6,
                            "line_end": 6,
                            "title": "Return result",
                            "explanation": "Return the accumulated sum.",
                        },
                    ]
                },
                "suggested_trace": {
                    "suggested_call": "func_h([1, 2, 3, -1, 5])",
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
        ps_loops, created = ProblemSet.objects.get_or_create(
            slug="python-loops",
            defaults={
                "title": "Python Loops",
                "description": (
                    "Practice reading and understanding for-loops and "
                    "while-loops in Python. Includes EiPL (explain the code) "
                    "and Prompt (explain from an image) problems."
                ),
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "python-loops", created)

        for idx, problem in enumerate(all_problems):
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_loops,
                problem=problem,
                defaults={"order": idx},
            )
            self._report("ProblemSetMembership", problem.slug, created)

        # ==================================================================
        # 7. Course
        # ==================================================================
        course, created = Course.all_objects.get_or_create(
            course_id="loops-2026",
            defaults={
                "name": "Python Loops Fundamentals",
                "description": (
                    "A focused course on understanding iteration in Python "
                    "through for-loops and while-loops."
                ),
                "is_active": True,
                "enrollment_open": True,
            },
        )
        self._report("Course", "loops-2026", created)

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
            "CourseInstructor", f"{instructor.username} -> loops-2026", created
        )

        # Link problem set to course
        now = timezone.now()
        _, created = CourseProblemSet.objects.update_or_create(
            course=course,
            problem_set=ps_loops,
            defaults={
                "order": 1,
                "due_date": now + timedelta(days=30),
                "deadline_type": "soft",
                "is_required": True,
            },
        )
        self._report("CourseProblemSet", "python-loops -> loops-2026", created)

        # ==================================================================
        # Summary
        # ==================================================================
        self.stdout.write(
            self.style.SUCCESS(
                "\nPython Loops seed data ready!\n"
                f"  Category: 1 (Loops)\n"
                f"  EiPL problems: {len(eipl_problems)}\n"
                f"  Prompt problems: {len(prompt_problems)}\n"
                f"  Test cases: {tc_count} new\n"
                f"  Hints: {hint_count} new\n"
                f"  Problem set: python-loops ({len(all_problems)} problems)\n"
                f"  Course: loops-2026"
            )
        )

    def _report(self, model_name: str, identifier: str, created: bool):
        """Print whether an object was created or already existed."""
        if created:
            self.stdout.write(f"  Created {model_name}: {identifier}")
        else:
            self.stdout.write(f"  Skipped {model_name}: {identifier} (already exists)")
