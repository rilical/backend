from django.apps import AppConfig


class ProvidersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'providers'
    verbose_name = 'Providers'

    def ready(self):
        """
        Initialize the providers app when Django starts.
        """
        # Import any signals or initialization code here
        pass
