"""
Management command to seed E2E test data for Playwright tests.

Runs AFTER create_test_users, which creates users and the CS101-2024 course.
Creates problems, problem sets, test cases, hints, and progress data
needed for comprehensive E2E testing.

Idempotent: safe to run multiple times via get_or_create.
"""

from django.core.management.base import BaseCommand

from purplex.config.environment import config


class Command(BaseCommand):
    help = (
        "Seeds E2E test data (problems, problem sets, hints, etc.) for Playwright tests"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation even in non-development environment",
        )

    def handle(self, *args, **options):
        if not config.is_development and not options["force"]:
            self.stdout.write(
                self.style.ERROR(
                    "E2E seed data can only be created in development environment.\n"
                    "Use --force to override this check (not recommended)."
                )
            )
            return

        if not config.is_development:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: Seeding E2E data in non-development environment!"
                )
            )

        # Import models inside handle to avoid import issues at module load time
        from datetime import timedelta

        from django.contrib.auth.models import User
        from django.utils import timezone

        from purplex.problems_app.models import (
            Course,
            CourseProblemSet,
            DebugFixProblem,
            EiplProblem,
            McqProblem,
            ProbeableCodeProblem,
            ProbeableSpecProblem,
            ProblemCategory,
            ProblemHint,
            ProblemSet,
            ProblemSetMembership,
            PromptProblem,
            RefuteProblem,
            TestCase,
            UserProgress,
        )
        from purplex.submissions.models import Submission
        from purplex.users_app.models import (
            ConsentMethod,
            ConsentType,
            UserConsent,
        )

        # ------------------------------------------------------------------
        # Look up prerequisite objects created by create_test_users
        # ------------------------------------------------------------------
        try:
            instructor = User.objects.get(username="instructor")
            student = User.objects.get(username="student")
            admin = User.objects.get(username="admin")
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "Required test users not found. Run create_test_users first."
                )
            )
            raise

        try:
            course = Course.all_objects.get(course_id="CS101-2024")
        except Course.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "CS101-2024 course not found. Run create_test_users first."
                )
            )
            raise

        # ------------------------------------------------------------------
        # 1. Categories
        # ------------------------------------------------------------------
        cat_arrays, created = ProblemCategory.objects.get_or_create(
            slug="arrays",
            defaults={"name": "Arrays", "description": "Array manipulation problems"},
        )
        self._report("ProblemCategory", "Arrays", created)

        cat_loops, created = ProblemCategory.objects.get_or_create(
            slug="loops",
            defaults={"name": "Loops", "description": "Loop-based problems"},
        )
        self._report("ProblemCategory", "Loops", created)

        # ------------------------------------------------------------------
        # 2. Problems (one per type, deterministic slugs)
        # ------------------------------------------------------------------
        mcq, created = McqProblem.objects.get_or_create(
            slug="e2e-mcq-1",
            defaults={
                "title": "E2E: What is a variable?",
                "question_text": (
                    "Which of the following best describes a variable in Python?"
                ),
                "options": [
                    {
                        "id": "a",
                        "text": "A named storage location in memory",
                        "is_correct": True,
                        "explanation": "Correct! A variable stores a value.",
                    },
                    {
                        "id": "b",
                        "text": "A type of loop",
                        "is_correct": False,
                        "explanation": "A loop is a control flow structure.",
                    },
                    {
                        "id": "c",
                        "text": "A built-in function",
                        "is_correct": False,
                        "explanation": "Functions are callable objects.",
                    },
                    {
                        "id": "d",
                        "text": "A comment in code",
                        "is_correct": False,
                        "explanation": "Comments are ignored by the interpreter.",
                    },
                ],
                "allow_multiple": False,
                "grading_mode": "deterministic",
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("McqProblem", "e2e-mcq-1", created)
        mcq.categories.add(cat_arrays, cat_loops)

        eipl, created = EiplProblem.objects.get_or_create(
            slug="e2e-eipl-1",
            defaults={
                "title": "E2E: Sum of List",
                "description": "Explain what this function does in plain language.",
                "function_signature": "def sum_list(numbers: list[int]) -> int",
                "function_name": "sum_list",
                "reference_solution": (
                    "def sum_list(numbers):\n"
                    "    total = 0\n"
                    "    for n in numbers:\n"
                    "        total += n\n"
                    "    return total"
                ),
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("EiplProblem", "e2e-eipl-1", created)
        eipl.categories.add(cat_arrays, cat_loops)

        prompt, created = PromptProblem.objects.get_or_create(
            slug="e2e-prompt-1",
            defaults={
                "title": "E2E: Describe the Algorithm",
                "description": "Look at the image and describe the algorithm shown.",
                "function_signature": "def algorithm() -> str",
                "function_name": "algorithm",
                "reference_solution": 'def algorithm():\n    return "sorted"',
                "image_url": "https://example.com/e2e-algorithm.png",
                "image_alt_text": "A flowchart showing a sorting algorithm",
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "e2e-prompt-1", created)
        prompt.categories.add(cat_arrays)

        prompt_terminal, created = PromptProblem.objects.get_or_create(
            slug="e2e-prompt-terminal-1",
            defaults={
                "title": "E2E: Describe the Program Output",
                "description": "Look at the terminal interaction and describe what the program does.",
                "function_signature": "def square(x: int) -> int",
                "function_name": "square",
                "reference_solution": "def square(x):\n    return x ** 2",
                "display_mode": "terminal",
                "display_data": {
                    "schema_version": 1,
                    "runs": [
                        {
                            "label": "Run 1",
                            "interactions": [
                                {"type": "output", "text": "Enter a number: "},
                                {"type": "input", "text": "5"},
                                {"type": "output", "text": "The square is: 25"},
                            ],
                        },
                        {
                            "label": "Run 2",
                            "interactions": [
                                {"type": "output", "text": "Enter a number: "},
                                {"type": "input", "text": "-3"},
                                {"type": "output", "text": "The square is: 9"},
                            ],
                        },
                    ],
                },
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "e2e-prompt-terminal-1", created)
        prompt_terminal.categories.add(cat_arrays)

        prompt_table, created = PromptProblem.objects.get_or_create(
            slug="e2e-prompt-table-1",
            defaults={
                "title": "E2E: Describe the Function",
                "description": "Look at the function call table and describe what the function does.",
                "function_signature": "def add(a: int, b: int) -> int",
                "function_name": "add",
                "reference_solution": "def add(a, b):\n    return a + b",
                "display_mode": "function_table",
                "display_data": {
                    "schema_version": 1,
                    "calls": [
                        {"args": [2, 3], "return_value": 5},
                        {"args": [0, 0], "return_value": 0},
                        {"args": [-1, 1], "return_value": 0},
                        {"args": [10, 20], "return_value": 30},
                    ],
                },
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("PromptProblem", "e2e-prompt-table-1", created)
        prompt_table.categories.add(cat_arrays)

        debugfix, created = DebugFixProblem.objects.get_or_create(
            slug="e2e-debugfix-1",
            defaults={
                "title": "E2E: Fix the Loop",
                "description": "The function should sum numbers from 1 to n, but it has a bug.",
                "function_signature": "def sum_to_n(n: int) -> int",
                "function_name": "sum_to_n",
                "reference_solution": (
                    "def sum_to_n(n):\n"
                    "    total = 0\n"
                    "    for i in range(1, n + 1):\n"
                    "        total += i\n"
                    "    return total"
                ),
                "buggy_code": (
                    "def sum_to_n(n):\n"
                    "    total = 0\n"
                    "    for i in range(1, n):  # Bug: should be n + 1\n"
                    "        total += i\n"
                    "    return total"
                ),
                "bug_hints": [
                    {"level": 1, "text": "Check the range boundaries"},
                    {"level": 2, "text": "range(1, n) excludes n itself"},
                ],
                "difficulty": "beginner",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("DebugFixProblem", "e2e-debugfix-1", created)
        debugfix.categories.add(cat_loops)

        probeable_code, created = ProbeableCodeProblem.objects.get_or_create(
            slug="e2e-probeable-code-1",
            defaults={
                "title": "E2E: Probe the Function",
                "description": "Discover what this function does by probing it with inputs.",
                "function_signature": "def mystery(lst: list[int]) -> list[int]",
                "function_name": "mystery",
                "reference_solution": ("def mystery(lst):\n    return sorted(lst)"),
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
        self._report("ProbeableCodeProblem", "e2e-probeable-code-1", created)
        probeable_code.categories.add(cat_arrays)

        probeable_spec, created = ProbeableSpecProblem.objects.get_or_create(
            slug="e2e-probeable-spec-1",
            defaults={
                "title": "E2E: Probe the Spec",
                "description": "Discover the function behavior, then explain it in plain language.",
                "function_signature": "def discover(x: int) -> int",
                "function_name": "discover",
                "reference_solution": "def discover(x):\n    return x ** 2",
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
        self._report("ProbeableSpecProblem", "e2e-probeable-spec-1", created)
        probeable_spec.categories.add(cat_loops)

        refute, created = RefuteProblem.objects.get_or_create(
            slug="e2e-refute-1",
            defaults={
                "title": "E2E: Find Counterexample",
                "question_text": "Find an input that disproves the claim below.",
                "claim_text": "The function always returns a positive number",
                "claim_predicate": "result > 0",
                "reference_solution": "def f(x):\n    return x * 2",
                "function_signature": "def f(x: int) -> int",
                "expected_counterexample": {"x": -5},
                "grading_mode": "deterministic",
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": instructor,
            },
        )
        self._report("RefuteProblem", "e2e-refute-1", created)
        refute.categories.add(cat_arrays)

        all_problems = [
            mcq,
            eipl,
            prompt,
            debugfix,
            probeable_code,
            probeable_spec,
            refute,
        ]

        # ------------------------------------------------------------------
        # 2b. Additional problems created by admin (ensures admin list >10)
        # ------------------------------------------------------------------
        admin_mcq, created = McqProblem.objects.get_or_create(
            slug="e2e-admin-mcq-1",
            defaults={
                "title": "E2E Admin: Data Types",
                "question_text": "Which of the following is an immutable data type in Python?",
                "options": [
                    {
                        "id": "a",
                        "text": "list",
                        "is_correct": False,
                        "explanation": "Lists are mutable.",
                    },
                    {
                        "id": "b",
                        "text": "dict",
                        "is_correct": False,
                        "explanation": "Dicts are mutable.",
                    },
                    {
                        "id": "c",
                        "text": "tuple",
                        "is_correct": True,
                        "explanation": "Correct! Tuples are immutable.",
                    },
                    {
                        "id": "d",
                        "text": "set",
                        "is_correct": False,
                        "explanation": "Sets are mutable.",
                    },
                ],
                "allow_multiple": False,
                "grading_mode": "deterministic",
                "difficulty": "beginner",
                "is_active": True,
                "created_by": admin,
            },
        )
        self._report("McqProblem", "e2e-admin-mcq-1", created)
        admin_mcq.categories.add(cat_arrays)

        admin_eipl, created = EiplProblem.objects.get_or_create(
            slug="e2e-admin-eipl-1",
            defaults={
                "title": "E2E Admin: Max of List",
                "description": "Explain what this function does in plain language.",
                "function_signature": "def max_list(numbers: list[int]) -> int",
                "function_name": "max_list",
                "reference_solution": (
                    "def max_list(numbers):\n"
                    "    result = numbers[0]\n"
                    "    for n in numbers:\n"
                    "        if n > result:\n"
                    "            result = n\n"
                    "    return result"
                ),
                "difficulty": "beginner",
                "is_active": True,
                "created_by": admin,
            },
        )
        self._report("EiplProblem", "e2e-admin-eipl-1", created)
        admin_eipl.categories.add(cat_arrays)

        admin_debugfix, created = DebugFixProblem.objects.get_or_create(
            slug="e2e-admin-debugfix-1",
            defaults={
                "title": "E2E Admin: Fix Factorial",
                "description": "The function should compute n!, but has a bug.",
                "function_signature": "def factorial(n: int) -> int",
                "function_name": "factorial",
                "reference_solution": (
                    "def factorial(n):\n"
                    "    if n <= 1:\n"
                    "        return 1\n"
                    "    return n * factorial(n - 1)"
                ),
                "buggy_code": (
                    "def factorial(n):\n"
                    "    if n <= 1:\n"
                    "        return 0\n"
                    "    return n * factorial(n - 1)"
                ),
                "bug_hints": [
                    {"level": 1, "text": "Check the base case return value"},
                ],
                "difficulty": "beginner",
                "is_active": True,
                "created_by": admin,
            },
        )
        self._report("DebugFixProblem", "e2e-admin-debugfix-1", created)
        admin_debugfix.categories.add(cat_loops)

        admin_prompt, created = PromptProblem.objects.get_or_create(
            slug="e2e-admin-prompt-1",
            defaults={
                "title": "E2E Admin: Describe the Pattern",
                "description": "Describe the pattern shown in the image.",
                "function_signature": "def pattern() -> str",
                "function_name": "pattern",
                "reference_solution": 'def pattern():\n    return "fibonacci"',
                "image_url": "https://example.com/e2e-pattern.png",
                "image_alt_text": "A diagram showing a number pattern",
                "difficulty": "intermediate",
                "is_active": True,
                "created_by": admin,
            },
        )
        self._report("PromptProblem", "e2e-admin-prompt-1", created)
        admin_prompt.categories.add(cat_arrays)

        admin_problems = [admin_mcq, admin_eipl, admin_debugfix, admin_prompt]
        all_problems.extend(admin_problems)

        # ------------------------------------------------------------------
        # 3. Test Cases (for executable types)
        # ------------------------------------------------------------------
        # EiPL test cases
        eipl_cases = [
            {
                "inputs": [[1, 2, 3]],
                "expected_output": 6,
                "is_sample": True,
                "order": 0,
            },
            {
                "inputs": [[10, 20]],
                "expected_output": 30,
                "is_sample": True,
                "order": 1,
            },
            {"inputs": [[]], "expected_output": 0, "is_sample": False, "order": 2},
        ]
        for tc_data in eipl_cases:
            _, created = TestCase.objects.get_or_create(
                problem=eipl,
                inputs=tc_data["inputs"],
                expected_output=tc_data["expected_output"],
                defaults={
                    "is_sample": tc_data["is_sample"],
                    "is_hidden": not tc_data["is_sample"],
                    "order": tc_data["order"],
                    "description": f"sum_list({tc_data['inputs'][0]}) = {tc_data['expected_output']}",
                },
            )
            self._report("TestCase (eipl)", f"inputs={tc_data['inputs']}", created)

        # DebugFix test cases
        debugfix_cases = [
            {"inputs": [5], "expected_output": 15, "is_sample": True, "order": 0},
            {"inputs": [1], "expected_output": 1, "is_sample": False, "order": 1},
        ]
        for tc_data in debugfix_cases:
            _, created = TestCase.objects.get_or_create(
                problem=debugfix,
                inputs=tc_data["inputs"],
                expected_output=tc_data["expected_output"],
                defaults={
                    "is_sample": tc_data["is_sample"],
                    "is_hidden": not tc_data["is_sample"],
                    "order": tc_data["order"],
                    "description": f"sum_to_n({tc_data['inputs'][0]}) = {tc_data['expected_output']}",
                },
            )
            self._report("TestCase (debugfix)", f"inputs={tc_data['inputs']}", created)

        # ProbeableCode test cases
        pc_cases = [
            {
                "inputs": [[3, 1, 2]],
                "expected_output": [1, 2, 3],
                "is_sample": True,
                "order": 0,
            },
        ]
        for tc_data in pc_cases:
            _, created = TestCase.objects.get_or_create(
                problem=probeable_code,
                inputs=tc_data["inputs"],
                expected_output=tc_data["expected_output"],
                defaults={
                    "is_sample": tc_data["is_sample"],
                    "is_hidden": False,
                    "order": tc_data["order"],
                    "description": f"mystery({tc_data['inputs'][0]}) = {tc_data['expected_output']}",
                },
            )
            self._report(
                "TestCase (probeable_code)", f"inputs={tc_data['inputs']}", created
            )

        # ------------------------------------------------------------------
        # 4. Problem Sets
        # ------------------------------------------------------------------
        ps_basics, created = ProblemSet.objects.get_or_create(
            slug="e2e-basics",
            defaults={
                "title": "E2E Basics",
                "description": "Basic problems for E2E testing",
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "e2e-basics", created)

        ps_code, created = ProblemSet.objects.get_or_create(
            slug="e2e-code",
            defaults={
                "title": "E2E Code Challenges",
                "description": "Code challenge problems for E2E testing",
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "e2e-code", created)

        ps_mixed, created = ProblemSet.objects.get_or_create(
            slug="e2e-mixed",
            defaults={
                "title": "E2E Mixed Set",
                "description": "Mixed problem types for E2E testing",
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "e2e-mixed", created)

        # ProblemSetMembership: e2e-basics -> mcq, eipl
        basics_members = [(mcq, 0), (eipl, 1)]
        for problem, order in basics_members:
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_basics,
                problem=problem,
                defaults={"order": order},
            )
            self._report("ProblemSetMembership (basics)", problem.slug, created)

        # ProblemSetMembership: e2e-code -> debugfix, probeable_code
        code_members = [(debugfix, 0), (probeable_code, 1)]
        for problem, order in code_members:
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_code,
                problem=problem,
                defaults={"order": order},
            )
            self._report("ProblemSetMembership (code)", problem.slug, created)

        # ProblemSetMembership: e2e-mixed -> all problems
        for idx, problem in enumerate(all_problems):
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_mixed,
                problem=problem,
                defaults={"order": idx},
            )
            self._report("ProblemSetMembership (mixed)", problem.slug, created)

        # Unassigned problem sets (NOT linked to CS101-2024)
        # These provide the "available to add" items for course management tests.
        ps_admin_set, created = ProblemSet.objects.get_or_create(
            slug="e2e-admin-set",
            defaults={
                "title": "E2E Admin Set",
                "description": "Admin-created problem set (unassigned)",
                "is_public": True,
                "created_by": admin,
            },
        )
        self._report("ProblemSet", "e2e-admin-set (unassigned)", created)

        for idx, problem in enumerate(admin_problems):
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_admin_set,
                problem=problem,
                defaults={"order": idx},
            )
            self._report("ProblemSetMembership (admin-set)", problem.slug, created)

        ps_extra, created = ProblemSet.objects.get_or_create(
            slug="e2e-extra",
            defaults={
                "title": "E2E Extra Practice",
                "description": "Extra practice problems (unassigned)",
                "is_public": True,
                "created_by": instructor,
            },
        )
        self._report("ProblemSet", "e2e-extra (unassigned)", created)

        extra_members = [(admin_debugfix, 0), (admin_eipl, 1)]
        for problem, order in extra_members:
            _, created = ProblemSetMembership.objects.get_or_create(
                problem_set=ps_extra,
                problem=problem,
                defaults={"order": order},
            )
            self._report("ProblemSetMembership (extra)", problem.slug, created)

        # ------------------------------------------------------------------
        # 5. CourseProblemSet linkages to CS101-2024
        # ------------------------------------------------------------------
        now = timezone.now()

        _, created = CourseProblemSet.objects.update_or_create(
            course=course,
            problem_set=ps_basics,
            defaults={
                "order": 1,
                "due_date": now + timedelta(days=30),
                "deadline_type": "soft",
                "is_required": True,
            },
        )
        self._report("CourseProblemSet", "e2e-basics -> CS101-2024", created)

        _, created = CourseProblemSet.objects.update_or_create(
            course=course,
            problem_set=ps_code,
            defaults={
                "order": 2,
                "due_date": now - timedelta(days=7),
                "deadline_type": "soft",
                "is_required": True,
            },
        )
        self._report("CourseProblemSet", "e2e-code -> CS101-2024 (past soft)", created)

        _, created = CourseProblemSet.objects.update_or_create(
            course=course,
            problem_set=ps_mixed,
            defaults={
                "order": 3,
                "due_date": now - timedelta(days=7),
                "deadline_type": "hard",
                "is_required": True,
            },
        )
        self._report("CourseProblemSet", "e2e-mixed -> CS101-2024 (past hard)", created)

        # ------------------------------------------------------------------
        # 6. Hints for e2e-eipl-1
        # ------------------------------------------------------------------
        _, created = ProblemHint.objects.get_or_create(
            problem=eipl,
            hint_type="variable_fade",
            defaults={
                "is_enabled": True,
                "min_attempts": 2,
                "content": {
                    "mappings": [
                        {"from": "total", "to": "running sum"},
                        {"from": "n", "to": "each number"},
                    ]
                },
            },
        )
        self._report("ProblemHint", "variable_fade for e2e-eipl-1", created)

        _, created = ProblemHint.objects.get_or_create(
            problem=eipl,
            hint_type="subgoal_highlight",
            defaults={
                "is_enabled": True,
                "min_attempts": 2,
                "content": {
                    "subgoals": [
                        {
                            "line_start": 1,
                            "line_end": 1,
                            "title": "Initialize",
                            "explanation": "Set up a variable to hold the running total.",
                        },
                        {
                            "line_start": 2,
                            "line_end": 3,
                            "title": "Accumulate",
                            "explanation": "Loop through each number and add it to the total.",
                        },
                        {
                            "line_start": 4,
                            "line_end": 4,
                            "title": "Return",
                            "explanation": "Return the computed sum.",
                        },
                    ]
                },
            },
        )
        self._report("ProblemHint", "subgoal_highlight for e2e-eipl-1", created)

        _, created = ProblemHint.objects.get_or_create(
            problem=eipl,
            hint_type="suggested_trace",
            defaults={
                "is_enabled": True,
                "min_attempts": 2,
                "content": {
                    "suggested_call": "sum_list([1, 2, 3])",
                },
            },
        )
        self._report("ProblemHint", "suggested_trace for e2e-eipl-1", created)

        # ------------------------------------------------------------------
        # 7. Prior submission for student on e2e-mcq-1
        # ------------------------------------------------------------------
        existing_sub = Submission.objects.filter(
            user=student,
            problem=mcq,
            problem_set=ps_basics,
            course=course,
            submission_type="mcq",
            is_correct=True,
        ).first()
        if not existing_sub:
            Submission.objects.create(
                user=student,
                problem=mcq,
                problem_set=ps_basics,
                course=course,
                submission_type="mcq",
                raw_input="a",
                score=100,
                is_correct=True,
                passed_all_tests=True,
                completion_status="complete",
                execution_status="completed",
            )
            created = True
        else:
            created = False
        self._report("Submission", "student -> e2e-mcq-1 (mcq)", created)

        # ------------------------------------------------------------------
        # 8. Consent record for student (behavioral tracking)
        # ------------------------------------------------------------------
        for consent_type, label in [
            (ConsentType.BEHAVIORAL_TRACKING, "behavioral_tracking"),
            (ConsentType.AI_PROCESSING, "ai_processing"),
        ]:
            existing = UserConsent.objects.filter(
                user=student,
                consent_type=consent_type,
                granted=True,
            ).exists()
            if not existing:
                UserConsent.objects.create(
                    user=student,
                    consent_type=consent_type,
                    granted=True,
                    ip_address="127.0.0.1",
                    policy_version="1.0",
                    consent_method=ConsentMethod.REGISTRATION,
                )
                self._report("UserConsent", f"{label} for student", True)
            else:
                self._report("UserConsent", f"{label} for student", False)

        # ------------------------------------------------------------------
        # 9. UserProgress for student on e2e-mcq-1
        # ------------------------------------------------------------------
        _, created = UserProgress.objects.get_or_create(
            user=student,
            problem=mcq,
            problem_set=ps_basics,
            course=course,
            defaults={
                "status": "completed",
                "best_score": 100,
                "attempts": 1,
                "successful_attempts": 1,
                "is_completed": True,
                "completion_percentage": 100,
                "grade": "complete",
                "first_attempt": now,
                "last_attempt": now,
                "completed_at": now,
            },
        )
        self._report("UserProgress", "student -> e2e-mcq-1 (completed)", created)

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        self.stdout.write(
            self.style.SUCCESS(
                "\nE2E seed data ready!\n"
                f"  Categories: 2\n"
                f"  Problems: {len(all_problems)} (7 by instructor + 4 by admin)\n"
                f"  Problem Sets: 5 (3 assigned to CS101-2024, 2 unassigned)\n"
                f"  CourseProblemSet linkages: 3\n"
                f"  Hints: 3 (variable_fade, subgoal_highlight, suggested_trace)\n"
                f"  Submission: 1 (student -> e2e-mcq-1)\n"
                f"  Consent: 2 (behavioral_tracking, ai_processing)\n"
                f"  Progress: 1 (student -> e2e-mcq-1 completed)"
            )
        )

    def _report(self, model_name: str, identifier: str, created: bool):
        """Print whether an object was created or already existed."""
        if created:
            self.stdout.write(f"  Created {model_name}: {identifier}")
        else:
            self.stdout.write(f"  Skipped {model_name}: {identifier} (already exists)")
