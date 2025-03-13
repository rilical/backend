from django.apps import AppConfig


class AggregatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aggregator'
    verbose_name = 'Aggregator'

    def ready(self):
        """
        Initialize the aggregator app when Django starts.
        """
        # Import any signals or initialization code here
        pass
