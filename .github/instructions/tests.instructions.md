---
applyTo: "tests/**/test_*.py"
---

# Test Review Rules

## 1. Every test file must declare pytestmark

Unit tests and integration tests must be explicitly marked. Without `django_db`, pytest-django blocks database access and raises a clear error.

```python
# Unit test file
pytestmark = [pytest.mark.unit, pytest.mark.django_db]

# Integration test file
pytestmark = [pytest.mark.integration, pytest.mark.django_db]
```

Flag any test file missing `pytestmark`.

## 2. Use factories, never Model.objects.create()

All test data must come from Factory Boy factories in `tests/factories/__init__.py`. If no factory exists for a model, add one.

```python
# WRONG
user = User.objects.create_user(username="test", password="pass")
course = Course.objects.create(name="Test", slug="test")
# RIGHT
from tests.factories import UserFactory, CourseFactory
user = UserFactory()
course = CourseFactory()
```

## 3. Use conftest fixtures for common objects

Shared fixtures are defined in `tests/conftest.py`. Use them for standard objects like `user`, `admin_user`, `course`, `problem_set`, `problem`.

```python
# WRONG — recreating what conftest already provides
@pytest.fixture
def my_user():
    return UserFactory()

# RIGHT — use the shared fixture
def test_something(user, course):
    ...
```

## 4. CourseFactory does not accept instructor=

The `Course.instructor` FK was removed. Instructor assignment uses `CourseInstructorFactory`.

```python
# WRONG — will raise TypeError
course = CourseFactory(instructor=user)
# RIGHT
course = CourseFactory()
CourseInstructorFactory(course=course, user=user, role="primary")
```

## 5. Mock Firebase via get_firebase_service()

Never call Firebase directly in tests. Mock the service factory.

```python
# WRONG
from firebase_admin import auth
auth.delete_user(uid)
# RIGHT
@patch("purplex.users_app.utils.firebase.get_firebase_service")
def test_delete(mock_firebase):
    mock_firebase.return_value = MagicMock()
    ...
```

## 6. Use force_authenticate for auth

```python
# WRONG
client.credentials(HTTP_AUTHORIZATION="Bearer fake-token")
# RIGHT
api_client.force_authenticate(user=user)
```

## 7. Test file naming

Test files must follow `test_<feature>.py` convention. Flag files like `tests_feature.py` or `feature_test.py`.

## 8. Assert specific exceptions

```python
# WRONG — too broad, hides bugs
with pytest.raises(Exception):
    service.do_thing()
# RIGHT
with pytest.raises(NotFound, match="Course not found"):
    service.do_thing()
```

## 9. No shared state between tests

Each test must create its own data via factories or fixtures. Never rely on data created by another test. No module-level model instances.

```python
# WRONG — module-level state shared across tests
user = UserFactory()

class TestCourse:
    def test_a(self):
        course = CourseFactory()  # uses module-level user implicitly
# RIGHT
class TestCourse:
    def test_a(self):
        user = UserFactory()
        course = CourseFactory()
```

## 10. Privacy and FERPA test patterns

- Use `UserConsentFactory` and `AgeVerificationFactory` for consent tests
- For FERPA tests, set `directory_info_visible` on the user's profile:

```python
# Set up FERPA visibility
user = UserFactory()
user.profile.directory_info_visible = True
user.profile.save()
```

- Use fixtures from conftest: `user_consent`, `age_verification`, `minor_user`, `child_user`, `nominee`
