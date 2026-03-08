import random
from datetime import timedelta

from django.contrib.auth.models import User as DjangoUser
from django.core.management.base import BaseCommand
from django.db import transaction

from purplex.problems_app.models import (
    Course,
    CourseEnrollment,
    CourseInstructor,
    CourseProblemSet,
    EiplProblem,
    Problem,
    ProblemCategory,
    ProblemHint,
    ProblemSet,
    ProblemSetMembership,
    TestCase,
    UserProgress,
)
from purplex.problems_app.services import ProgressService
from purplex.submissions.models import Submission
from purplex.users_app.models import UserProfile


class Command(BaseCommand):
    help = (
        "Populate the database with comprehensive sample data showcasing all features"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clear all existing data before populating",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if options["clean"]:
                self.stdout.write("Clearing existing data...")
                self.clear_data()

            self.stdout.write("Creating comprehensive sample data...")

            # Create categories
            categories = self.create_categories()

            # Create users (instructors and students)
            instructors, students = self.create_users()

            # Create problems with hints
            problems = self.create_problems(categories)

            # Create problem sets
            problem_sets = self.create_problem_sets(problems)

            # Create courses with enrollments
            courses = self.create_courses(instructors, students, problem_sets)

            # Create sample submissions and progress
            self.create_sample_progress(students, problems, problem_sets, courses)

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully created comprehensive sample data:\n"
                    f"- {len(categories)} categories\n"
                    f"- {len(problems)} problems with hints\n"
                    f"- {sum(p.test_cases.count() for p in problems)} test cases\n"
                    f"- {len(problem_sets)} problem sets\n"
                    f"- {len(courses)} courses\n"
                    f"- {len(instructors)} instructors\n"
                    f"- {len(students)} students\n"
                    f"- Sample progress and submissions"
                )
            )

    def clear_data(self):
        """Clear all existing data"""
        Submission.objects.all().delete()
        UserProgress.objects.all().delete()
        CourseEnrollment.objects.all().delete()
        Course.all_objects.all().delete()
        ProblemSet.objects.all().delete()
        ProblemHint.objects.all().delete()
        Problem.objects.all().delete()
        ProblemCategory.objects.all().delete()
        # Don't delete users - they might have important data

    def create_categories(self):
        """Create problem categories"""
        self.stdout.write("Creating categories...")

        categories = []

        cat_data = [
            {
                "name": "String Manipulation",
                "slug": "strings",
                "description": "Problems involving string processing and manipulation",
                "color": "#3b82f6",
                "order": 1,
            },
            {
                "name": "Algorithms",
                "slug": "algorithms",
                "description": "Classic algorithmic problems and techniques",
                "color": "#ef4444",
                "order": 2,
            },
            {
                "name": "Data Structures",
                "slug": "data-structures",
                "description": "Problems focusing on data structure usage",
                "color": "#10b981",
                "order": 3,
            },
            {
                "name": "Mathematics",
                "slug": "mathematics",
                "description": "Mathematical and numerical problems",
                "color": "#f59e0b",
                "order": 4,
            },
        ]

        for data in cat_data:
            cat, _ = ProblemCategory.objects.get_or_create(
                slug=data["slug"], defaults=data
            )
            categories.append(cat)

        return categories

    def create_users(self):
        """Create instructor and student users"""
        self.stdout.write("Creating users...")

        instructors = []
        students = []

        # Create instructors
        for i in range(1, 3):
            username = f"prof_{i}"
            django_user, created = DjangoUser.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": "Professor",
                    "last_name": f"{i}",
                    "email": f"{username}@university.edu",
                    "is_staff": True,
                },
            )
            if created:
                django_user.set_password("password123")
                django_user.save()

            UserProfile.objects.get_or_create(
                user=django_user,
                defaults={
                    "firebase_uid": f"{username}_firebase_uid",
                    "role": "instructor",
                },
            )

            instructors.append(django_user)

        # Create students
        for i in range(1, 9):
            username = f"student_{i}"
            django_user, created = DjangoUser.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": "Student",
                    "last_name": f"{i}",
                    "email": f"{username}@university.edu",
                },
            )
            if created:
                django_user.set_password("password123")
                django_user.save()

            UserProfile.objects.get_or_create(
                user=django_user,
                defaults={
                    "firebase_uid": f"{username}_firebase_uid",
                    "role": "student",
                },
            )

            students.append(django_user)

        return instructors, students

    def create_problems(self, categories):
        """Create problems with test cases and hints"""
        self.stdout.write("Creating problems with hints...")

        problems = []

        # String Manipulation Problems
        problem_data = [
            # String Manipulation
            {
                "slug": "palindrome-checker",
                "title": "Palindrome Checker",
                "description": """# Palindrome Checker

Write a function that determines if a given string is a palindrome.

A palindrome reads the same forward and backward, ignoring spaces, punctuation, and case.

## Examples
- `is_palindrome("racecar")` → `True`
- `is_palindrome("A man a plan a canal Panama")` → `True`
- `is_palindrome("hello")` → `False`""",
                "difficulty": "easy",
                "categories": [categories[0]],  # String Manipulation
                "function_name": "is_palindrome",
                "function_signature": "def is_palindrome(s: str) -> bool:",
                "reference_solution": """def is_palindrome(s):
    cleaned = ''.join(char.lower() for char in s if char.isalnum())
    return cleaned == cleaned[::-1]""",
                "test_cases": [
                    (["racecar"], True, "Simple palindrome", False, True),
                    (["hello"], False, "Non-palindrome", False, True),
                    (
                        ["A man a plan a canal Panama"],
                        True,
                        "Complex palindrome",
                        False,
                        True,
                    ),
                    ([""], True, "Empty string", True, False),
                    (["a"], True, "Single character", True, False),
                ],
                "hints": [
                    {
                        "type": "variable_fade",
                        "content": {
                            "mappings": [
                                {"from": "s", "to": "input_string"},
                                {"from": "cleaned", "to": "normalized_text"},
                                {"from": "char", "to": "character"},
                            ]
                        },
                        "min_attempts": 3,
                    }
                ],
            },
            {
                "slug": "anagram-detector",
                "title": "Anagram Detector",
                "description": """# Anagram Detector

Write a function that checks if two strings are anagrams of each other.

Two strings are anagrams if they contain the same characters with the same frequency.

## Examples
- `is_anagram("listen", "silent")` → `True`
- `is_anagram("hello", "world")` → `False`""",
                "difficulty": "beginner",
                "categories": [categories[0]],  # String Manipulation
                "function_name": "is_anagram",
                "function_signature": "def is_anagram(str1: str, str2: str) -> bool:",
                "reference_solution": """def is_anagram(str1, str2):
    str1 = str1.replace(" ", "").lower()
    str2 = str2.replace(" ", "").lower()
    return sorted(str1) == sorted(str2)""",
                "test_cases": [
                    (["listen", "silent"], True, "Basic anagram", False, True),
                    (["hello", "world"], False, "Non-anagram", False, True),
                    (["A", "a"], True, "Case insensitive", False, True),
                    (["", ""], True, "Empty strings", True, False),
                ],
                "hints": [
                    {
                        "type": "subgoal_highlight",
                        "content": {
                            "subgoals": [
                                {
                                    "line_start": 1,
                                    "line_end": 2,
                                    "title": "Normalize strings",
                                    "explanation": "Remove spaces and convert to lowercase for fair comparison",
                                },
                                {
                                    "line_start": 3,
                                    "line_end": 3,
                                    "title": "Compare sorted characters",
                                    "explanation": "Sort both strings and check if they are equal",
                                },
                            ]
                        },
                        "min_attempts": 2,
                    }
                ],
            },
            {
                "slug": "string-compression",
                "title": "String Compression",
                "description": """# String Compression

Implement basic string compression using the counts of repeated characters.

For example, the string "aabcccccaaa" would become "a2b1c5a3".

## Examples
- `compress("aabcccccaaa")` → `"a2b1c5a3"`
- `compress("abc")` → `"abc"` (no compression if result would be longer)""",
                "difficulty": "intermediate",
                "categories": [categories[0]],  # String Manipulation
                "function_name": "compress",
                "function_signature": "def compress(s: str) -> str:",
                "reference_solution": """def compress(s):
    if not s:
        return s

    result = []
    count = 1

    for i in range(1, len(s)):
        if s[i] == s[i-1]:
            count += 1
        else:
            result.append(s[i-1] + str(count))
            count = 1

    result.append(s[-1] + str(count))
    compressed = ''.join(result)

    return compressed if len(compressed) < len(s) else s""",
                "test_cases": [
                    (["aabcccccaaa"], "a2b1c5a3", "Basic compression", False, True),
                    (["abc"], "abc", "No compression needed", False, True),
                    ([""], "", "Empty string", True, False),
                    (["aaaa"], "a4", "All same character", True, False),
                ],
                "hints": [
                    {
                        "type": "suggested_trace",
                        "content": {
                            "suggested_call": 'compress("aabbcc")',
                            "trace_explanation": "Walk through how the function processes consecutive characters",
                        },
                        "min_attempts": 4,
                    }
                ],
            },
            # Algorithms
            {
                "slug": "binary-search",
                "title": "Binary Search",
                "description": """# Binary Search

Implement binary search to find the index of a target value in a sorted array.

Return -1 if the target is not found.

## Examples
- `binary_search([1, 3, 5, 7, 9], 5)` → `2`
- `binary_search([1, 3, 5, 7, 9], 6)` → `-1`""",
                "difficulty": "beginner",
                "categories": [categories[1]],  # Algorithms
                "function_name": "binary_search",
                "function_signature": "def binary_search(arr: list, target: int) -> int:",
                "reference_solution": """def binary_search(arr, target):
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1""",
                "test_cases": [
                    ([[1, 3, 5, 7, 9], 5], 2, "Target in middle", False, True),
                    ([[1, 3, 5, 7, 9], 1], 0, "Target at start", False, True),
                    ([[1, 3, 5, 7, 9], 9], 4, "Target at end", False, True),
                    ([[1, 3, 5, 7, 9], 6], -1, "Target not found", False, True),
                    ([[], 5], -1, "Empty array", True, False),
                ],
                "hints": [
                    {
                        "type": "variable_fade",
                        "content": {
                            "mappings": [
                                {"from": "left", "to": "start_index"},
                                {"from": "right", "to": "end_index"},
                                {"from": "mid", "to": "middle_index"},
                            ]
                        },
                        "min_attempts": 2,
                    },
                    {
                        "type": "subgoal_highlight",
                        "content": {
                            "subgoals": [
                                {
                                    "line_start": 1,
                                    "line_end": 1,
                                    "title": "Initialize boundaries",
                                    "explanation": "Set up left and right pointers",
                                },
                                {
                                    "line_start": 3,
                                    "line_end": 10,
                                    "title": "Binary search loop",
                                    "explanation": "Repeatedly divide search space in half",
                                },
                            ]
                        },
                        "min_attempts": 3,
                    },
                    {
                        "type": "suggested_trace",
                        "content": {
                            "suggested_call": "binary_search([1, 3, 5, 7], 3)",
                            "trace_explanation": "Trace through finding the target value 3",
                        },
                        "min_attempts": 4,
                    },
                ],
            },
            {
                "slug": "quick-sort",
                "title": "Quick Sort",
                "description": """# Quick Sort

Implement the quick sort algorithm to sort an array in ascending order.

## Examples
- `quick_sort([3, 1, 4, 1, 5, 9])` → `[1, 1, 3, 4, 5, 9]`
- `quick_sort([5, 2, 8, 1])` → `[1, 2, 5, 8]`""",
                "difficulty": "intermediate",
                "categories": [categories[1]],  # Algorithms
                "function_name": "quick_sort",
                "function_signature": "def quick_sort(arr: list) -> list:",
                "reference_solution": """def quick_sort(arr):
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quick_sort(left) + middle + quick_sort(right)""",
                "test_cases": [
                    (
                        [[3, 1, 4, 1, 5, 9]],
                        [1, 1, 3, 4, 5, 9],
                        "Mixed values",
                        False,
                        True,
                    ),
                    ([[5, 2, 8, 1]], [1, 2, 5, 8], "Simple array", False, True),
                    ([[]], [], "Empty array", True, False),
                    ([[1]], [1], "Single element", True, False),
                ],
                "hints": [
                    {
                        "type": "subgoal_highlight",
                        "content": {
                            "subgoals": [
                                {
                                    "line_start": 1,
                                    "line_end": 2,
                                    "title": "Base case",
                                    "explanation": "Handle arrays with 0 or 1 element",
                                },
                                {
                                    "line_start": 4,
                                    "line_end": 7,
                                    "title": "Partition",
                                    "explanation": "Divide array into three parts based on pivot",
                                },
                                {
                                    "line_start": 9,
                                    "line_end": 9,
                                    "title": "Recursive combine",
                                    "explanation": "Recursively sort and combine partitions",
                                },
                            ]
                        },
                        "min_attempts": 3,
                    }
                ],
            },
            {
                "slug": "fibonacci-dp",
                "title": "Fibonacci with Dynamic Programming",
                "description": """# Fibonacci with Dynamic Programming

Calculate the nth Fibonacci number using dynamic programming.

The Fibonacci sequence: 0, 1, 1, 2, 3, 5, 8, 13, ...

## Examples
- `fibonacci(0)` → `0`
- `fibonacci(6)` → `8`""",
                "difficulty": "advanced",
                "categories": [categories[1]],  # Algorithms
                "function_name": "fibonacci",
                "function_signature": "def fibonacci(n: int) -> int:",
                "reference_solution": """def fibonacci(n):
    if n <= 1:
        return n

    dp = [0] * (n + 1)
    dp[1] = 1

    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]

    return dp[n]""",
                "test_cases": [
                    ([0], 0, "Base case 0", False, True),
                    ([1], 1, "Base case 1", False, True),
                    ([6], 8, "Sixth Fibonacci", False, True),
                    ([10], 55, "Tenth Fibonacci", True, False),
                ],
                "hints": [
                    {
                        "type": "variable_fade",
                        "content": {
                            "mappings": [
                                {"from": "dp", "to": "fib_cache"},
                                {"from": "i", "to": "current_index"},
                            ]
                        },
                        "min_attempts": 3,
                    }
                ],
            },
            # Data Structures
            {
                "slug": "valid-parentheses",
                "title": "Valid Parentheses",
                "description": """# Valid Parentheses

Check if a string containing only parentheses characters is valid.

A string is valid if all brackets are closed in the correct order.

## Examples
- `is_valid("()")` → `True`
- `is_valid("()[]{}")` → `True`
- `is_valid("(]")` → `False`""",
                "difficulty": "easy",
                "categories": [categories[2]],  # Data Structures
                "function_name": "is_valid",
                "function_signature": "def is_valid(s: str) -> bool:",
                "reference_solution": """def is_valid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}

    for char in s:
        if char in mapping:
            if not stack or stack.pop() != mapping[char]:
                return False
        else:
            stack.append(char)

    return len(stack) == 0""",
                "test_cases": [
                    (["()"], True, "Simple valid", False, True),
                    (["()[]{}"], True, "Multiple types", False, True),
                    (["(]"], False, "Mismatched", False, True),
                    ([""], True, "Empty string", True, False),
                ],
                "hints": [
                    {
                        "type": "suggested_trace",
                        "content": {
                            "suggested_call": 'is_valid("({[]})")',
                            "trace_explanation": "Trace how the stack handles nested brackets",
                        },
                        "min_attempts": 2,
                    }
                ],
            },
            {
                "slug": "two-sum",
                "title": "Two Sum",
                "description": """# Two Sum

Find two numbers in an array that add up to a target sum.

Return the indices of the two numbers.

## Examples
- `two_sum([2, 7, 11, 15], 9)` → `[0, 1]`
- `two_sum([3, 2, 4], 6)` → `[1, 2]`""",
                "difficulty": "beginner",
                "categories": [categories[2]],  # Data Structures
                "function_name": "two_sum",
                "function_signature": "def two_sum(nums: list, target: int) -> list:",
                "reference_solution": """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []""",
                "test_cases": [
                    ([[2, 7, 11, 15], 9], [0, 1], "Basic case", False, True),
                    ([[3, 2, 4], 6], [1, 2], "Different indices", False, True),
                    ([[3, 3], 6], [0, 1], "Same values", True, False),
                ],
                "hints": [
                    {
                        "type": "variable_fade",
                        "content": {
                            "mappings": [
                                {"from": "seen", "to": "number_indices"},
                                {"from": "complement", "to": "needed_value"},
                            ]
                        },
                        "min_attempts": 3,
                    }
                ],
            },
            {
                "slug": "linked-list-reversal",
                "title": "Linked List Reversal",
                "description": """# Linked List Reversal

Reverse a linked list represented as a Python list.

## Examples
- `reverse_list([1, 2, 3, 4, 5])` → `[5, 4, 3, 2, 1]`
- `reverse_list([1])` → `[1]`""",
                "difficulty": "intermediate",
                "categories": [categories[2]],  # Data Structures
                "function_name": "reverse_list",
                "function_signature": "def reverse_list(lst: list) -> list:",
                "reference_solution": """def reverse_list(lst):
    return lst[::-1]""",
                "test_cases": [
                    ([[1, 2, 3, 4, 5]], [5, 4, 3, 2, 1], "Normal list", False, True),
                    ([[1]], [1], "Single element", False, True),
                    ([[]], [], "Empty list", True, False),
                ],
                "hints": [],  # No hints for this problem
            },
            # Mathematics
            {
                "slug": "prime-checker",
                "title": "Prime Number Checker",
                "description": """# Prime Number Checker

Check if a number is prime.

A prime number is only divisible by 1 and itself.

## Examples
- `is_prime(7)` → `True`
- `is_prime(4)` → `False`""",
                "difficulty": "easy",
                "categories": [categories[3]],  # Mathematics
                "function_name": "is_prime",
                "function_signature": "def is_prime(n: int) -> bool:",
                "reference_solution": """def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True""",
                "test_cases": [
                    ([7], True, "Prime number", False, True),
                    ([4], False, "Composite number", False, True),
                    ([2], True, "Smallest prime", False, True),
                    ([1], False, "Not prime", True, False),
                ],
                "hints": [
                    {
                        "type": "variable_fade",
                        "content": {
                            "mappings": [
                                {"from": "n", "to": "number_to_check"},
                                {"from": "i", "to": "divisor"},
                            ]
                        },
                        "min_attempts": 2,
                    },
                    {
                        "type": "subgoal_highlight",
                        "content": {
                            "subgoals": [
                                {
                                    "line_start": 1,
                                    "line_end": 2,
                                    "title": "Handle edge cases",
                                    "explanation": "Numbers less than 2 are not prime",
                                },
                                {
                                    "line_start": 3,
                                    "line_end": 5,
                                    "title": "Check divisibility",
                                    "explanation": "Test divisibility up to square root",
                                },
                            ]
                        },
                        "min_attempts": 3,
                    },
                    {
                        "type": "suggested_trace",
                        "content": {
                            "suggested_call": "is_prime(11)",
                            "trace_explanation": "Walk through checking if 11 is prime",
                        },
                        "min_attempts": 4,
                    },
                ],
            },
            {
                "slug": "gcd-calculator",
                "title": "GCD Calculator",
                "description": """# Greatest Common Divisor

Calculate the greatest common divisor of two numbers using Euclid's algorithm.

## Examples
- `gcd(48, 18)` → `6`
- `gcd(7, 5)` → `1`""",
                "difficulty": "beginner",
                "categories": [categories[3]],  # Mathematics
                "function_name": "gcd",
                "function_signature": "def gcd(a: int, b: int) -> int:",
                "reference_solution": """def gcd(a, b):
    while b:
        a, b = b, a % b
    return a""",
                "test_cases": [
                    ([48, 18], 6, "Common factors", False, True),
                    ([7, 5], 1, "Coprime numbers", False, True),
                    ([100, 50], 50, "One divides other", True, False),
                ],
                "hints": [
                    {
                        "type": "subgoal_highlight",
                        "content": {
                            "subgoals": [
                                {
                                    "line_start": 1,
                                    "line_end": 2,
                                    "title": "Euclidean algorithm",
                                    "explanation": "Repeatedly apply modulo operation until b becomes 0",
                                }
                            ]
                        },
                        "min_attempts": 3,
                    }
                ],
            },
            {
                "slug": "matrix-multiplication",
                "title": "Matrix Multiplication",
                "description": """# Matrix Multiplication

Multiply two 2x2 matrices.

## Examples
- `multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]])` → `[[19, 22], [43, 50]]`""",
                "difficulty": "intermediate",
                "categories": [categories[3]],  # Mathematics
                "function_name": "multiply",
                "function_signature": "def multiply(A: list, B: list) -> list:",
                "reference_solution": """def multiply(A, B):
    result = [[0, 0], [0, 0]]
    for i in range(2):
        for j in range(2):
            for k in range(2):
                result[i][j] += A[i][k] * B[k][j]
    return result""",
                "test_cases": [
                    (
                        [[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
                        [[19, 22], [43, 50]],
                        "Basic multiplication",
                        False,
                        True,
                    ),
                    (
                        [[[1, 0], [0, 1]], [[5, 6], [7, 8]]],
                        [[5, 6], [7, 8]],
                        "Identity matrix",
                        False,
                        True,
                    ),
                ],
                "hints": [],  # No hints for this problem
            },
        ]

        for data in problem_data:
            problem, _ = EiplProblem.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "title": data["title"],
                    "description": data["description"],
                    "difficulty": data["difficulty"],
                    "function_name": data["function_name"],
                    "function_signature": data["function_signature"],
                    "reference_solution": data["reference_solution"],
                    "memory_limit": 128,
                    "tags": data.get("tags", []),
                    "is_active": True,
                    "completion_threshold": 80,
                    "segmentation_config": (
                        {
                            "enabled": True,
                            "threshold": 3,
                            "examples": {
                                "relational": {
                                    "prompt": "The function checks if a string is a palindrome by comparing it with its reverse",
                                    "segments": [
                                        "The function should check if palindrome"
                                    ],
                                    "code_lines": [[1, 2, 3]],
                                },
                                "multi_structural": {
                                    "prompt": "First normalize the string, then check if it reads the same backwards",
                                    "segments": [
                                        "First normalize the string",
                                        "then check if it reads the same",
                                    ],
                                    "code_lines": [[1, 2], [3, 4]],
                                },
                            },
                        }
                        if data["slug"] in ["palindrome-checker", "string-compression"]
                        else {}
                    ),
                },
            )

            # Add categories
            for cat in data["categories"]:
                problem.categories.add(cat)

            # Create test cases
            for i, (inputs, expected, desc, hidden, sample) in enumerate(
                data["test_cases"]
            ):
                TestCase.objects.get_or_create(
                    problem=problem,
                    order=i,
                    defaults={
                        "inputs": inputs,
                        "expected_output": expected,
                        "description": desc,
                        "is_hidden": hidden,
                        "is_sample": sample,
                    },
                )

            # Create hints
            for hint_data in data.get("hints", []):
                ProblemHint.objects.get_or_create(
                    problem=problem,
                    hint_type=hint_data["type"],
                    defaults={
                        "is_enabled": True,
                        "min_attempts": hint_data.get("min_attempts", 3),
                        "content": hint_data["content"],
                    },
                )

            problems.append(problem)

        return problems

    def create_problem_sets(self, problems):
        """Create problem sets"""
        self.stdout.write("Creating problem sets...")

        problem_sets = []

        sets_data = [
            {
                "slug": "introduction-to-programming",
                "title": "Introduction to Programming",
                "description": "Start your programming journey with these fundamental problems",
                "problems": [
                    "palindrome-checker",
                    "valid-parentheses",
                    "prime-checker",
                ],
            },
            {
                "slug": "string-algorithms",
                "title": "String Algorithms",
                "description": "Master string manipulation techniques",
                "problems": [
                    "palindrome-checker",
                    "anagram-detector",
                    "string-compression",
                ],
            },
            {
                "slug": "data-structures-fundamentals",
                "title": "Data Structures Fundamentals",
                "description": "Learn essential data structures",
                "problems": ["valid-parentheses", "two-sum", "linked-list-reversal"],
            },
            {
                "slug": "algorithm-mastery",
                "title": "Algorithm Mastery",
                "description": "Advanced algorithmic problems",
                "problems": [
                    "binary-search",
                    "quick-sort",
                    "fibonacci-dp",
                    "gcd-calculator",
                    "matrix-multiplication",
                ],
            },
        ]

        for set_data in sets_data:
            problem_set, _ = ProblemSet.objects.get_or_create(
                slug=set_data["slug"],
                defaults={
                    "title": set_data["title"],
                    "description": set_data["description"],
                    "is_public": True,
                },
            )

            # Add problems to set with ordering
            for order, problem_slug in enumerate(set_data["problems"]):
                problem = Problem.objects.get(slug=problem_slug)
                ProblemSetMembership.objects.get_or_create(
                    problem_set=problem_set, problem=problem, defaults={"order": order}
                )

            problem_sets.append(problem_set)

        return problem_sets

    def create_courses(self, instructors, students, problem_sets):
        """Create courses with enrollments"""
        self.stdout.write("Creating courses and enrollments...")

        courses = []

        # CS101 - Introduction to Computer Science
        cs101, _ = Course.all_objects.get_or_create(
            course_id="CS101-FALL2024",
            defaults={
                "name": "Introduction to Computer Science",
                "description": "Learn the fundamentals of programming and computer science",
                "is_active": True,
                "enrollment_open": True,
            },
        )
        CourseInstructor.objects.get_or_create(
            course=cs101, user=instructors[0], defaults={"role": "primary"}
        )

        # Add problem sets to CS101
        for order, ps_slug in enumerate(
            ["introduction-to-programming", "string-algorithms"]
        ):
            ps = ProblemSet.objects.get(slug=ps_slug)
            CourseProblemSet.objects.get_or_create(
                course=cs101, problem_set=ps, defaults={"order": order}
            )

        # Enroll students 1-5 in CS101
        for student in students[:5]:
            CourseEnrollment.objects.get_or_create(
                course=cs101, user=student, defaults={"is_active": True}
            )

        courses.append(cs101)

        # CS201 - Data Structures and Algorithms
        cs201, _ = Course.all_objects.get_or_create(
            course_id="CS201-FALL2024",
            defaults={
                "name": "Data Structures and Algorithms",
                "description": "Deep dive into data structures and algorithmic thinking",
                "is_active": True,
                "enrollment_open": True,
            },
        )
        CourseInstructor.objects.get_or_create(
            course=cs201, user=instructors[1], defaults={"role": "primary"}
        )

        # Add problem sets to CS201
        for order, ps_slug in enumerate(
            ["data-structures-fundamentals", "algorithm-mastery"]
        ):
            ps = ProblemSet.objects.get(slug=ps_slug)
            CourseProblemSet.objects.get_or_create(
                course=cs201, problem_set=ps, defaults={"order": order}
            )

        # Enroll students 3-5 in CS201 (overlap with CS101)
        for student in students[2:5]:
            CourseEnrollment.objects.get_or_create(
                course=cs201, user=student, defaults={"is_active": True}
            )

        courses.append(cs201)

        # CS301 - Advanced Algorithms (closed enrollment)
        cs301, _ = Course.all_objects.get_or_create(
            course_id="CS301-SPRING2025",
            defaults={
                "name": "Advanced Algorithms",
                "description": "Graduate-level algorithms course",
                "is_active": True,
                "enrollment_open": False,  # Closed enrollment
            },
        )
        CourseInstructor.objects.get_or_create(
            course=cs301, user=instructors[0], defaults={"role": "primary"}
        )

        # Add problem sets to CS301
        ps = ProblemSet.objects.get(slug="algorithm-mastery")
        CourseProblemSet.objects.get_or_create(
            course=cs301, problem_set=ps, defaults={"order": 0}
        )

        # Enroll students 6-7 in CS301
        for student in students[5:7]:
            CourseEnrollment.objects.get_or_create(
                course=cs301, user=student, defaults={"is_active": True}
            )

        courses.append(cs301)

        return courses

    def create_sample_progress(self, students, problems, problem_sets, courses):
        """Create sample progress and submissions"""
        self.stdout.write("Creating sample progress and submissions...")

        # Student 1: High achiever in CS101
        student1 = students[0]
        cs101 = Course.objects.get(course_id="CS101-FALL2024")

        for ps in cs101.problem_sets.all():
            for membership in ps.problemsetmembership_set.all():
                problem = membership.problem

                # Create a high-scoring submission
                score = random.randint(85, 100)
                submission = Submission.objects.create(
                    user=student1,
                    problem=problem,
                    problem_set=ps,
                    course=cs101,
                    raw_input="I need to solve this problem step by step...",
                    processed_code="# Solution code",
                    submission_type="eipl",
                    score=score,
                    passed_all_tests=(score == 100),
                    is_correct=(score == 100),
                    completion_status="complete" if score == 100 else "partial",
                    execution_status="completed",
                    execution_time_ms=int(random.uniform(100, 2000)),
                    time_spent=timedelta(minutes=random.randint(5, 30)),
                )

                # Use ProgressService to update progress
                ProgressService.process_submission(submission)

        # Student 2: Partial progress in CS101
        student2 = students[1]
        ps = ProblemSet.objects.get(slug="introduction-to-programming")

        for i, membership in enumerate(ps.problemsetmembership_set.all()):
            if i < 2:  # Only complete first 2 problems
                problem = membership.problem

                submission = Submission.objects.create(
                    user=student2,
                    problem=problem,
                    problem_set=ps,
                    course=cs101,
                    raw_input="Trying to understand the problem...",
                    processed_code="# Partial solution",
                    submission_type="eipl",
                    score=random.randint(60, 80),
                    passed_all_tests=False,
                    is_correct=False,
                    completion_status="partial",
                    execution_status="completed",
                    execution_time_ms=int(random.uniform(100, 2000)),
                    time_spent=timedelta(minutes=random.randint(10, 45)),
                )

                # Use ProgressService to update progress
                ProgressService.process_submission(submission)

        # Student 3-5: Various progress in CS201
        cs201 = Course.objects.get(course_id="CS201-FALL2024")
        for student in students[2:5]:
            ps = ProblemSet.objects.get(slug="data-structures-fundamentals")

            # Each student completes different number of problems
            num_problems = random.randint(1, ps.problems.count())
            for i, membership in enumerate(ps.problemsetmembership_set.all()):
                if i < num_problems:
                    problem = membership.problem

                    # Multiple attempts for some problems
                    num_attempts = random.randint(1, 3)
                    for attempt in range(num_attempts):
                        score = random.randint(40, 100)
                        submission = Submission.objects.create(
                            user=student,
                            problem=problem,
                            problem_set=ps,
                            course=cs201,
                            raw_input=f"Attempt {attempt + 1}: Working on the solution...",
                            processed_code="# Solution attempt",
                            submission_type="eipl",
                            score=score,
                            passed_all_tests=(score == 100),
                            is_correct=(score == 100),
                            completion_status=(
                                "complete"
                                if score == 100
                                else ("partial" if score >= 60 else "incomplete")
                            ),
                            execution_status="completed",
                            execution_time_ms=int(random.uniform(100, 3000)),
                            time_spent=timedelta(minutes=random.randint(5, 60)),
                        )

                    # Use ProgressService to update progress after final attempt
                    ProgressService.process_submission(submission)
