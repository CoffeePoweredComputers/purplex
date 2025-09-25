"""
Test suite to ensure repository pattern compliance.

This test ensures:
1. Repositories don't return QuerySets (only structured data)
2. Services don't import Django ORM components
3. Complete data layer isolation is maintained
"""

import ast
import inspect
import os
import importlib
import pkgutil
from typing import List, Set, Tuple
from django.db.models import QuerySet
import pytest


class RepositoryPatternValidator:
    """Validates repository pattern implementation across the codebase."""
    
    def __init__(self):
        self.violations = []
        self.warnings = []
    
    def get_all_repository_classes(self):
        """Find all repository classes in the project."""
        repositories = []
        repo_path = 'purplex/problems_app/repositories'
        
        # Import all repository modules
        for filename in os.listdir(repo_path):
            if filename.endswith('_repository.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                module_path = f'purplex.problems_app.repositories.{module_name}'
                try:
                    module = importlib.import_module(module_path)
                    # Find repository classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            name.endswith('Repository') and 
                            obj.__module__ == module_path):
                            repositories.append(obj)
                except ImportError as e:
                    print(f"Could not import {module_path}: {e}")
        
        # Also check users_app repositories
        user_repo_path = 'purplex/users_app/repositories'
        if os.path.exists(user_repo_path):
            for filename in os.listdir(user_repo_path):
                if filename.endswith('_repository.py') and not filename.startswith('__'):
                    module_name = filename[:-3]
                    module_path = f'purplex.users_app.repositories.{module_name}'
                    try:
                        module = importlib.import_module(module_path)
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                name.endswith('Repository') and 
                                obj.__module__ == module_path):
                                repositories.append(obj)
                    except ImportError as e:
                        print(f"Could not import {module_path}: {e}")
        
        return repositories
    
    def check_repository_return_types(self, repo_class):
        """Check that repository methods don't return QuerySets."""
        violations = []
        
        for name, method in inspect.getmembers(repo_class, inspect.ismethod):
            if name.startswith('_'):  # Skip private methods
                continue
            
            # Get method signature and return annotation
            try:
                sig = inspect.signature(method)
                return_annotation = sig.return_annotation
                
                # Check if QuerySet is in the return type
                if return_annotation != inspect.Signature.empty:
                    annotation_str = str(return_annotation)
                    if 'QuerySet' in annotation_str:
                        violations.append(
                            f"{repo_class.__name__}.{name} returns QuerySet! "
                            f"Should return List[Dict], Dict, or domain objects."
                        )
            except Exception as e:
                print(f"Could not inspect {repo_class.__name__}.{name}: {e}")
        
        return violations
    
    def check_service_imports(self, service_file_path: str) -> List[str]:
        """Check that service files don't import Django ORM components."""
        violations = []
        forbidden_imports = [
            'from django.db.models import',
            'from django.db import',
            'import django.db.models',
            'import django.db',
        ]
        
        try:
            with open(service_file_path, 'r') as f:
                content = f.read()
                
            # Parse the Python file
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Check regular imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith('django.db'):
                            violations.append(
                                f"{service_file_path}: Imports {alias.name} "
                                f"(services should not import Django ORM)"
                            )
                
                # Check from imports
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith('django.db'):
                        # Allow TYPE_CHECKING imports (for type hints only)
                        # Check if this import is inside TYPE_CHECKING block
                        is_type_checking = False
                        for parent in ast.walk(tree):
                            if isinstance(parent, ast.If):
                                if (isinstance(parent.test, ast.Name) and 
                                    parent.test.id == 'TYPE_CHECKING'):
                                    if node in ast.walk(parent):
                                        is_type_checking = True
                                        break
                        
                        if not is_type_checking:
                            imported_items = ', '.join(alias.name for alias in node.names)
                            violations.append(
                                f"{service_file_path}: Imports {imported_items} from {node.module} "
                                f"(services should not import Django ORM)"
                            )
        except Exception as e:
            print(f"Could not parse {service_file_path}: {e}")
        
        return violations
    
    def check_service_method_calls(self, service_file_path: str) -> List[str]:
        """Check that services don't call ORM methods."""
        violations = []
        orm_methods = [
            'select_related', 'prefetch_related', 'annotate', 'aggregate',
            'values', 'values_list', 'exclude', 'order_by', 'distinct',
            'defer', 'only', 'using', 'select_for_update', 'raw'
        ]
        
        try:
            with open(service_file_path, 'r') as f:
                content = f.read()
            
            # Simple string search for ORM method calls
            for method in orm_methods:
                if f'.{method}(' in content:
                    # Check if it's not in a comment or string
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if f'.{method}(' in line and not line.strip().startswith('#'):
                            # Exclude lines that are clearly comments or docstrings
                            if not line.strip().startswith(('"""', "'''", '#')):
                                violations.append(
                                    f"{service_file_path}:{i}: Calls .{method}() "
                                    f"(services should not use ORM methods)"
                                )
        except Exception as e:
            print(f"Could not check {service_file_path}: {e}")
        
        return violations
    
    def validate_all(self):
        """Run all validation checks."""
        all_violations = []
        
        # Check repositories
        print("Checking repository return types...")
        repositories = self.get_all_repository_classes()
        for repo_class in repositories:
            violations = self.check_repository_return_types(repo_class)
            all_violations.extend(violations)
        
        # Check services
        print("Checking service layer isolation...")
        service_paths = [
            'purplex/problems_app/services',
            'purplex/users_app/services'
        ]
        
        for service_dir in service_paths:
            if os.path.exists(service_dir):
                for filename in os.listdir(service_dir):
                    if filename.endswith('_service.py'):
                        filepath = os.path.join(service_dir, filename)
                        
                        # Check imports
                        violations = self.check_service_imports(filepath)
                        all_violations.extend(violations)
                        
                        # Check method calls
                        violations = self.check_service_method_calls(filepath)
                        all_violations.extend(violations)
        
        return all_violations


class TestRepositoryPatternCompliance:
    """Test suite for repository pattern compliance."""
    
    def test_no_queryset_returns_in_repositories(self):
        """Ensure no repository method returns QuerySet."""
        validator = RepositoryPatternValidator()
        repositories = validator.get_all_repository_classes()
        
        all_violations = []
        for repo_class in repositories:
            violations = validator.check_repository_return_types(repo_class)
            all_violations.extend(violations)
        
        if all_violations:
            violation_report = '\n'.join(all_violations)
            pytest.fail(
                f"Repository pattern violations found:\n{violation_report}\n\n"
                "Repositories should return:\n"
                "- List[Dict] for collections\n"
                "- Dict for single records with computed fields\n"
                "- Domain objects (but NOT QuerySets)\n"
                "- Optional[Model] for single lookups (but converted to dict if complex)"
            )
    
    def test_no_orm_imports_in_services(self):
        """Ensure services don't import Django ORM components."""
        validator = RepositoryPatternValidator()
        
        all_violations = []
        service_paths = [
            'purplex/problems_app/services',
            'purplex/users_app/services'
        ]
        
        for service_dir in service_paths:
            if os.path.exists(service_dir):
                for filename in os.listdir(service_dir):
                    if filename.endswith('_service.py'):
                        filepath = os.path.join(service_dir, filename)
                        violations = validator.check_service_imports(filepath)
                        all_violations.extend(violations)
        
        if all_violations:
            violation_report = '\n'.join(all_violations)
            pytest.fail(
                f"Service layer isolation violations found:\n{violation_report}\n\n"
                "Services should NOT import:\n"
                "- django.db.models\n"
                "- django.db\n"
                "- Any Django ORM components\n\n"
                "Use TYPE_CHECKING for type hints only."
            )
    
    def test_no_orm_method_calls_in_services(self):
        """Ensure services don't call ORM methods."""
        validator = RepositoryPatternValidator()
        
        all_violations = []
        service_paths = [
            'purplex/problems_app/services',
            'purplex/users_app/services'
        ]
        
        for service_dir in service_paths:
            if os.path.exists(service_dir):
                for filename in os.listdir(service_dir):
                    if filename.endswith('_service.py'):
                        filepath = os.path.join(service_dir, filename)
                        violations = validator.check_service_method_calls(filepath)
                        all_violations.extend(violations)
        
        if all_violations:
            violation_report = '\n'.join(all_violations)
            pytest.fail(
                f"Service layer ORM usage violations found:\n{violation_report}\n\n"
                "Services should NOT call ORM methods like:\n"
                "- .select_related()\n"
                "- .prefetch_related()\n"
                "- .annotate()\n"
                "- .filter() (except on repository results)\n"
                "- .exclude()\n"
                "- etc.\n\n"
                "All database operations must go through repositories."
            )
    
    def test_repository_method_naming_conventions(self):
        """Ensure repository methods follow naming conventions."""
        validator = RepositoryPatternValidator()
        repositories = validator.get_all_repository_classes()
        
        violations = []
        expected_prefixes = [
            'get_', 'create_', 'update_', 'delete_', 'exists_', 
            'count_', 'search_', 'filter_', 'bulk_'
        ]
        
        for repo_class in repositories:
            for name, method in inspect.getmembers(repo_class, inspect.ismethod):
                if name.startswith('_'):  # Skip private methods
                    continue
                
                # Check if method name starts with expected prefix
                if not any(name.startswith(prefix) for prefix in expected_prefixes):
                    violations.append(
                        f"{repo_class.__name__}.{name} doesn't follow naming convention. "
                        f"Should start with: {', '.join(expected_prefixes)}"
                    )
        
        if violations:
            violation_report = '\n'.join(violations)
            pytest.fail(
                f"Repository naming convention violations:\n{violation_report}"
            )


if __name__ == '__main__':
    # Run validation directly
    validator = RepositoryPatternValidator()
    violations = validator.validate_all()
    
    if violations:
        print("\n❌ Repository Pattern Violations Found:\n")
        for violation in violations:
            print(f"  - {violation}")
        print(f"\nTotal violations: {len(violations)}")
    else:
        print("\n✅ No repository pattern violations found!")