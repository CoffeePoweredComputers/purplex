from rest_framework import serializers
from .models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership

class ProblemCategorySerializer(serializers.ModelSerializer):
    problems_count = serializers.ReadOnlyField()
    
    class Meta:
        model = ProblemCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color', 'order', 'problems_count']

class SimpleProblemSetSerializer(serializers.ModelSerializer):
    """Simple serializer for showing problem sets within problem details"""
    class Meta:
        model = ProblemSet
        fields = ['slug', 'title']

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'inputs', 'expected_output', 'description', 'is_hidden', 'is_sample', 'order']

class ProblemSerializer(serializers.ModelSerializer):
    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=ProblemCategory.objects.all(),
        source='categories',
        write_only=True,
        required=False
    )
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases = TestCaseSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()
    visible_test_cases_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Problem
        fields = [
            'slug', 'title', 'description', 'difficulty', 'problem_type', 'categories', 'category_ids',
            'function_name', 'function_signature', 'reference_solution', 'hints',
            'time_limit', 'memory_limit', 'estimated_time', 'tags', 'is_active',
            'problem_sets', 'test_cases', 'test_cases_count', 'visible_test_cases_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['slug', 'created_by', 'created_at', 'updated_at', 'version']

class ProblemListSerializer(serializers.ModelSerializer):
    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Problem
        fields = [
            'slug', 'title', 'description', 'difficulty', 'problem_type', 'categories', 'problem_sets',
            'function_name', 'estimated_time', 'tags', 'is_active',
            'test_cases_count', 'created_at'
        ]

class ProblemForProblemSetSerializer(serializers.ModelSerializer):
    """Serializer for problems when displayed within a problem set context.
    Includes the reference solution for the code editor."""
    categories = ProblemCategorySerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()
    visible_test_cases_count = serializers.ReadOnlyField()
    solution = serializers.CharField(source='reference_solution', read_only=True)  # Alias for frontend compatibility
    
    class Meta:
        model = Problem
        fields = [
            'slug', 'title', 'description', 'difficulty', 'problem_type', 'categories',
            'function_name', 'function_signature', 'reference_solution', 'solution',
            'hints', 'estimated_time', 'tags', 'is_active',
            'test_cases_count', 'visible_test_cases_count'
        ]

class ProblemSetMembershipSerializer(serializers.ModelSerializer):
    problem = ProblemForProblemSetSerializer(read_only=True)
    
    class Meta:
        model = ProblemSetMembership
        fields = ['problem', 'order']

class ProblemSetSerializer(serializers.ModelSerializer):
    problems_detail = ProblemSetMembershipSerializer(source='problemsetmembership_set', many=True, read_only=True)
    problems_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ProblemSet
        fields = [
            'slug', 'title', 'description', 'problems_detail', 'problems_count',
            'icon', 'is_public', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_by', 'created_at', 'updated_at']

class ProblemSetListSerializer(serializers.ModelSerializer):
    problems_count = serializers.ReadOnlyField()
    
    class Meta:
        model = ProblemSet
        fields = ['slug', 'title', 'description', 'icon', 'problems_count', 'is_public', 'created_at']

# Admin-specific serializers with more control
class AdminProblemSerializer(ProblemSerializer):
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    
    class Meta(ProblemSerializer.Meta):
        read_only_fields = ['created_at', 'updated_at']  # Allow editing slug and version

class AdminTestCaseSerializer(TestCaseSerializer):
    class Meta(TestCaseSerializer.Meta):
        fields = TestCaseSerializer.Meta.fields + ['created_at']