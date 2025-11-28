from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from ..models import Problem, ProblemHint, ProblemCategory


class ProblemHintModelTests(TestCase):
    """Test suite for ProblemHint model functionality and validation"""

    def setUp(self):
        """Create test data for hint tests"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        self.category = ProblemCategory.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        self.problem = Problem.objects.create(
            slug='test-problem',
            title='Test Problem',
            description='Test problem description',
            function_name='test_function',
            function_signature='def test_function():',
            reference_solution='def test_function():\n    return True',
            created_by=self.user
        )

    def test_variable_fade_hint_creation(self):
        """Test creating a valid variable fade hint"""
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=3,
            content={
                'mappings': [
                    {'from': 'x', 'to': 'count'},
                    {'from': 'y', 'to': 'total'}
                ]
            }
        )
        
        self.assertEqual(hint.hint_type, 'variable_fade')
        self.assertEqual(len(hint.content['mappings']), 2)
        self.assertEqual(hint.content['mappings'][0]['from'], 'x')

    def test_subgoal_highlight_hint_creation(self):
        """Test creating a valid subgoal highlight hint"""
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=True,
            min_attempts=2,
            content={
                'subgoals': [
                    {
                        'line_start': 1,
                        'line_end': 3,
                        'title': 'Initialize variables',
                        'explanation': 'Set up the initial state'
                    },
                    {
                        'line_start': 4,
                        'line_end': 6,
                        'title': 'Process data',
                        'explanation': 'Perform the main calculation'
                    }
                ]
            }
        )
        
        self.assertEqual(hint.hint_type, 'subgoal_highlight')
        self.assertEqual(len(hint.content['subgoals']), 2)
        self.assertEqual(hint.content['subgoals'][0]['title'], 'Initialize variables')

    def test_suggested_trace_hint_creation(self):
        """Test creating a valid suggested trace hint"""
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='suggested_trace',
            is_enabled=True,
            min_attempts=1,
            content={
                'suggested_call': 'test_function()',
                'explanation': 'Try tracing this function call'
            }
        )
        
        self.assertEqual(hint.hint_type, 'suggested_trace')
        self.assertEqual(hint.content['suggested_call'], 'test_function()')

    def test_hint_type_uniqueness(self):
        """Test that each hint type can only exist once per problem"""
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={'mappings': []}
        )
        
        # Attempting to create another variable_fade hint should fail
        with self.assertRaises(Exception):  # IntegrityError due to unique_together constraint
            ProblemHint.objects.create(
                problem=self.problem,
                hint_type='variable_fade',
                is_enabled=False,
                content={'mappings': []}
            )

    def test_variable_fade_validation_missing_mappings(self):
        """Test validation fails when variable fade hint missing mappings"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={}  # Missing mappings
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Variable fade hint must contain mappings', str(context.exception))

    def test_variable_fade_validation_invalid_mappings_format(self):
        """Test validation fails when mappings is not a list"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={'mappings': 'not a list'}
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Mappings must be a list', str(context.exception))

    def test_variable_fade_validation_invalid_mapping_structure(self):
        """Test validation fails when mapping lacks required fields"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={
                'mappings': [
                    {'from': 'x'},  # Missing 'to' field
                    {'to': 'total'}  # Missing 'from' field
                ]
            }
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Each mapping must have "from" and "to" fields', str(context.exception))

    def test_subgoal_highlight_validation_missing_subgoals(self):
        """Test validation fails when subgoal highlight hint missing subgoals"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=True,
            content={}  # Missing subgoals
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Subgoal highlight hint must contain subgoals', str(context.exception))

    def test_subgoal_highlight_validation_invalid_subgoals_format(self):
        """Test validation fails when subgoals is not a list"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=True,
            content={'subgoals': 'not a list'}
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Subgoals must be a list', str(context.exception))

    def test_subgoal_highlight_validation_missing_required_fields(self):
        """Test validation fails when subgoal lacks required fields"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=True,
            content={
                'subgoals': [
                    {
                        'line_start': 1,
                        'title': 'Step 1'
                        # Missing line_end and explanation
                    }
                ]
            }
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Each subgoal must have: line_start, line_end, title, explanation', str(context.exception))

    def test_suggested_trace_validation_missing_suggested_call(self):
        """Test validation fails when suggested trace hint missing suggested_call"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='suggested_trace',
            is_enabled=True,
            content={}  # Missing suggested_call
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Suggested trace hint must contain suggested_call', str(context.exception))

    def test_suggested_trace_validation_invalid_suggested_call_type(self):
        """Test validation fails when suggested_call is not a string"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='suggested_trace',
            is_enabled=True,
            content={'suggested_call': 123}  # Not a string
        )
        
        with self.assertRaises(ValidationError) as context:
            hint.clean()
        
        self.assertIn('Suggested call must be a string', str(context.exception))

    def test_hint_ordering_by_type(self):
        """Test that hints are ordered by hint_type"""
        hint_c = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={'mappings': []}
        )
        
        hint_a = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=True,
            content={'subgoals': []}
        )
        
        hint_b = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='suggested_trace',
            is_enabled=True,
            content={'suggested_call': 'test()'}
        )
        
        hints = list(ProblemHint.objects.filter(problem=self.problem))
        
        # Should be ordered alphabetically by hint_type
        expected_order = ['subgoal_highlight', 'suggested_trace', 'variable_fade']
        actual_order = [hint.hint_type for hint in hints]
        
        self.assertEqual(actual_order, expected_order)

    def test_hint_str_representation(self):
        """Test string representation of hint"""
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={'mappings': []}
        )
        
        expected_str = f"{self.problem.title} - Variable Fade"
        self.assertEqual(str(hint), expected_str)

    def test_edge_case_empty_content(self):
        """Test hint creation with empty content (should fail validation)"""
        hint = ProblemHint(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={}
        )
        
        with self.assertRaises(ValidationError):
            hint.clean()

    def test_edge_case_none_content(self):
        """Test hint creation with None content (should use default)"""
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='suggested_trace',
            is_enabled=False,
            # content will default to empty dict
        )
        
        # Should save but fail validation when cleaned
        with self.assertRaises(ValidationError):
            hint.clean()

    def test_unicode_variable_names(self):
        """Test variable fade with Unicode variable names"""
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            content={
                'mappings': [
                    {'from': 'α', 'to': 'alpha'},
                    {'from': 'β', 'to': 'beta'},
                    {'from': 'variable_名前', 'to': 'variable_name'}
                ]
            }
        )
        
        # Should not raise validation error
        hint.clean()
        self.assertEqual(len(hint.content['mappings']), 3)

    def test_large_subgoal_list(self):
        """Test subgoal hint with many subgoals (performance consideration)"""
        large_subgoals = []
        for i in range(100):
            large_subgoals.append({
                'line_start': i * 2 + 1,
                'line_end': i * 2 + 2,
                'title': f'Step {i + 1}',
                'explanation': f'Explanation for step {i + 1}'
            })
        
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=True,
            content={'subgoals': large_subgoals}
        )
        
        # Should not raise validation error
        hint.clean()
        self.assertEqual(len(hint.content['subgoals']), 100)

    def test_concurrent_hint_creation(self):
        """Test creating hints concurrently (race condition simulation)"""
        from django.db import transaction
        
        def create_hint():
            with transaction.atomic():
                return ProblemHint.objects.create(
                    problem=self.problem,
                    hint_type='variable_fade',
                    is_enabled=True,
                    content={'mappings': []}
                )
        
        # First creation should succeed
        hint1 = create_hint()
        self.assertIsNotNone(hint1)
        
        # Second creation should fail due to unique constraint
        with self.assertRaises(Exception):
            create_hint()