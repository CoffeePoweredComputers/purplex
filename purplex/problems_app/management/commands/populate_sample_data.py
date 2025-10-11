from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership, ProblemHint

class Command(BaseCommand):
    help = 'Populate the database with sample problems and categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of sample data (delete existing)',
        )

    def handle(self, *args, **options):
        if options['force']:
            self.stdout.write('Clearing existing sample data...')
            Problem.objects.all().delete()
            ProblemCategory.objects.all().delete()
            ProblemSet.objects.all().delete()

        # Create categories
        self.stdout.write('Creating categories...')
        
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
                'description': 'General algorithmic problems',
                'color': '#ef4444',
                'order': 2
            }
        )[0]
        
        data_structures_cat = ProblemCategory.objects.get_or_create(
            name='Data Structures',
            defaults={
                'slug': 'data-structures',
                'description': 'Problems focusing on data structure usage',
                'color': '#10b981',
                'order': 3
            }
        )[0]

        # Create sample problems
        self.stdout.write('Creating sample problems...')
        
        # Anagram problem
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
                'problem_type': 'eipl',
                'function_name': 'foo',
                'function_signature': 'def foo(a: str, b: str) -> bool:',
                'reference_solution': '''def foo(a, b):
    # Remove spaces and convert to lowercase
    x = a.replace(" ", "").lower()
    y = b.replace(" ", "").lower()
    
    # Check if sorted characters are equal
    return sorted(x) == sorted(y)''',
                'memory_limit': 128,
                'tags': ['strings', 'sorting', 'hash-map'],
                'is_active': True,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'checks if two strings have the same letters by sorting them',
                            'segments': [
                                'checks if two strings have the same letters by sorting them'
                            ],
                            'code_lines': [[2, 3, 5]]
                        },
                        'multi_structural': {
                            'prompt': 'first it takes a and removes spaces and makes it lowercase and stores in x then it takes b and removes spaces and makes it lowercase and stores in y then it sorts x and sorts y and checks if theyre equal',
                            'segments': [
                                'takes a and removes spaces and makes it lowercase and stores in x',
                                'takes b and removes spaces and makes it lowercase and stores in y',
                                'sorts x and sorts y and checks if theyre equal'
                            ],
                            'code_lines': [[2], [3], [5]]
                        }
                    }
                }
            }
        )[0]
        
        anagram_problem.categories.add(strings_cat)
        
        # Add hints for anagram problem
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
                            'line_start': 2,
                            'line_end': 3,
                            'title': 'Prepare: Normalize for Fair Comparison',
                            'explanation': 'Remove formatting differences (spaces, case) so comparison focuses only on letter content. Anagrams differ in arrangement, not characters.'
                        },
                        {
                            'line_start': 5,
                            'line_end': 5,
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
        
        # Add test cases for anagram
        test_cases = [
            (['listen', 'silent'], True, 'Basic anagram test', False, True),
            (['hello', 'world'], False, 'Non-anagram test', False, True),
            (['A', 'a'], True, 'Case insensitive test', False, True),
            (['race', 'care'], True, 'Another anagram', False, False),
            (['rat', 'car'], False, 'Different lengths', False, False),
            (['Astronomer', 'Moon starer'], True, 'Spaces and case', True, False),
            (['', ''], True, 'Empty strings', True, False),
            (['a', 'aa'], False, 'Different character counts', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(test_cases):
            TestCase.objects.get_or_create(
                problem=anagram_problem,
                order=i,
                defaults={
                    'inputs': inputs,
                    'expected_output': expected,
                    'description': description,
                    'is_hidden': is_hidden,
                    'is_sample': is_sample
                }
            )

        # Palindrome problem
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
                'problem_type': 'eipl',
                'function_name': 'foo',
                'function_signature': 'def foo(x: str) -> bool:',
                'reference_solution': '''def foo(x):
    # Clean the string: remove spaces and convert to lowercase
    c = ''.join(i.lower() for i in x if i.isalnum())
    
    # Check if it reads the same forwards and backwards
    return c == c[::-1]''',
                'memory_limit': 128,
                'tags': ['strings', 'two-pointers'],
                'is_active': True,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'checks if a string reads the same forwards and backwards',
                            'segments': [
                                'checks if a string reads the same forwards and backwards'
                            ],
                            'code_lines': [[2, 4]]
                        },
                        'multi_structural': {
                            'prompt': 'first it goes through x and filters only letters and numbers and lowercases them and stores in c then it reverses c and checks if c equals the reversed version',
                            'segments': [
                                'goes through x and filters only letters and numbers and lowercases them and stores in c',
                                'reverses c and checks if c equals the reversed version'
                            ],
                            'code_lines': [[2], [4]]
                        }
                    }
                }
            }
        )[0]
        
        palindrome_problem.categories.add(strings_cat)
        
        # Add hints for palindrome problem
        ProblemHint.objects.get_or_create(
            problem=palindrome_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 'x', 'to': 'input_string'},
                        {'from': 'c', 'to': 'cleaned_string'},
                        {'from': 'i', 'to': 'char'}
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
                            'line_start': 2,
                            'line_end': 2,
                            'title': 'Prepare: Extract Core Letters',
                            'explanation': 'Remove non-letters to focus on the actual word content. Palindromes ignore spaces and punctuation, comparing only letter sequences.'
                        },
                        {
                            'line_start': 4,
                            'line_end': 4,
                            'title': 'Decide: Test Symmetry',
                            'explanation': 'Compare string with its reverse. If they match, the string reads the same forwards and backwards—the definition of a palindrome.'
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
                    'suggested_call': 'foo("A man a plan a canal Panama")',
                    'trace_steps': [
                        'x = "A man a plan a canal Panama" — Has spaces and mixed case',
                        'Iterate and filter: keep only letters/numbers, convert to lowercase',
                        'c = "amanaplanacanalpanama" — WHY: isolated the letter sequence',
                        'c[::-1] = "amanaplanacanalpanama" — WHY: reverse to test symmetry',
                        'c == c[::-1] is True — AHA: reads same both directions ✓',
                        'Return: True'
                    ]
                }
            }
        )
        
        # Add test cases for palindrome
        palindrome_tests = [
            (['racecar'], True, 'Simple palindrome', False, True),
            (['hello'], False, 'Non-palindrome', False, True),
            (['A man a plan a canal Panama'], True, 'Complex palindrome with spaces', False, True),
            (['race a car'], False, 'Not a palindrome with spaces', False, False),
            ([''], True, 'Empty string', True, False),
            (['a'], True, 'Single character', True, False),
            (['Madam'], True, 'Case insensitive', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(palindrome_tests):
            TestCase.objects.get_or_create(
                problem=palindrome_problem,
                order=i,
                defaults={
                    'inputs': inputs,
                    'expected_output': expected,
                    'description': description,
                    'is_hidden': is_hidden,
                    'is_sample': is_sample
                }
            )

        # Valid Parentheses problem
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
                'problem_type': 'eipl',
                'function_name': 'foo',
                'function_signature': 'def foo(s: str) -> bool:',
                'reference_solution': '''def foo(s):
    k = []
    m = {')': '(', '}': '{', ']': '['}
    
    for c in s:
        if c in m:
            # Closing bracket
            if not k or k.pop() != m[c]:
                return False
        else:
            # Opening bracket
            k.append(c)
    
    return len(k) == 0''',
                'memory_limit': 128,
                'tags': ['strings', 'stack', 'data-structures'],
                'is_active': True,
                'segmentation_config': {
                    'enabled': True,
                    'threshold': 2,
                    'examples': {
                        'relational': {
                            'prompt': 'uses a stack to match opening and closing brackets',
                            'segments': [
                                'uses a stack to match opening and closing brackets'
                            ],
                            'code_lines': [[2, 3, 5, 6, 7, 8, 9, 10, 11, 13]]
                        },
                        'multi_structural': {
                            'prompt': 'first it makes an empty list k for the stack then it makes a dictionary m that maps closing brackets to opening brackets then it loops through each character c in s then if c is in m it checks if k is empty or if popping from k doesnt equal the opening bracket for c and returns false if so otherwise it pushes c to k then after the loop it checks if k is empty',
                            'segments': [
                                'makes an empty list k for the stack',
                                'makes a dictionary m that maps closing brackets to opening brackets',
                                'loops through each character c in s',
                                'if c is in m it checks if k is empty or if popping from k doesnt equal the opening bracket for c and returns false if so',
                                'otherwise it pushes c to k',
                                'after the loop it checks if k is empty'
                            ],
                            'code_lines': [[2], [3], [5], [6, 7, 8], [10, 11], [13]]
                        }
                    }
                }
            }
        )[0]
        
        parentheses_problem.categories.add(strings_cat, data_structures_cat)
        
        # Add hints for parentheses problem
        ProblemHint.objects.get_or_create(
            problem=parentheses_problem,
            hint_type='variable_fade',
            defaults={
                'is_enabled': True,
                'min_attempts': 3,
                'content': {
                    'mappings': [
                        {'from': 's', 'to': 'input_string'},
                        {'from': 'k', 'to': 'stack'},
                        {'from': 'm', 'to': 'bracket_pairs'},
                        {'from': 'c', 'to': 'current_char'}
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
                            'title': 'Setup: Prepare Matching System',
                            'explanation': 'Initialize stack to track unmatched opening brackets, and create mapping to identify which opener matches each closer. Stack enables last-in-first-out matching.'
                        },
                        {
                            'line_start': 5,
                            'line_end': 11,
                            'title': 'Process: Match Brackets as Encountered',
                            'explanation': 'For each bracket: if closing, verify it matches the most recent opener (pop and compare). If opening, save it for later matching (push). This enforces correct nesting order.'
                        },
                        {
                            'line_start': 13,
                            'line_end': 13,
                            'title': 'Validate: Check Complete Pairing',
                            'explanation': 'Empty stack means all openers found their closers. Non-empty means some brackets were never matched—invalid.'
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
                    'suggested_call': 'foo("([{}])")',
                    'trace_steps': [
                        's = "([{}])" — Nested brackets, need to match in order',
                        'k = [], m = {")":"(", "}":"{", "]":"["} — WHY: stack tracks opens, map identifies pairs',
                        'c = "(": opening → push to k → k = ["("]',
                        'c = "[": opening → push to k → k = ["(", "["]',
                        'c = "{": opening → push to k → k = ["(", "[", "{"]',
                        'c = "}": closing → pop "{", matches m["}"] ✓ → k = ["(", "["]',
                        'c = "]": closing → pop "[", matches m["]"] ✓ → k = ["("]',
                        'c = ")": closing → pop "(", matches m[")"] ✓ → k = []',
                        'len(k) == 0 → True — AHA: all openers matched in correct order ✓'
                    ]
                }
            }
        )
        
        # Add test cases for valid parentheses
        parentheses_tests = [
            (['()'], True, 'Simple valid parentheses', False, True),
            (['()[]{}'], True, 'Multiple types valid', False, True),
            (['(]'], False, 'Wrong closing bracket', False, True),
            (['([)]'], False, 'Wrong order', False, False),
            ([''], True, 'Empty string', True, False),
            (['(((('], False, 'Only opening brackets', True, False),
            (['))))'], False, 'Only closing brackets', True, False),
            (['(()())'], True, 'Nested valid', True, False),
        ]
        
        for i, (inputs, expected, description, is_hidden, is_sample) in enumerate(parentheses_tests):
            TestCase.objects.get_or_create(
                problem=parentheses_problem,
                order=i,
                defaults={
                    'inputs': inputs,
                    'expected_output': expected,
                    'description': description,
                    'is_hidden': is_hidden,
                    'is_sample': is_sample
                }
            )

        # Create a problem set
        self.stdout.write('Creating problem set...')
        
        beginner_set = ProblemSet.objects.get_or_create(
            slug='string-fundamentals',
            defaults={
                'title': 'String Fundamentals',
                'description': 'Essential string manipulation problems for beginners',
                'is_public': True
            }
        )[0]
        
        # Add problems to set
        ProblemSetMembership.objects.get_or_create(
            problem_set=beginner_set,
            problem=anagram_problem,
            defaults={'order': 0}
        )
        
        ProblemSetMembership.objects.get_or_create(
            problem_set=beginner_set,
            problem=palindrome_problem,
            defaults={'order': 1}
        )
        
        ProblemSetMembership.objects.get_or_create(
            problem_set=beginner_set,
            problem=parentheses_problem,
            defaults={'order': 2}
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully populated sample data!')
        )
        self.stdout.write(f'Created {Problem.objects.count()} problems')
        self.stdout.write(f'Created {ProblemCategory.objects.count()} categories')
        self.stdout.write(f'Created {ProblemSet.objects.count()} problem sets')
        self.stdout.write(f'Created {TestCase.objects.count()} test cases')