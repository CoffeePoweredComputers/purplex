"""
Unit tests for the handler registry and base class.

Per-handler tests live in test_handlers_<type>.py files.
"""

import inspect
from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import (
    get_handler,
    get_registered_types,
    is_registered,
)
from purplex.problems_app.handlers.base import ActivityHandler

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestHandlerRegistry:
    """Tests for the handler registry."""

    def test_eipl_handler_registered(self):
        """EiPL handler should be registered on import."""
        assert is_registered("eipl")

    def test_get_registered_types_includes_eipl(self):
        """get_registered_types should include 'eipl'."""
        types = get_registered_types()
        assert "eipl" in types

    def test_get_unknown_handler_raises_value_error(self):
        """Requesting an unknown handler should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_handler("unknown_type")
        assert "Unknown activity type: unknown_type" in str(exc_info.value)

    def test_get_handler_returns_new_instance(self):
        """Each get_handler call should return a new instance."""
        handler1 = get_handler("eipl")
        handler2 = get_handler("eipl")
        assert handler1 is not handler2

    def test_handler_inherits_from_activity_handler(self):
        """Handler should inherit from ActivityHandler."""
        handler = get_handler("eipl")
        assert isinstance(handler, ActivityHandler)


# ─── process_submission() contract tests ─────────────────────


ASYNC_HANDLER_TYPES = [
    "eipl",
    "prompt",
    "debug_fix",
    "probeable_code",
    "probeable_spec",
]
SYNC_HANDLER_TYPES = ["mcq", "refute"]


class TestAsyncHandlersProcessSubmission:
    """Async handlers should inherit the base class default for process_submission()."""

    @pytest.fixture(params=ASYNC_HANDLER_TYPES)
    def handler(self, request):
        return get_handler(request.param)

    def test_raises_not_implemented_error(self, handler):
        """Calling process_submission() on an async handler should raise NotImplementedError."""
        mock_submission = MagicMock()
        mock_problem = MagicMock()

        with pytest.raises(NotImplementedError) as exc_info:
            handler.process_submission(mock_submission, "input", mock_problem)

        assert handler.type_name in str(exc_info.value)
        assert "Celery pipeline" in str(exc_info.value)

    def test_inherits_from_base_class(self, handler):
        """Async handlers should not override process_submission() — they inherit the base default."""
        assert "process_submission" not in type(handler).__dict__

    def test_error_message_includes_handler_type(self, handler):
        """Error message should identify which handler was called."""
        mock_submission = MagicMock()
        mock_problem = MagicMock()

        with pytest.raises(NotImplementedError, match=handler.type_name):
            handler.process_submission(mock_submission, "input", mock_problem)


class TestSyncHandlersProcessSubmission:
    """Sync handlers should have their own working process_submission()."""

    def test_mcq_has_own_process_submission(self):
        """MCQ handler should override process_submission()."""
        handler = get_handler("mcq")
        assert "process_submission" in type(handler).__dict__

    def test_refute_has_own_process_submission(self):
        """Refute handler should override process_submission()."""
        handler = get_handler("refute")
        assert "process_submission" in type(handler).__dict__


class TestBaseClassProcessSubmission:
    """Base class process_submission() default behavior."""

    def test_base_default_is_not_abstract(self):
        """process_submission should be a concrete method, not abstract."""
        method = ActivityHandler.process_submission
        assert not getattr(method, "__isabstractmethod__", False)
        # Should be a regular function, not decorated with @abstractmethod
        assert callable(method)
        # Verify it has a real implementation (not just `pass`)
        source = inspect.getsource(method)
        assert "NotImplementedError" in source
