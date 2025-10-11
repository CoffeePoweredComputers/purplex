from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from purplex.problems_app.models import (
    Course, Problem, ProblemSet, ProblemCategory, TestCase,
    ProblemSetMembership, CourseProblemSet, ProblemHint
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
- `foo("listen", "silent")` → `True`
- `foo("hello", "world")` → `False`
- `foo("A", "a")` → `True` (case insensitive)

## Constraints
- The comparison should be case-insensitive
- Ignore spaces and punctuation
- String length: 1 ≤ len(str) ≤ 1000''',
                'difficulty': 'beginner',
                'function_name': 'foo',
                'function_signature': 'def foo(a: str, b: str) -> bool:',
                'reference_solution': '''def foo(a, b):
    # Remove spaces and convert to lowercase
    x = ''.join(a.split()).lower()
    y = ''.join(b.split()).lower()

    # Check if sorted characters are equal
    return sorted(x) == sorted(y)''',
                'memory_limit': 128,
                'tags': ['strings', 'sorting', 'hash-map'],
                'is_active': True,
                'created_by': instructor1,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'checks if two strings have the same letters by sorting them',
                            'segments': [
                                'checks if two strings have the same letters by sorting them'
                            ],
                            'code_lines': [[3, 4, 7]]
                        },
                        'multi_structural': {
                            'prompt': 'first it takes a and removes spaces and makes it lowercase and stores in x then it takes b and removes spaces and makes it lowercase and stores in y then it sorts x and sorts y and checks if theyre equal',
                            'segments': [
                                'takes a and removes spaces and makes it lowercase and stores in x',
                                'takes b and removes spaces and makes it lowercase and stores in y',
                                'sorts x and sorts y and checks if theyre equal'
                            ],
                            'code_lines': [[3], [4], [7]]
                        }
                    }
                }
            }
        )[0]
        anagram_problem.categories.add(strings_cat)

        # Add hints for Anagram problem
        ProblemHint.objects.get_or_create(
            problem=anagram_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'a', 'to': 'first_string'},
                        {'from': 'b', 'to': 'second_string'},
                        {'from': 'x', 'to': 'cleaned_first'},
                        {'from': 'y', 'to': 'cleaned_second'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=anagram_problem,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 3,
                            'line_end': 4,
                            'title': 'Prepare: Normalize for Fair Comparison',
                            'explanation': 'Remove formatting differences (spaces, case) so comparison focuses only on letter content. Anagrams differ in arrangement, not characters.'
                        },
                        {
                            'line_start': 7,
                            'line_end': 7,
                            'title': 'Decide: Compare Character Content',
                            'explanation': 'Sorting reveals if strings contain same letters. If sorted versions match, they have identical characters—the definition of anagrams.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=anagram_problem,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo("Listen", "Silent")',
                    'trace_steps': [
                        'a = "Listen", b = "Silent" — Different case and order',
                        'x = "listen" — WHY: normalize to focus on letters, not format',
                        'y = "silent" — WHY: apply same normalization for fair comparison',
                        'sorted(x) = ["e","i","l","n","s","t"] — WHY: reveal character content',
                        'sorted(y) = ["e","i","l","n","s","t"] — WHY: reveal character content',
                        'Equal! → True — AHA: same characters = anagrams ✓'
                    ]
                }
            }
        )

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
- `foo("racecar")` → `True`
- `foo("hello")` → `False`
- `foo("A man a plan a canal Panama")` → `True`

## Constraints
- The comparison should be case-insensitive
- Ignore spaces and punctuation
- String length: 1 ≤ len(str) ≤ 1000''',
                'difficulty': 'beginner',
                'function_name': 'foo',
                'function_signature': 'def foo(x: str) -> bool:',
                'reference_solution': '''def foo(x):
    # Clean the string: remove spaces and convert to lowercase
    y = ''.join(c.lower() for c in x if c.isalnum())

    # Check if it reads the same forwards and backwards
    return y == y[::-1]''',
                'memory_limit': 128,
                'tags': ['strings', 'two-pointers'],
                'is_active': True,
                'created_by': instructor1,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'checks if string reads same forwards and backwards by cleaning it and reversing',
                            'segments': [
                                'checks if string reads same forwards and backwards by cleaning it and reversing'
                            ],
                            'code_lines': [[3, 6]]
                        },
                        'multi_structural': {
                            'prompt': 'first it goes through each character in x and keeps only letters and numbers and makes them lowercase and stores in y then it reverses y and checks if its equal to y',
                            'segments': [
                                'goes through each character in x and keeps only letters and numbers and makes them lowercase and stores in y',
                                'reverses y and checks if its equal to y'
                            ],
                            'code_lines': [[3], [6]]
                        }
                    }
                }
            }
        )[0]
        palindrome_problem.categories.add(strings_cat)

        # Add hints for Palindrome problem
        ProblemHint.objects.get_or_create(
            problem=palindrome_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'x', 'to': 'input_string'},
                        {'from': 'y', 'to': 'cleaned_string'},
                        {'from': 'c', 'to': 'char'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=palindrome_problem,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 3,
                            'line_end': 3,
                            'title': 'Prepare: Extract Core Content',
                            'explanation': 'Remove formatting (spaces, punctuation, case) to focus on character sequence. Palindromes are about letter patterns, not formatting.'
                        },
                        {
                            'line_start': 6,
                            'line_end': 6,
                            'title': 'Decide: Test Symmetry',
                            'explanation': 'Compare string to its reverse. If identical, the sequence is symmetric—the definition of a palindrome.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=palindrome_problem,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo("Race car")',
                    'trace_steps': [
                        'x = "Race car" — Has spaces and mixed case',
                        'y = "racecar" — WHY: normalize to focus on letter sequence',
                        'y[::-1] = "racecar" — WHY: test if sequence is symmetric',
                        'Equal! → True — AHA: same forwards/backwards = palindrome ✓'
                    ]
                }
            }
        )

        # Problem 3: Two Sum (shared problem)
        two_sum_problem = Problem.objects.get_or_create(
            slug='two-sum',
            defaults={
                'title': 'Two Sum',
                'description': '''# Two Sum

Given an array of integers `x` and an integer `y`, return indices of the
two numbers such that they add up to y.

You may assume that each input would have exactly one solution, and you may not
use the same element twice.

## Examples
- `foo([2,7,11,15], 9)` → `[0,1]` (because 2 + 7 = 9)
- `foo([3,2,4], 6)` → `[1,2]` (because 2 + 4 = 6)

## Constraints
- 2 ≤ x.length ≤ 10⁴
- -10⁹ ≤ x[i] ≤ 10⁹
- -10⁹ ≤ y ≤ 10⁹
- Only one valid answer exists.''',
                'difficulty': 'beginner',
                'function_name': 'foo',
                'function_signature': 'def foo(x: list, y: int) -> list:',
                'reference_solution': '''def foo(x, y):
    m = {}
    for i, v in enumerate(x):
        c = y - v
        if c in m:
            return [m[c], i]
        m[v] = i
    return []''',
                'memory_limit': 128,
                'tags': ['arrays', 'hash-map', 'algorithms'],
                'is_active': True,
                'created_by': instructor1,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'iterates through array storing values in dictionary and checking if complement exists to find two numbers that sum to target',
                            'segments': [
                                'iterates through array storing values in dictionary and checking if complement exists to find two numbers that sum to target'
                            ],
                            'code_lines': [[2, 3, 4, 5, 6, 7]]
                        },
                        'multi_structural': {
                            'prompt': 'creates empty dictionary m then loops through each index i and value v in x then calculates c as y minus v then checks if c is in m and returns indices if found then stores v with index i in m then returns empty list',
                            'segments': [
                                'creates empty dictionary m',
                                'loops through each index i and value v in x',
                                'calculates c as y minus v',
                                'checks if c is in m and returns indices if found',
                                'stores v with index i in m',
                                'returns empty list'
                            ],
                            'code_lines': [[2], [3], [4], [5, 6], [7], [8]]
                        }
                    }
                }
            }
        )[0]
        two_sum_problem.categories.add(arrays_cat, algorithms_cat)

        # Add hints for Two Sum problem
        ProblemHint.objects.get_or_create(
            problem=two_sum_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'x', 'to': 'numbers_array'},
                        {'from': 'y', 'to': 'target_sum'},
                        {'from': 'm', 'to': 'seen_values'},
                        {'from': 'i', 'to': 'index'},
                        {'from': 'v', 'to': 'value'},
                        {'from': 'c', 'to': 'complement'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=two_sum_problem,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 2,
                            'line_end': 2,
                            'title': 'Setup: Track What We\'ve Seen',
                            'explanation': 'Dictionary remembers values and their positions. Enables instant lookup to find if complement exists.'
                        },
                        {
                            'line_start': 3,
                            'line_end': 4,
                            'title': 'Process: Check Each Value',
                            'explanation': 'For each number, calculate what value would complete the sum. This complement is the "missing piece" we\'re looking for.'
                        },
                        {
                            'line_start': 5,
                            'line_end': 7,
                            'title': 'Decide: Found or Remember',
                            'explanation': 'If complement exists in memory, we found our pair! Otherwise, remember current value for future checks.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=two_sum_problem,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo([2,7,11,15], 9)',
                    'trace_steps': [
                        'x = [2,7,11,15], y = 9 — Need two numbers that sum to 9',
                        'm = {} — WHY: track values we\'ve seen for instant lookup',
                        'i=0, v=2: c = 9-2 = 7 — WHY: 7 would complete the sum',
                        'c(7) not in m → m[2]=0 — WHY: remember 2 at index 0 for later',
                        'i=1, v=7: c = 9-7 = 2 — WHY: 2 would complete the sum',
                        'c(2) in m! → [0,1] — AHA: found 2 earlier at index 0, pair found ✓'
                    ]
                }
            }
        )

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
- `foo("()")` → `True`
- `foo("()[]{}")` → `True`
- `foo("(]")` → `False`
- `foo("([)]")` → `False`

## Constraints
- String length: 0 ≤ len(s) ≤ 10000
- String consists of parentheses only''',
                'difficulty': 'intermediate',
                'function_name': 'foo',
                'function_signature': 'def foo(s: str) -> bool:',
                'reference_solution': '''def foo(s):
    x = []
    m = {')': '(', '}': '{', ']': '['}

    for c in s:
        if c in m:
            # Closing bracket
            if not x or x.pop() != m[c]:
                return False
        else:
            # Opening bracket
            x.append(c)

    return len(x) == 0''',
                'memory_limit': 128,
                'tags': ['strings', 'stack', 'algorithms'],
                'is_active': True,
                'created_by': instructor2,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'uses stack to match opening and closing brackets ensuring they are properly paired and ordered',
                            'segments': [
                                'uses stack to match opening and closing brackets ensuring they are properly paired and ordered'
                            ],
                            'code_lines': [[2, 3, 5, 6, 8, 9, 10, 12, 14]]
                        },
                        'multi_structural': {
                            'prompt': 'creates empty list x and mapping m then loops through each character c in s then checks if c is closing bracket then validates stack has match and pops it or returns false then appends opening brackets to x then checks if stack is empty',
                            'segments': [
                                'creates empty list x and mapping m',
                                'loops through each character c in s',
                                'checks if c is closing bracket',
                                'validates stack has match and pops it or returns false',
                                'appends opening brackets to x',
                                'checks if stack is empty'
                            ],
                            'code_lines': [[2, 3], [5], [6], [8, 9], [12], [14]]
                        }
                    }
                }
            }
        )[0]
        parentheses_problem.categories.add(strings_cat, algorithms_cat)

        # Add hints for Valid Parentheses problem
        ProblemHint.objects.get_or_create(
            problem=parentheses_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 's', 'to': 'input_string'},
                        {'from': 'x', 'to': 'stack'},
                        {'from': 'm', 'to': 'bracket_pairs'},
                        {'from': 'c', 'to': 'char'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=parentheses_problem,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 2,
                            'line_end': 3,
                            'title': 'Setup: Prepare Matching Tools',
                            'explanation': 'Stack tracks opening brackets in order. Dictionary maps each closing bracket to its matching opening bracket for validation.'
                        },
                        {
                            'line_start': 5,
                            'line_end': 12,
                            'title': 'Process: Match or Stack',
                            'explanation': 'Closing brackets must match the most recent opening bracket (stack top). Opening brackets are saved for future matching.'
                        },
                        {
                            'line_start': 14,
                            'line_end': 14,
                            'title': 'Validate: All Paired?',
                            'explanation': 'Empty stack means every opening bracket found its closing pair. Non-empty means unpaired brackets remain.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=parentheses_problem,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo("([)]")',
                    'trace_steps': [
                        's = "([)]" — Mixed bracket types, potentially invalid',
                        'x = [], m = {")":"(", "}":"{", "]":"["} — WHY: track opens, know pairs',
                        'c="(": opening → x = ["("] — WHY: save for future match',
                        'c="[": opening → x = ["(","["] — WHY: stack maintains order',
                        'c=")": closing, m[")"]="(" — WHY: check if matches stack top',
                        'x.pop()="[" ≠ "(" → False — AHA: wrong bracket type, order violated ✗'
                    ]
                }
            }
        )

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
- `foo(2)` → `1` (F(2) = F(1) + F(0) = 1 + 0 = 1)
- `foo(3)` → `2` (F(3) = F(2) + F(1) = 1 + 1 = 2)
- `foo(4)` → `3` (F(4) = F(3) + F(2) = 2 + 1 = 3)

## Constraints
- 0 ≤ n ≤ 30''',
                'difficulty': 'beginner',
                'function_name': 'foo',
                'function_signature': 'def foo(n: int) -> int:',
                'reference_solution': '''def foo(n):
    if n <= 1:
        return n

    x, y = 0, 1
    for _ in range(2, n + 1):
        x, y = y, x + y

    return y''',
                'memory_limit': 128,
                'tags': ['mathematics', 'dynamic-programming', 'algorithms'],
                'is_active': True,
                'created_by': instructor2,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'calculates fibonacci number using iteration with two variables tracking previous values',
                            'segments': [
                                'calculates fibonacci number using iteration with two variables tracking previous values'
                            ],
                            'code_lines': [[2, 3, 5, 6, 7, 9]]
                        },
                        'multi_structural': {
                            'prompt': 'checks if n is 0 or 1 and returns n then initializes x to 0 and y to 1 then loops from 2 to n plus 1 then swaps x and y where x becomes y and y becomes x plus y then returns y',
                            'segments': [
                                'checks if n is 0 or 1 and returns n',
                                'initializes x to 0 and y to 1',
                                'loops from 2 to n plus 1',
                                'swaps x and y where x becomes y and y becomes x plus y',
                                'returns y'
                            ],
                            'code_lines': [[2, 3], [5], [6], [7], [9]]
                        }
                    }
                }
            }
        )[0]
        fibonacci_problem.categories.add(math_cat, algorithms_cat)

        # Add hints for Fibonacci problem
        ProblemHint.objects.get_or_create(
            problem=fibonacci_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'n', 'to': 'target_position'},
                        {'from': 'x', 'to': 'previous'},
                        {'from': 'y', 'to': 'current'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=fibonacci_problem,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 2,
                            'line_end': 3,
                            'title': 'Base Cases: Handle Simple Inputs',
                            'explanation': 'F(0)=0 and F(1)=1 by definition. These require no calculation, just direct return.'
                        },
                        {
                            'line_start': 5,
                            'line_end': 7,
                            'title': 'Build Up: Generate Sequence',
                            'explanation': 'Start from F(0) and F(1), then iteratively compute each next number as sum of previous two. Variables slide forward through sequence.'
                        },
                        {
                            'line_start': 9,
                            'line_end': 9,
                            'title': 'Result: Return Current Value',
                            'explanation': 'After n-1 iterations, current variable holds F(n)—the exact position requested.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=fibonacci_problem,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo(4)',
                    'trace_steps': [
                        'n = 4 — Want F(4)',
                        'n > 1, so compute iteratively',
                        'x=0, y=1 — WHY: start with F(0)=0, F(1)=1',
                        'Loop 2→4: — WHY: build sequence step by step',
                        '  i=2: x,y = 1,1 — WHY: F(2) = F(1)+F(0) = 1+0 = 1',
                        '  i=3: x,y = 1,2 — WHY: F(3) = F(2)+F(1) = 1+1 = 2',
                        '  i=4: x,y = 2,3 — WHY: F(4) = F(3)+F(2) = 2+1 = 3',
                        'return y=3 — AHA: built up to exact position requested ✓'
                    ]
                }
            }
        )

        # Problem 6: Reverse Array
        reverse_array_problem = Problem.objects.get_or_create(
            slug='reverse-array',
            defaults={
                'title': 'Reverse Array',
                'description': '''# Reverse Array

Given an array of integers, return a new array with elements in reverse order.

## Examples
- `foo([1, 2, 3, 4, 5])` → `[5, 4, 3, 2, 1]`
- `foo([10])` → `[10]`
- `foo([])` → `[]`

## Constraints
- 0 ≤ array length ≤ 1000
- -10⁹ ≤ array[i] ≤ 10⁹''',
                'difficulty': 'easy',
                'function_name': 'foo',
                'function_signature': 'def foo(x: list) -> list:',
                'reference_solution': '''def foo(x):
    return x[::-1]''',
                'memory_limit': 128,
                'tags': ['arrays', 'basic'],
                'is_active': True,
                'created_by': instructor1,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'reverses the array using slice notation',
                            'segments': [
                                'reverses the array using slice notation'
                            ],
                            'code_lines': [[2]]
                        },
                        'multi_structural': {
                            'prompt': 'returns x with slice notation that goes backwards',
                            'segments': [
                                'returns x with slice notation that goes backwards'
                            ],
                            'code_lines': [[2]]
                        }
                    }
                }
            }
        )[0]
        reverse_array_problem.categories.add(arrays_cat)

        # Add hints for Reverse Array problem
        ProblemHint.objects.get_or_create(
            problem=reverse_array_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'x', 'to': 'input_array'}
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=reverse_array_problem,
            hint_type='subgoal_highlight',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'subgoals': [
                        {
                            'line_start': 2,
                            'line_end': 2,
                            'title': 'Reverse: Use Slice Notation',
                            'explanation': 'Python slice [::-1] creates new list traversing from end to start with step -1. Single operation reverses entire sequence.'
                        }
                    ]
                }
            }
        )

        ProblemHint.objects.get_or_create(
            problem=reverse_array_problem,
            hint_type='suggested_trace',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'suggested_call': 'foo([1,2,3,4,5])',
                    'trace_steps': [
                        'x = [1,2,3,4,5] — Array in original order',
                        'x[::-1] — WHY: slice with step -1 traverses backwards',
                        'Start at end (5), step backward → [5,4,3,2,1]',
                        'return [5,4,3,2,1] — AHA: reversed order in one operation ✓'
                    ]
                }
            }
        )

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