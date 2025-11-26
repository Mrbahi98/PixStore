from django.apps import AppConfig
import logging

logger = logging.getLogger(name)


class StoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "store"

    def ready(self):
        """
        On startup, try to apply migrations.
        If DB is not ready, log the error but don't crash the app.
        """
        from django.core.management import call_command
        from django.db.utils import OperationalError, ProgrammingError

        try:
            call_command("migrate", interactive=False)
            logger.info("Auto-migrate executed successfully on startup.")
        except (OperationalError, ProgrammingError) as e:
            logger.error("Auto-migrate failed due to DB error: %s", e)
        except Exception:
            logger.exception("Unexpected error during auto-migrate on startup.")
