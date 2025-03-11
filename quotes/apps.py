from django.apps import AppConfig


class QuotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quotes'
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        This ensures that the signal connections are established.
        """
        import quotes.signals  # noqa 