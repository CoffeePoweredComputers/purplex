from django.apps import AppConfig


class ProblemsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "purplex.problems_app"

    def ready(self):
        """Import signal handlers when app is ready."""
        # Import signal handlers to register them (side-effect import)
        from . import signals  # noqa: F401
