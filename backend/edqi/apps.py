from django.apps import AppConfig


class EdqiConfig(AppConfig):
    name = 'edqi'

    def ready(self):
        # Register the signal handlers
        import edqi.services.event_handler

