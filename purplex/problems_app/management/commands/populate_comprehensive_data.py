from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from purplex.problems_app.models import (
    Course, Problem, ProblemSet, ProblemCategory, TestCase, 
    ProblemSetMembership, CourseProblemSet
)
from purplex.users_app.models import UserProfile

class Command(BaseCommand):
    help = 'Populate the database with comprehensive course, problem set, and problem data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of sample data (delete existing)',
        )

    def handle(self, *args, **options):
        if options['force']:
            self.stdout.write('Clearing existing comprehensive data...')
            Course.objects.all().delete()
            Problem.objects.all().delete()
            ProblemCategory.objects.all().delete()
            ProblemSet.objects.all().delete()

        # Create instructor users
        self.stdout.write('Creating instructor users...')
        
        instructor1, created = User.objects.get_or_create(
            username='prof_smith',
            defaults={
                'first_name': 'Alice',
                'last_name': 'Smith',
                'email': 'alice.smith@university.edu',
                'is_staff': True
            }
        )
        if created:
            instructor1.set_password('password123')
            instructor1.save()
            UserProfile.objects.create(user=instructor1, role='instructor', firebase_uid='instructor1_uid')

        instructor2, created = User.objects.get_or_create(
            username='prof_jones',
            defaults={
                'first_name': 'Bob',
                'last_name': 'Jones',
                'email': 'bob.jones@university.edu',
                'is_staff': True
            }
        )
        if created:
            instructor2.set_password('password123')
            instructor2.save()
            UserProfile.objects.create(user=instructor2, role='instructor', firebase_uid='instructor2_uid')

        # Create categories
        self.stdout.write('Creating problem categories...')
        
        strings_cat = ProblemCategory.objects.get_or_create(
            name='String Manipulation',
            defaults={
                'slug': 'strings',
                'description': 'Problems involving string processing and manipulation',
                'color': '#3b82f6',
                'order': 1
            }
        )[0]
        
        algorithms_cat = ProblemCategory.objects.get_or_create(
            name='Algorithms',
            defaults={
                'slug': 'algorithms',
                'description': 'General algorithmic problems and data structures',
                'color': '#ef4444',
                'order': 2
            }
        )[0]
        
        arrays_cat = ProblemCategory.objects.get_or_create(
            name='Arrays & Lists',
            defaults={
                'slug': 'arrays',
                'description': 'Problems focusing on array and list manipulation',
                'color': '#10b981',
                'order': 3
            }
        )[0]

        math_cat = ProblemCategory.objects.get_or_create(
            name='Mathematics',
            defaults={
                'slug': 'mathematics',
                'description': 'Mathematical and numerical problems',
                'color': '#f59e0b',
                'order': 4
            }
        )[0]

        # Create comprehensive set of problems
        self.stdout.write('Creating problems...')
        
        # Problem 1: Anagram Checker (will be shared across multiple sets)
        anagram_problem = Problem.objects.get_or_create(
            slug='anagram-checker',
            defaults={
                'title': 'Anagram Checker',
                'description': '''# Anagram Checker

Write a function that determines if two strings are anagrams of each other.

Two strings are anagrams if they contain the same characters with the same frequency, 
but possibly in a different order.

## Examples
- `is_anagram("listen", "silent")` → `True`
- `is_anagram("hello", "world")` → `False`
- `is_anagram("A", "a")` → `True` (case insensitive)

## Constraints
- The comparison should be case-insensitive
- Ignore spaces and punctuation
- String length: 1 ≤ len(str) ≤ 1000''',
                'difficulty': 'beginner',
                'function_name': 'is_anagram',
                'function_signature': 'def is_anagram(str1: str, str2: str) -> bool:',
                'reference_solution': '''def is_anagram(str1, str2):
    # Remove spaces and convert to lowercase
    str1 = ''.join(str1.split()).lower()
    str2 = ''.join(str2.split()).lower()
    
    # Check if sorted characters are equal
    return sorted(str1) == sorted(str2)''',
                'memory_limit': 128,
                'tags': ['strings', 'sorting', 'hash-map'],
                'is_active': True,
                'created_by': instructor1
            }
        )[0]
        anagram_problem.categories.add(strings_cat)

        # Problem 2: Palindrome Checker 
        palindrome_problem = Problem.objects.get_or_create(
            slug='palindrome-checker',
            defaults={
                'title': 'Palindrome Checker',
                'description': '''# Palindrome Checker

Write a function that determines if a given string is a palindrome.

A palindrome is a word, phrase, number, or other sequence of characters that reads 
the same forward and backward.

## Examples
- `is_palindrome("racecar")` → `True`
- `is_palindrome("hello")` → `False`
- `is_palindrome("A man a plan a canal Panama")` → `True`

## Constraints
- The comparison should be case-insensitive
- Ignore spaces and punctuation
- String length: 1 ≤ len(str) ≤ 1000''',
                'difficulty': 'beginner',
                'function_name': 'is_palindrome',
                'function_signature': 'def is_palindrome(s: str) -> bool:',
                'reference_solution': '''def is_palindrome(s):
    # Clean the string: remove spaces and convert to lowercase
    cleaned = ''.join(char.lower() for char in s if char.isalnum())
    
    # Check if it reads the same forwards and backwards
    return cleaned == cleaned[::-1]''',
                'memory_limit': 128,
                'tags': ['strings', 'two-pointers'],
                'is_active': True,
                'created_by': instructor1
            }
        )[0]
        palindrome_problem.categories.add(strings_cat)

        # Problem 3: Two Sum (shared problem)
        two_sum_problem = Problem.objects.get_or_create(
            slug='two-sum',
            defaults={
                'title': 'Two Sum',
                'description': '''# Two Sum

Given an array of integers `nums` and an integer `target`, return indices of the 
two numbers such that they add up to target.

You may assume that each input would have exactly one solution, and you may not 
use the same element twice.

## Examples
- `two_sum([2,7,11,15], 9)` → `[0,1]` (because 2 + 7 = 9)
- `two_sum([3,2,4], 6)` → `[1,2]` (because 2 + 4 = 6)

## Constraints
- 2 ≤ nums.length ≤ 10⁴
- -10⁹ ≤ nums[i] ≤ 10⁹
- -10⁹ ≤ target ≤ 10⁹
- Only one valid answer exists.''',
                'difficulty': 'beginner',
                'function_name': 'two_sum',
                'function_signature': 'def two_sum(nums: list, target: int) -> list:',
                'reference_solution': '''def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []''',
                'memory_limit': 128,
                'tags': ['arrays', 'hash-map', 'algorithms'],
                'is_active': True,
                'created_by': instructor1
            }
        )[0]
        two_sum_problem.categories.add(arrays_cat, algorithms_cat)

        # Problem 4: Valid Parentheses
        parentheses_problem = Problem.objects.get_or_create(
            slug='valid-parentheses',
            defaults={
                'title': 'Valid Parentheses',
                'description': '''# Valid Parentheses

Given a string containing just the characters '(', ')', '{', '}', '[' and ']', 
determine if the input string is valid.

An input string is valid if:
1. Open brackets must be closed by the same type of brackets
2. Open brackets must be closed in the correct order

## Examples
- `is_valid("()")` → `True`
- `is_valid("()[]{}")` → `True`
- `is_valid("(]")` → `False`
- `is_valid("([)]")` → `False`

## Constraints
- String length: 0 ≤ len(s) ≤ 10000
- String consists of parentheses only''',
                'difficulty': 'intermediate',
                'function_name': 'is_valid',
                'function_signature': 'def is_valid(s: str) -> bool:',
                'reference_solution': '''def is_valid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:
            # Closing bracket
            if not stack or stack.pop() != mapping[char]:
                return False
        else:
            # Opening bracket
            stack.append(char)
    
    return len(stack) == 0''',
                'memory_limit': 128,
                'tags': ['strings', 'stack', 'algorithms'],
                'is_active': True,
                'created_by': instructor2
            }
        )[0]
        parentheses_problem.categories.add(strings_cat, algorithms_cat)

        # Problem 5: Fibonacci Sequence
        fibonacci_problem = Problem.objects.get_or_create(
            slug='fibonacci-sequence',
            defaults={
                'title': 'Fibonacci Number',
                'description': '''# Fibonacci Number

The Fibonacci numbers, commonly denoted F(n) form a sequence, called the Fibonacci sequence, 
such that each number is the sum of the two preceding ones, starting from 0 and 1.

F(0) = 0, F(1) = 1
F(n) = F(n - 1) + F(n - 2), for n > 1.

Given n, calculate F(n).

## Examples
- `fibonacci(2)` → `1` (F(2) = F(1) + F(0) = 1 + 0 = 1)
- `fibonacci(3)` → `2` (F(3) = F(2) + F(1) = 1 + 1 = 2)
- `fibonacci(4)` → `3` (F(4) = F(3) + F(2) = 2 + 1 = 3)

## Constraints
- 0 ≤ n ≤ 30''',
                'difficulty': 'beginner',
                'function_name': 'fibonacci',
                'function_signature': 'def fibonacci(n: int) -> int:',
                'reference_solution': '''def fibonacci(n):
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b''',
                'memory_limit': 128,
                'tags': ['mathematics', 'dynamic-programming', 'algorithms'],
                'is_active': True,
                'created_by': instructor2
            }
        )[0]
        fibonacci_problem.categories.add(math_cat, algorithms_cat)

        # Problem 6: Reverse Array
        reverse_array_problem = Problem.objects.get_or_create(
            slug='reverse-array',
            defaults={
                'title': 'Reverse Array',
                'description': '''# Reverse Array

Given an array of integers, return a new array with elements in reverse order.

## Examples
- `reverse_array([1, 2, 3, 4, 5])` → `[5, 4, 3, 2, 1]`
- `reverse_array([10])` → `[10]`
- `reverse_array([])` → `[]`

## Constraints
- 0 ≤ array length ≤ 1000
- -10⁹ ≤ array[i] ≤ 10⁹''',
                'difficulty': 'easy',
                'function_name': 'reverse_array',
                'function_signature': 'def reverse_array(arr: list) -> list:',
                'reference_solution': '''def reverse_array(arr):
    return arr[::-1]''',
                'memory_limit': 128,
                'tags': ['arrays', 'basic'],
                'is_active': True,
                'created_by': instructor1
            }
        )[0]
        reverse_array_problem.categories.add(arrays_cat)

        # Add test cases for all problems
        self.create_test_cases(anagram_problem, palindrome_problem, two_sum_problem, 
                             parentheses_problem, fibonacci_problem, reverse_array_problem)

        # Create Problem Sets
        self.stdout.write('Creating problem sets...')
        
        # Problem Set 1: String Fundamentals
        string_fundamentals = ProblemSet.objects.get_or_create(
            slug='string-fundamentals',
            defaults={
                'title': 'String Fundamentals',
                'description': 'Essential string manipulation problems for beginners',
                'is_public': True,
                'created_by': instructor1
            }
        )[0]

        # Problem Set 2: Algorithm Basics
        algorithm_basics = ProblemSet.objects.get_or_create(
            slug='algorithm-basics',
            defaults={
                'title': 'Algorithm Basics',
                'description': 'Introduction to fundamental algorithms and problem-solving',
                'is_public': True,
                'created_by': instructor1
            }
        )[0]

        # Problem Set 3: Array Operations
        array_operations = ProblemSet.objects.get_or_create(
            slug='array-operations',
            defaults={
                'title': 'Array Operations',
                'description': 'Working with arrays and basic data manipulation',
                'is_public': True,
                'created_by': instructor2
            }
        )[0]

        # Problem Set 4: Advanced Problem Solving
        advanced_solving = ProblemSet.objects.get_or_create(
            slug='advanced-problem-solving',
            defaults={
                'title': 'Advanced Problem Solving',
                'description': 'More challenging problems combining multiple concepts',
                'is_public': True,
                'created_by': instructor2
            }
        )[0]

        # Add problems to problem sets (with shared problems)
        self.stdout.write('Adding problems to problem sets...')
        
        # String Fundamentals: anagram, palindrome
        ProblemSetMembership.objects.get_or_create(
            problem_set=string_fundamentals, problem=anagram_problem, defaults={'order': 0}
        )
        ProblemSetMembership.objects.get_or_create(
            problem_set=string_fundamentals, problem=palindrome_problem, defaults={'order': 1}
        )

        # Algorithm Basics: two_sum, fibonacci, anagram (shared)
        ProblemSetMembership.objects.get_or_create(
            problem_set=algorithm_basics, problem=two_sum_problem, defaults={'order': 0}
        )
        ProblemSetMembership.objects.get_or_create(
            problem_set=algorithm_basics, problem=fibonacci_problem, defaults={'order': 1}
        )
        ProblemSetMembership.objects.get_or_create(
            problem_set=algorithm_basics, problem=anagram_problem, defaults={'order': 2}
        )

        # Array Operations: reverse_array, two_sum (shared)
        ProblemSetMembership.objects.get_or_create(
            problem_set=array_operations, problem=reverse_array_problem, defaults={'order': 0}
        )
        ProblemSetMembership.objects.get_or_create(
            problem_set=array_operations, problem=two_sum_problem, defaults={'order': 1}
        )

        # Advanced Problem Solving: parentheses, fibonacci (shared), two_sum (shared)
        ProblemSetMembership.objects.get_or_create(
            problem_set=advanced_solving, problem=parentheses_problem, defaults={'order': 0}
        )
        ProblemSetMembership.objects.get_or_create(
            problem_set=advanced_solving, problem=fibonacci_problem, defaults={'order': 1}
        )
        ProblemSetMembership.objects.get_or_create(
            problem_set=advanced_solving, problem=two_sum_problem, defaults={'order': 2}
        )

        # Create Courses
        self.stdout.write('Creating courses...')
        
        # Course 1: Intro to Programming
        intro_course = Course.objects.get_or_create(
            course_id='CS101-FALL2024',
            defaults={
                'name': 'Introduction to Programming',
                'description': '''A comprehensive introduction to programming fundamentals using Python. 
Students will learn basic programming concepts including variables, functions, control structures, 
and problem-solving techniques through hands-on coding exercises.''',
                'instructor': instructor1,
                'is_active': True,
                'enrollment_open': True
            }
        )[0]

        # Course 2: Data Structures and Algorithms
        dsa_course = Course.objects.get_or_create(
            course_id='CS201-FALL2024',
            defaults={
                'name': 'Data Structures and Algorithms',
                'description': '''An intermediate course covering fundamental data structures and algorithms. 
Students will explore arrays, strings, stacks, queues, and basic algorithmic problem-solving techniques 
with emphasis on efficiency and best practices.''',
                'instructor': instructor2,
                'is_active': True,
                'enrollment_open': True
            }
        )[0]

        # Add problem sets to courses (with shared problem sets)
        self.stdout.write('Adding problem sets to courses...')
        
        # Intro to Programming Course: String Fundamentals, Array Operations
        CourseProblemSet.objects.get_or_create(
            course=intro_course, problem_set=string_fundamentals, 
            defaults={'order': 0, 'is_required': True}
        )
        CourseProblemSet.objects.get_or_create(
            course=intro_course, problem_set=array_operations, 
            defaults={'order': 1, 'is_required': True}
        )

        # Data Structures and Algorithms Course: Algorithm Basics, Advanced Problem Solving
        CourseProblemSet.objects.get_or_create(
            course=dsa_course, problem_set=algorithm_basics, 
            defaults={'order': 0, 'is_required': True}
        )
        CourseProblemSet.objects.get_or_create(
            course=dsa_course, problem_set=advanced_solving, 
            defaults={'order': 1, 'is_required': True}
        )

        # Cross-course sharing: Add String Fundamentals to DSA course as optional
        CourseProblemSet.objects.get_or_create(
            course=dsa_course, problem_set=string_fundamentals, 
            defaults={'order': 2, 'is_required': False}
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully populated comprehensive data!')
        )
        self.stdout.write(f'Created {Course.objects.count()} courses')
        self.stdout.write(f'Created {ProblemSet.objects.count()} problem sets')
        self.stdout.write(f'Created {Problem.objects.count()} problems')
        self.stdout.write(f'Created {ProblemCategory.objects.count()} categories')
        self.stdout.write(f'Created {TestCase.objects.count()} test cases')
        self.stdout.write(f'Created {ProblemSetMembership.objects.count()} problem-set memberships')
        self.stdout.write(f'Created {CourseProblemSet.objects.count()} course-problemset relationships')
        
        # Show sharing summary
        self.stdout.write('\n--- Sharing Summary ---')
        self.stdout.write(f'Anagram problem appears in {anagram_problem.problemsetmembership_set.count()} problem sets')
        self.stdout.write(f'Two Sum problem appears in {two_sum_problem.problemsetmembership_set.count()} problem sets')
        self.stdout.write(f'Fibonacci problem appears in {fibonacci_problem.problemsetmembership_set.count()} problem sets')
        self.stdout.write(f'String Fundamentals appears in {string_fundamentals.courseproblemset_set.count()} courses')

    def create_test_cases(self, anagram_problem, palindrome_problem, two_sum_problem, 
                         parentheses_problem, fibonacci_problem, reverse_array_problem):
        """Create test cases for all problems"""
        
        # Anagram test cases
        anagram_tests = [
            (['listen', 'silent'], True, 'Basic anagram test', False, True),
            (['hello', 'world'], False, 'Non-anagram test', False, True),
            (['A', 'a'], True, 'Case insensitive test', False, True),
            (['race', 'care'], True, 'Another anagram', False, False),
            (['rat', 'car'], False, 'Different lengths', False, False),
            (['Astronomer', 'Moon starer'], True, 'Spaces test', True, False),
            (['', ''], True, 'Empty strings', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(anagram_tests):
            TestCase.objects.get_or_create(
                problem=anagram_problem, order=i,
                defaults={
                    'inputs': inputs, 'expected_output': expected,
                    'description': description, 'is_hidden': is_hidden, 'is_sample': is_sample
                }
            )

        # Palindrome test cases
        palindrome_tests = [
            (['racecar'], True, 'Simple palindrome', False, True),
            (['hello'], False, 'Non-palindrome', False, True),
            (['A man a plan a canal Panama'], True, 'Complex palindrome', False, True),
            (['race a car'], False, 'Not palindrome with spaces', False, False),
            ([''], True, 'Empty string', True, False),
            (['a'], True, 'Single character', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(palindrome_tests):
            TestCase.objects.get_or_create(
                problem=palindrome_problem, order=i,
                defaults={
                    'inputs': inputs, 'expected_output': expected,
                    'description': description, 'is_hidden': is_hidden, 'is_sample': is_sample
                }
            )

        # Two Sum test cases
        two_sum_tests = [
            ([[2, 7, 11, 15], 9], [0, 1], 'Basic two sum', False, True),
            ([[3, 2, 4], 6], [1, 2], 'Another example', False, True),
            ([[3, 3], 6], [0, 1], 'Duplicate numbers', False, True),
            ([[1, 2, 3, 4, 5], 8], [2, 4], 'Larger array', True, False),
            ([[-1, -2, -3, -4, -5], -8], [2, 4], 'Negative numbers', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(two_sum_tests):
            TestCase.objects.get_or_create(
                problem=two_sum_problem, order=i,
                defaults={
                    'inputs': inputs, 'expected_output': expected,
                    'description': description, 'is_hidden': is_hidden, 'is_sample': is_sample
                }
            )

        # Valid Parentheses test cases
        parentheses_tests = [
            (['()'], True, 'Simple valid', False, True),
            (['()[]{}"'], True, 'Multiple types', False, True),
            (['(]'], False, 'Wrong closing', False, True),
            (['([)]'], False, 'Wrong order', False, False),
            ([''], True, 'Empty string', True, False),
            (['(((('], False, 'Only opening', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(parentheses_tests):
            TestCase.objects.get_or_create(
                problem=parentheses_problem, order=i,
                defaults={
                    'inputs': inputs, 'expected_output': expected,
                    'description': description, 'is_hidden': is_hidden, 'is_sample': is_sample
                }
            )

        # Fibonacci test cases
        fibonacci_tests = [
            ([0], 0, 'Base case F(0)', False, True),
            ([1], 1, 'Base case F(1)', False, True),
            ([2], 1, 'F(2) = 1', False, True),
            ([3], 2, 'F(3) = 2', False, False),
            ([4], 3, 'F(4) = 3', False, False),
            ([10], 55, 'F(10) = 55', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(fibonacci_tests):
            TestCase.objects.get_or_create(
                problem=fibonacci_problem, order=i,
                defaults={
                    'inputs': inputs, 'expected_output': expected,
                    'description': description, 'is_hidden': is_hidden, 'is_sample': is_sample
                }
            )

        # Reverse Array test cases
        reverse_tests = [
            ([[1, 2, 3, 4, 5]], [5, 4, 3, 2, 1], 'Basic reverse', False, True),
            ([[10]], [10], 'Single element', False, True),
            ([[]], [], 'Empty array', False, True),
            ([[-1, -2, -3]], [-3, -2, -1], 'Negative numbers', True, False),
            ([[1, 1, 1]], [1, 1, 1], 'Duplicates', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(reverse_tests):
            TestCase.objects.get_or_create(
                problem=reverse_array_problem, order=i,
                defaults={
                    'inputs': inputs, 'expected_output': expected,
                    'description': description, 'is_hidden': is_hidden, 'is_sample': is_sample
                }
            )