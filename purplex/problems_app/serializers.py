from rest_framework import serializers
from .models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership, Course, CourseProblemSet, CourseEnrollment
from .repositories.problem_category_repository import ProblemCategoryRepository
from .services.admin_service import AdminProblemService
from .handlers import get_handler, is_registered

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
            'function_name', 'function_signature', 'reference_solution',
            'memory_limit', 'tags', 'is_active', 'segmentation_enabled', 'segmentation_config',
            'requires_highlevel_comprehension', 'segmentation_threshold',
            'problem_sets', 'test_cases', 'test_cases_count', 'visible_test_cases_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'version',
            'mcq_options'  # MCQ-specific: array of {id, text, is_correct} objects
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
            'function_name', 'tags', 'is_active',
            'test_cases_count', 'created_at'
        ]

class ProblemForProblemSetSerializer(serializers.ModelSerializer):
    """Serializer for problems when displayed within a problem set context.
    Includes the reference solution for the code editor and handler-provided config."""
    categories = ProblemCategorySerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()
    visible_test_cases_count = serializers.ReadOnlyField()

    # Handler-provided configuration for frontend rendering
    display_config = serializers.SerializerMethodField()
    input_config = serializers.SerializerMethodField()
    hints_config = serializers.SerializerMethodField()
    feedback_config = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            'slug', 'title', 'description', 'difficulty', 'problem_type', 'categories',
            'function_name', 'function_signature', 'reference_solution',
            'tags', 'is_active', 'segmentation_enabled', 'segmentation_config',
            'test_cases_count', 'visible_test_cases_count',
            # Handler-provided config fields
            'display_config', 'input_config', 'hints_config', 'feedback_config'
        ]

    def _get_handler_config(self, problem):
        """Get full config from handler, cached per serialization."""
        if not hasattr(self, '_handler_config_cache'):
            self._handler_config_cache = {}
        if problem.pk not in self._handler_config_cache:
            if is_registered(problem.problem_type):
                handler = get_handler(problem.problem_type)
                self._handler_config_cache[problem.pk] = handler.get_problem_config(problem)
            else:
                self._handler_config_cache[problem.pk] = {}
        return self._handler_config_cache[problem.pk]

    def get_display_config(self, problem):
        """Get display configuration from handler."""
        return self._get_handler_config(problem).get('display', {})

    def get_input_config(self, problem):
        """Get input configuration from handler."""
        return self._get_handler_config(problem).get('input', {})

    def get_hints_config(self, problem):
        """Get hints configuration from handler."""
        return self._get_handler_config(problem).get('hints', {})

    def get_feedback_config(self, problem):
        """Get feedback configuration from handler."""
        return self._get_handler_config(problem).get('feedback', {})

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
    """Enhanced serializer for admin problem operations with test case handling"""
    
    # Read-only fields
    categories = serializers.SerializerMethodField()
    test_cases_count = serializers.ReadOnlyField()
    visible_test_cases_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    # Write-only fields
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    # Test cases handling
    test_cases = TestCaseSerializer(many=True, required=False)
    
    class Meta(ProblemSerializer.Meta):
        read_only_fields = ['created_at', 'updated_at']

    def get_categories(self, obj):
        """Get categories with proper serialization"""
        return ProblemCategorySerializer(obj.categories.all(), many=True).data

    def validate(self, attrs):
        """Comprehensive validation using validation service"""
        import logging
        logger = logging.getLogger(__name__)

        # MCQ-specific validation
        problem_type = attrs.get('problem_type', getattr(self.instance, 'problem_type', 'eipl') if self.instance else 'eipl')
        mcq_options = attrs.get('mcq_options', [])

        if problem_type == 'mcq':
            # Validate MCQ options
            if not mcq_options:
                raise serializers.ValidationError({
                    'mcq_options': ['MCQ problems require at least 2 options']
                })

            if not isinstance(mcq_options, list):
                raise serializers.ValidationError({
                    'mcq_options': ['mcq_options must be a list']
                })

            # Filter out empty options (no text)
            valid_options = [opt for opt in mcq_options if opt.get('text', '').strip()]

            if len(valid_options) < 2:
                raise serializers.ValidationError({
                    'mcq_options': ['MCQ problems require at least 2 options with text']
                })

            if len(valid_options) > 6:
                raise serializers.ValidationError({
                    'mcq_options': ['MCQ problems can have at most 6 options']
                })

            # Validate option structure and count correct answers
            correct_count = 0
            for i, option in enumerate(valid_options):
                if not isinstance(option, dict):
                    raise serializers.ValidationError({
                        'mcq_options': [f'Option {i+1} must be an object']
                    })

                if not option.get('id'):
                    raise serializers.ValidationError({
                        'mcq_options': [f'Option {i+1} must have an id']
                    })

                if not option.get('text', '').strip():
                    raise serializers.ValidationError({
                        'mcq_options': [f'Option {i+1} must have text']
                    })

                if option.get('is_correct', False):
                    correct_count += 1

            if correct_count != 1:
                raise serializers.ValidationError({
                    'mcq_options': [f'Exactly one option must be marked as correct (found {correct_count})']
                })

            # Store only valid options
            attrs['mcq_options'] = valid_options
        else:
            # For non-MCQ problems, clear mcq_options
            attrs['mcq_options'] = []

        try:
            from .services.validation_service import ProblemValidationService

            validation_service = ProblemValidationService()

            # Validate problem data
            validation_result = validation_service.validate_problem_data(attrs)
            if not validation_result.is_valid:
                error_dict = {}
                for error in validation_result.errors:
                    if error.field not in error_dict:
                        error_dict[error.field] = []
                    error_dict[error.field].append(error.message)
                raise serializers.ValidationError(error_dict)

            return attrs
        except serializers.ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            # Log the error for debugging but don't fail validation
            logger.warning(f"Validation service error: {str(e)}")

            # Perform basic validation instead
            if not attrs.get('title', '').strip():
                raise serializers.ValidationError({'title': ['Title is required']})

            # For MCQ problems, reference_solution is optional
            if problem_type != 'mcq':
                if not attrs.get('reference_solution', '').strip():
                    raise serializers.ValidationError({'reference_solution': ['Reference solution is required']})

            return attrs

    def create(self, validated_data):
        """Create problem with test cases in a transaction"""
        from django.db import transaction
        import re

        test_cases_data = validated_data.pop('test_cases', [])
        category_ids = validated_data.pop('category_ids', [])

        # Auto-extract function_name from reference_solution if not provided
        # function_signature is now required and must be provided explicitly for test case parsing
        reference_solution = validated_data.get('reference_solution', '')
        if reference_solution:
            # Extract function_name if not provided
            if not validated_data.get('function_name'):
                func_name_match = re.match(r'def\s+(\w+)\s*\(', reference_solution)
                if func_name_match:
                    validated_data['function_name'] = func_name_match.group(1)

        # Ensure description has a default value if not provided (field is deprecated)
        if 'description' not in validated_data or not validated_data['description']:
            validated_data['description'] = ''

        # Automatically set requires_highlevel_comprehension for EiPL problems with segmentation
        if validated_data.get('problem_type') == 'eipl':
            segmentation_config = validated_data.get('segmentation_config', {})
            # If segmentation is enabled (or not explicitly disabled), require high-level comprehension
            if segmentation_config.get('enabled', True):
                validated_data['requires_highlevel_comprehension'] = True
            else:
                validated_data['requires_highlevel_comprehension'] = False

        with transaction.atomic():
            # Create the problem using service
            problem = AdminProblemService.create_problem(validated_data)
            
            # Set categories using service
            if category_ids:
                categories = AdminProblemService.get_categories_by_ids(category_ids)
                problem.categories.set(categories)
            
            # Create test cases using service
            for order, test_case_data in enumerate(test_cases_data):
                test_case_data['order'] = order
                AdminProblemService.create_test_case(problem, test_case_data)
            
            return problem

    def update(self, instance, validated_data):
        """Update problem with test cases in a transaction"""
        from django.db import transaction
        import re

        test_cases_data = validated_data.pop('test_cases', None)
        category_ids = validated_data.pop('category_ids', None)

        # Auto-extract function_name from reference_solution if not provided
        # function_signature is now required and must be provided explicitly for test case parsing
        reference_solution = validated_data.get('reference_solution', instance.reference_solution)
        if reference_solution:
            # Extract function_name if not provided
            if 'function_name' not in validated_data or not validated_data.get('function_name'):
                func_name_match = re.match(r'def\s+(\w+)\s*\(', reference_solution)
                if func_name_match:
                    validated_data['function_name'] = func_name_match.group(1)

        # Automatically set requires_highlevel_comprehension for EiPL problems with segmentation
        problem_type = validated_data.get('problem_type', instance.problem_type)
        if problem_type == 'eipl':
            segmentation_config = validated_data.get('segmentation_config', instance.segmentation_config)
            # If segmentation is enabled (or not explicitly disabled), require high-level comprehension
            if segmentation_config.get('enabled', True):
                validated_data['requires_highlevel_comprehension'] = True
            else:
                validated_data['requires_highlevel_comprehension'] = False

        with transaction.atomic():
            # Update problem fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            # Increment version
            instance.version += 1
            instance.save()
            
            # Update categories if provided using service
            if category_ids is not None:
                categories = AdminProblemService.get_categories_by_ids(category_ids)
                instance.categories.set(categories)
            
            # Update test cases if provided
            if test_cases_data is not None:
                # Delete existing test cases
                instance.test_cases.all().delete()
                
                # Create new test cases using service
                for order, test_case_data in enumerate(test_cases_data):
                    test_case_data['order'] = order
                    AdminProblemService.create_test_case(instance, test_case_data)
            
            return instance

    def to_representation(self, instance):
        """Custom representation with proper test case serialization"""
        data = super().to_representation(instance)
        
        # Include test cases with proper serialization
        test_cases = instance.test_cases.all().order_by('order')
        data['test_cases'] = TestCaseSerializer(test_cases, many=True).data
        
        return data

class AdminTestCaseSerializer(TestCaseSerializer):
    class Meta(TestCaseSerializer.Meta):
        fields = TestCaseSerializer.Meta.fields + ['created_at']


# Course-related serializers
class CourseProblemSetSerializer(serializers.ModelSerializer):
    """Serializer for problem sets within a course context"""
    problem_set = ProblemSetSerializer(read_only=True)
    
    class Meta:
        model = CourseProblemSet
        fields = ['id', 'problem_set', 'order', 'is_required', 'added_at']


class CourseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing courses"""
    instructor_name = serializers.SerializerMethodField()
    problem_sets_count = serializers.IntegerField(read_only=True)
    enrolled_students_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'course_id', 'slug', 'name', 'description',
            'instructor_name', 'problem_sets_count', 'enrolled_students_count',
            'is_active', 'enrollment_open', 'created_at'
        ]

    def get_instructor_name(self, obj):
        """Get instructor's full name or username"""
        return obj.instructor.get_full_name() or obj.instructor.username


class CourseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for course with problem sets"""
    instructor = serializers.SerializerMethodField()
    problem_sets = serializers.SerializerMethodField()
    enrolled_students_count = serializers.IntegerField(source='enrollments.filter(is_active=True).count', read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_id', 'slug', 'name', 'description',
            'instructor', 'problem_sets', 'enrolled_students_count',
            'is_active', 'enrollment_open', 'created_at', 'updated_at'
        ]
    
    def get_instructor(self, obj):
        return {
            'id': obj.instructor.id,
            'username': obj.instructor.username,
            'full_name': obj.instructor.get_full_name() or obj.instructor.username,
            'email': obj.instructor.email
        }
    
    def get_problem_sets(self, obj):
        """Get problem sets ordered by position in course"""
        course_problem_sets = obj.courseproblemset_set.select_related('problem_set').order_by('order')
        return [{
            'id': cps.id,
            'order': cps.order,
            'is_required': cps.is_required,
            'problem_set': ProblemSetListSerializer(cps.problem_set).data
        } for cps in course_problem_sets]


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating courses"""
    instructor_id = serializers.IntegerField(write_only=True, required=False)
    problem_set_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Course
        fields = [
            'course_id', 'name', 'description', 'instructor_id',
            'is_active', 'enrollment_open', 'problem_set_ids'
        ]
    
    def validate_course_id(self, value):
        """Validate course ID format"""
        if not value:
            raise serializers.ValidationError("Course ID is required")
        
        # Check format (alphanumeric with hyphens/underscores)
        import re
        if not re.match(r'^[A-Za-z0-9_-]+$', value):
            raise serializers.ValidationError(
                "Course ID can only contain letters, numbers, hyphens, and underscores"
            )
        
        # Check uniqueness using service (exclude current instance for updates)
        if self.instance:
            # For updates, check if another course has this ID
            exists = AdminProblemService.check_course_exists(value)
            if exists and self.instance.course_id != value:
                raise serializers.ValidationError("A course with this ID already exists")
        else:
            # For creation, check if any course has this ID
            if AdminProblemService.check_course_exists(value):
                raise serializers.ValidationError("A course with this ID already exists")
        
        return value
    
    def create(self, validated_data):
        problem_set_ids = validated_data.pop('problem_set_ids', [])
        # Create course using service
        course = AdminProblemService.create_course(validated_data)
        
        # Add problem sets with ordering using service
        for order, ps_id in enumerate(problem_set_ids):
            problem_set = AdminProblemService.get_problem_set_by_id(ps_id)
            if problem_set:
                AdminProblemService.create_course_problem_set(
                    course=course,
                    problem_set=problem_set,
                    order=order
                )
        
        return course
    
    def update(self, instance, validated_data):
        problem_set_ids = validated_data.pop('problem_set_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update problem sets if provided
        if problem_set_ids is not None:
            # Clear existing
            instance.courseproblemset_set.all().delete()
            
            # Add new ones using service
            for order, ps_id in enumerate(problem_set_ids):
                problem_set = AdminProblemService.get_problem_set_by_id(ps_id)
                if problem_set:
                    AdminProblemService.create_course_problem_set(
                        course=instance,
                        problem_set=problem_set,
                        order=order
                    )
        
        return instance


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for course enrollments"""
    user = serializers.SerializerMethodField()
    course = CourseListSerializer(read_only=True)
    
    class Meta:
        model = CourseEnrollment
        fields = ['id', 'user', 'course', 'enrolled_at', 'is_active']
    
    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': obj.user.get_full_name() or obj.user.username,
            'email': obj.user.email
        }


class CourseLookupSerializer(serializers.Serializer):
    """Serializer for course lookup requests"""
    course_id = serializers.CharField(required=True)


class CourseEnrollSerializer(serializers.Serializer):
    """Serializer for course enrollment requests"""
    course_id = serializers.CharField(required=True)