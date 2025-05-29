from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership

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
    str1 = str1.replace(" ", "").lower()
    str2 = str2.replace(" ", "").lower()
    
    # Check if sorted characters are equal
    return sorted(str1) == sorted(str2)''',
                'hints': '''- Consider converting both strings to the same case
- Think about sorting the characters
- You might want to remove spaces first''',
                'memory_limit': 128,
                'tags': ['strings', 'sorting', 'hash-map'],
                'is_active': True
            }
        )[0]
        
        anagram_problem.categories.add(strings_cat)
        
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
                'hints': '''- Consider removing non-alphabetic characters
- Think about string reversal
- Two-pointer approach might be useful''',
                'memory_limit': 128,
                'tags': ['strings', 'two-pointers'],
                'is_active': True
            }
        )[0]
        
        palindrome_problem.categories.add(strings_cat)
        
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
                'hints': '''- Think about using a stack data structure
- Match opening and closing brackets
- Consider what happens with nested brackets''',
                'memory_limit': 128,
                'tags': ['strings', 'stack', 'data-structures'],
                'is_active': True
            }
        )[0]
        
        parentheses_problem.categories.add(strings_cat, data_structures_cat)
        
        # Add test cases for valid parentheses
        parentheses_tests = [
            (['()'], True, 'Simple valid parentheses', False, True),
            (['()[]{}"'], True, 'Multiple types valid', False, True),
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