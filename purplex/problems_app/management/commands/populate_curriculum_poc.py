from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership, ProblemHint

class Command(BaseCommand):
    help = 'POC: Populate first 3 problems from curriculum plan to validate schema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of POC data (delete existing)',
        )

    def handle(self, *args, **options):
        if options['force']:
            self.stdout.write('Clearing existing POC data...')
            Problem.objects.filter(slug__in=['count-vowels', 'sum-of-digits', 'is-even']).delete()

        # Get or create instructor
        instructor, _ = User.objects.get_or_create(
            username='instructor_poc',
            defaults={
                'email': 'instructor_poc@purplex.com',
                'is_staff': True
            }
        )

        # Create category
        self.stdout.write('Creating category...')
        basics_cat = ProblemCategory.objects.get_or_create(
            name='Python Basics',
            defaults={
                'slug': 'python-basics',
                'description': 'Fundamental Python operations',
                'color': '#3b82f6',
                'order': 1
            }
        )[0]

        # =====================================================================
        # PROBLEM 1: Count Vowels
        # =====================================================================
        self.stdout.write('Creating Problem 1: Count Vowels...')
        problem_1 = Problem.objects.get_or_create(
            slug='count-vowels',
            defaults={
                'title': 'Count Vowels',
                'description': '''# Count Vowels

Write a function that counts the number of vowels in a string.

## Examples
- `foo("hello")` → `2`
- `foo("aeiou")` → `5`
- `foo("xyz")` → `0`

## Constraints
- Case insensitive
- String length: 0 ≤ len(s) ≤ 1000''',
                'difficulty': 'beginner',
                'problem_type': 'eipl',
                'function_name': 'foo',
                'function_signature': 'def foo(s: str) -> int:',
                'reference_solution': '''def foo(s):
    return sum(1 for c in s.lower() if c in 'aeiou')''',
                'memory_limit': 128,
                'tags': ['strings', 'iteration', 'filtering'],
                'is_active': True,
                'created_by': instructor,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'counts how many vowels are in the string',
                            'segments': ['counts how many vowels are in the string'],
                            'code_lines': [[2]]
                        },
                        'multi_structural': {
                            'prompt': 'goes through each character in s and converts to lowercase then checks if its a vowel then counts how many',
                            'segments': [
                                'goes through each character in s and converts to lowercase',
                                'checks if its a vowel',
                                'counts how many'
                            ],
                            'code_lines': [[2], [2], [2]]
                        }
                    }
                }
            }
        )[0]

        problem_1.categories.add(basics_cat)

        # Add hints for Problem 1
        ProblemHint.objects.get_or_create(
            problem=problem_1,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 's', 'to': 'input_string'},
                        {'from': 'c', 'to': 'character'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=problem_1,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 2,
                            'line_end': 2,
                            'title': 'Filter: Count Vowels Only',
                            'explanation': 'Comprehension iterates and counts only vowel characters. The generator expression checks each character after converting to lowercase, testing membership in vowel set.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=problem_1,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo("Hello")',
                    'trace_steps': [
                        's = "Hello" — Input has mixed case',
                        'Iterate: c="H" → lowercase="h" → not in vowels',
                        'c="e" → lowercase="e" → in vowels → count +1',
                        'c="l" → lowercase="l" → not in vowels',
                        'c="l" → lowercase="l" → not in vowels',
                        'c="o" → lowercase="o" → in vowels → count +1',
                        'sum = 2 → AHA: lowercase normalization + membership test ✓'
                    ]
                }
            }
        )

        # Test cases for Problem 1
        test_cases_1 = [
            (['hello'], 2, 'Basic vowel count', False, True),
            (['aeiou'], 5, 'All vowels', False, True),
            (['xyz'], 0, 'No vowels', False, True),
            (['HELLO'], 2, 'Case insensitive', False, False),
            ([''], 0, 'Empty string', True, False),
            (['bcdfg'], 0, 'Only consonants', True, False),
        ]

        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(test_cases_1):
            TestCase.objects.get_or_create(
                problem=problem_1,
                order=i,
                defaults={
                    'inputs': inputs,
                    'expected_output': expected,
                    'description': description,
                    'is_hidden': is_hidden,
                    'is_sample': is_sample
                }
            )

        # =====================================================================
        # PROBLEM 2: Sum of Digits
        # =====================================================================
        self.stdout.write('Creating Problem 2: Sum of Digits...')
        problem_2 = Problem.objects.get_or_create(
            slug='sum-of-digits',
            defaults={
                'title': 'Sum of Digits',
                'description': '''# Sum of Digits

Write a function that returns the sum of all digits in a number.

## Examples
- `foo(123)` → `6` (1+2+3)
- `foo(0)` → `0`
- `foo(99)` → `18` (9+9)

## Constraints
- Input: 0 ≤ n ≤ 10^9''',
                'difficulty': 'beginner',
                'problem_type': 'eipl',
                'function_name': 'foo',
                'function_signature': 'def foo(n: int) -> int:',
                'reference_solution': '''def foo(n):
    return sum(int(d) for d in str(n))''',
                'memory_limit': 128,
                'tags': ['numbers', 'strings', 'conversion'],
                'is_active': True,
                'created_by': instructor,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'adds up all the digits in the number',
                            'segments': ['adds up all the digits in the number'],
                            'code_lines': [[2]]
                        },
                        'multi_structural': {
                            'prompt': 'converts n to string then loops through each digit character then converts back to int then sums them all',
                            'segments': [
                                'converts n to string',
                                'loops through each digit character',
                                'converts back to int',
                                'sums them all'
                            ],
                            'code_lines': [[2], [2], [2], [2]]
                        }
                    }
                }
            }
        )[0]

        problem_2.categories.add(basics_cat)

        # Add hints for Problem 2
        ProblemHint.objects.get_or_create(
            problem=problem_2,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'n', 'to': 'number'},
                        {'from': 'd', 'to': 'digit_char'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=problem_2,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 2,
                            'line_end': 2,
                            'title': 'Convert & Sum: Process Each Digit',
                            'explanation': 'String conversion enables iteration over individual digits. Each digit character is converted back to int for mathematical operations, then summed.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=problem_2,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo(123)',
                    'trace_steps': [
                        'n = 123 — Integer input',
                        'str(n) = "123" — WHY: strings are iterable, integers are not',
                        'Iterate: d="1" → int("1")=1',
                        'd="2" → int("2")=2',
                        'd="3" → int("3")=3',
                        'sum([1, 2, 3]) = 6',
                        'Return: 6 → AHA: string iteration enables digit access ✓'
                    ]
                }
            }
        )

        # Test cases for Problem 2
        test_cases_2 = [
            ([123], 6, 'Basic sum', False, True),
            ([0], 0, 'Zero', False, True),
            ([99], 18, 'Repeated digits', False, True),
            ([1000], 1, 'Multiple zeros', False, False),
            ([987654321], 45, 'Large number', True, False),
        ]

        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(test_cases_2):
            TestCase.objects.get_or_create(
                problem=problem_2,
                order=i,
                defaults={
                    'inputs': inputs,
                    'expected_output': expected,
                    'description': description,
                    'is_hidden': is_hidden,
                    'is_sample': is_sample
                }
            )

        # =====================================================================
        # PROBLEM 3: Is Even
        # =====================================================================
        self.stdout.write('Creating Problem 3: Is Even...')
        problem_3 = Problem.objects.get_or_create(
            slug='is-even',
            defaults={
                'title': 'Is Even',
                'description': '''# Is Even

Write a function that determines if a number is even.

## Examples
- `foo(4)` → `True`
- `foo(5)` → `False`
- `foo(0)` → `True`

## Constraints
- Input: -10^9 ≤ n ≤ 10^9''',
                'difficulty': 'beginner',
                'problem_type': 'eipl',
                'function_name': 'foo',
                'function_signature': 'def foo(n: int) -> bool:',
                'reference_solution': '''def foo(n):
    return n % 2 == 0''',
                'memory_limit': 128,
                'tags': ['numbers', 'modulo', 'conditions'],
                'is_active': True,
                'created_by': instructor,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'checks if number is divisible by 2',
                            'segments': ['checks if number is divisible by 2'],
                            'code_lines': [[2]]
                        },
                        'multi_structural': {
                            'prompt': 'takes n modulo 2 then checks if remainder equals 0',
                            'segments': [
                                'takes n modulo 2',
                                'checks if remainder equals 0'
                            ],
                            'code_lines': [[2], [2]]
                        }
                    }
                }
            }
        )[0]

        problem_3.categories.add(basics_cat)

        # Add hints for Problem 3
        ProblemHint.objects.get_or_create(
            problem=problem_3,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'n', 'to': 'number'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=problem_3,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 2,
                            'line_end': 2,
                            'title': 'Test: Check Divisibility',
                            'explanation': 'Modulo operator gives remainder after division. Zero remainder means evenly divisible. Even numbers are those divisible by 2 with no remainder.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=problem_3,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo(4)',
                    'trace_steps': [
                        'n = 4 — Test value',
                        '4 % 2 = 0 — WHY: modulo gives remainder after division',
                        '0 == 0 → True',
                        'Return: True → AHA: even means "no remainder when divided by 2" ✓'
                    ]
                }
            }
        )

        # Test cases for Problem 3
        test_cases_3 = [
            ([4], True, 'Even positive', False, True),
            ([5], False, 'Odd positive', False, True),
            ([0], True, 'Zero is even', False, True),
            ([-2], True, 'Even negative', False, False),
            ([-3], False, 'Odd negative', True, False),
            ([1000000], True, 'Large even number', True, False),
        ]

        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(test_cases_3):
            TestCase.objects.get_or_create(
                problem=problem_3,
                order=i,
                defaults={
                    'inputs': inputs,
                    'expected_output': expected,
                    'description': description,
                    'is_hidden': is_hidden,
                    'is_sample': is_sample
                }
            )

        # =====================================================================
        # Create Problem Set
        # =====================================================================
        self.stdout.write('Creating problem set...')

        poc_set = ProblemSet.objects.get_or_create(
            slug='basic-operations-poc',
            defaults={
                'title': 'Basic Operations (POC)',
                'description': 'POC: First 3 problems from CS101 curriculum',
                'is_public': True,
                'created_by': instructor
            }
        )[0]

        # Add problems to set
        ProblemSetMembership.objects.get_or_create(
            problem_set=poc_set,
            problem=problem_1,
            defaults={'order': 0}
        )

        ProblemSetMembership.objects.get_or_create(
            problem_set=poc_set,
            problem=problem_2,
            defaults={'order': 1}
        )

        ProblemSetMembership.objects.get_or_create(
            problem_set=poc_set,
            problem=problem_3,
            defaults={'order': 2}
        )

        # =====================================================================
        # Summary
        # =====================================================================
        self.stdout.write(
            self.style.SUCCESS('\n✅ Successfully populated POC curriculum data!')
        )
        self.stdout.write(f'Created {Problem.objects.filter(slug__in=["count-vowels", "sum-of-digits", "is-even"]).count()} problems')
        self.stdout.write(f'Created {TestCase.objects.filter(problem__slug__in=["count-vowels", "sum-of-digits", "is-even"]).count()} test cases')
        self.stdout.write(f'Created {ProblemHint.objects.filter(problem__slug__in=["count-vowels", "sum-of-digits", "is-even"]).count()} hints')
        self.stdout.write(f'Created 1 problem set')
        self.stdout.write('\n' + self.style.WARNING('Next step: Run this script and validate in admin/frontend'))
