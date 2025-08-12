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
                            'prompt': 'The function checks if two strings are anagrams by comparing their sorted characters after normalization',
                            'segments': [
                                'Normalize both strings by removing spaces and converting to lowercase',
                                'Compare the sorted characters to determine if they are anagrams'
                            ],
                            'code_lines': [[2, 3], [5]]
                        },
                        'multi_structural': {
                            'prompt': 'Line 1 removes spaces from first string, line 2 converts it to lowercase, line 3 removes spaces from second string, line 4 converts it to lowercase, line 5 sorts both and compares',
                            'segments': [
                                'Remove spaces from the first input string',
                                'Convert first string to lowercase',
                                'Remove spaces from the second input string', 
                                'Convert second string to lowercase',
                                'Sort characters of both strings and compare for equality'
                            ],
                            'code_lines': [[2], [2], [3], [3], [5]]
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
                        {'from': 'first string', 'to': 'a'},
                        {'from': 'second string', 'to': 'b'},
                        {'from': 'normalized first', 'to': 'x'},
                        {'from': 'normalized second', 'to': 'y'},
                        {'from': 'spaces removed', 'to': 'replace(" ", "")'},
                        {'from': 'lowercase', 'to': 'lower()'},
                        {'from': 'sorted characters', 'to': 'sorted()'}
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
                            'title': 'String Normalization',
                            'explanation': 'Remove spaces and convert both strings to lowercase for case-insensitive comparison'
                        },
                        {
                            'line_start': 5,
                            'line_end': 5,
                            'title': 'Anagram Check',
                            'explanation': 'Sort the characters of both normalized strings and compare them for equality'
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
                        'a = "Listen", b = "Silent"',
                        'x = "listen" (after removing spaces and lowercasing)',
                        'y = "silent" (after removing spaces and lowercasing)',
                        'sorted(x) = ["e", "i", "l", "n", "s", "t"]',
                        'sorted(y) = ["e", "i", "l", "n", "s", "t"]',
                        'Return: True (sorted lists are equal)'
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
                            'prompt': 'The function checks if a string is a palindrome by cleaning it and comparing with its reverse',
                            'segments': [
                                'Clean the string by keeping only alphanumeric characters in lowercase',
                                'Check if the cleaned string equals its reverse'
                            ],
                            'code_lines': [[2], [4]]
                        },
                        'multi_structural': {
                            'prompt': 'Line 1 filters alphanumeric characters and converts to lowercase, line 2 compares the cleaned string with its reverse',
                            'segments': [
                                'Join filtered alphanumeric characters converted to lowercase',
                                'Compare cleaned string with its reverse using slicing'
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
                        {'from': 'input string', 'to': 'x'},
                        {'from': 'cleaned string', 'to': 'c'},
                        {'from': 'character', 'to': 'i'},
                        {'from': 'alphanumeric check', 'to': 'isalnum()'},
                        {'from': 'lowercase conversion', 'to': 'lower()'},
                        {'from': 'reverse', 'to': '[::-1]'},
                        {'from': 'join characters', 'to': "join()"}
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
                            'title': 'String Cleaning',
                            'explanation': 'Filter out non-alphanumeric characters and convert to lowercase'
                        },
                        {
                            'line_start': 4,
                            'line_end': 4,
                            'title': 'Palindrome Check',
                            'explanation': 'Compare the cleaned string with its reverse'
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
                        'x = "A man a plan a canal Panama"',
                        'Filtering: keep only alphanumeric characters',
                        'c = "amanaplanacanalpanama" (after cleaning)',
                        'c[::-1] = "amanaplanacanalpanama"',
                        'c == c[::-1] evaluates to True',
                        'Return: True (string is a palindrome)'
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
                            'prompt': 'The function validates parentheses by using a stack to match opening and closing brackets',
                            'segments': [
                                'Initialize stack and bracket mapping',
                                'Process each character by pushing opens to stack or matching closes',
                                'Check if stack is empty to confirm all brackets matched'
                            ],
                            'code_lines': [[2, 3], [5, 11], [13]]
                        },
                        'multi_structural': {
                            'prompt': 'Line 1 creates stack, line 2 defines mapping, line 3 starts loop, lines 4-8 handle closing brackets, lines 9-10 handle opening brackets, line 11 checks if stack is empty',
                            'segments': [
                                'Create empty stack for tracking open brackets',
                                'Define mapping of closing to opening brackets',
                                'Iterate through each character in string',
                                'Check if character is a closing bracket',
                                'Pop from stack and verify matching bracket or return False',
                                'Add opening bracket to stack',
                                'Return True if stack is empty, False otherwise'
                            ],
                            'code_lines': [[2], [3], [5], [6], [8], [11], [13]]
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
                        {'from': 'input string', 'to': 's'},
                        {'from': 'stack', 'to': 'k'},
                        {'from': 'mapping dictionary', 'to': 'm'},
                        {'from': 'current character', 'to': 'c'},
                        {'from': 'closing bracket check', 'to': 'c in m'},
                        {'from': 'stack push', 'to': 'k.append()'},
                        {'from': 'stack pop', 'to': 'k.pop()'},
                        {'from': 'empty stack', 'to': 'len(k) == 0'}
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
                            'title': 'Initialize Data Structures',
                            'explanation': 'Create an empty stack and define mapping of closing to opening brackets'
                        },
                        {
                            'line_start': 5,
                            'line_end': 11,
                            'title': 'Process Brackets',
                            'explanation': 'Iterate through string, push opening brackets to stack, match closing brackets'
                        },
                        {
                            'line_start': 13,
                            'line_end': 13,
                            'title': 'Validate Result',
                            'explanation': 'Check if all brackets were properly matched by verifying stack is empty'
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
                        's = "([{}])"',
                        'k = [], m = {")": "(", "}": "{", "]": "["}',
                        'c = "(": not in m, push to stack → k = ["("]',
                        'c = "[": not in m, push to stack → k = ["(", "["]',
                        'c = "{": not in m, push to stack → k = ["(", "[", "{"]',
                        'c = "}": in m, pop "{" and check → matches, continue',
                        'c = "]": in m, pop "[" and check → matches, continue',
                        'c = ")": in m, pop "(" and check → matches, continue',
                        'len(k) == 0 → True',
                        'Return: True (all brackets matched correctly)'
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