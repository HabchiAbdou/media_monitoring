from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'

    def ready(self):
        """
        Ensure a superuser exists using environment variables:
        SUPERUSER_USERNAME / SUPERUSER_PASSWORD.
        """
        import os
        import sys
        from django.contrib.auth import get_user_model

        # Avoid running during migrations/collectstatic
        if any(cmd in sys.argv for cmd in ["migrate", "makemigrations", "collectstatic"]):
            return

        username = os.getenv("SUPERUSER_USERNAME")
        password = os.getenv("SUPERUSER_PASSWORD")
        if not username or not password:
            return

        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            try:
                User.objects.create_superuser(username=username, email="", password=password)
            except Exception:
                # Swallow errors to avoid startup failure; logs can capture if configured.
                return
