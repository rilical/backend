"""
Management command for cache operations.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from quotes.cache_utils import (
    invalidate_all_quote_caches,
    invalidate_corridor_caches,
    invalidate_provider_caches,
    preload_corridor_caches
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Utility command for cache operations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['invalidate_all', 'invalidate_corridor', 'invalidate_provider', 'preload_corridors'],
            required=True,
            help='The cache operation to perform'
        )
        parser.add_argument(
            '--source_country',
            help='Source country for corridor operations'
        )
        parser.add_argument(
            '--dest_country',
            help='Destination country for corridor operations'
        )
        parser.add_argument(
            '--provider_id',
            help='Provider ID for provider operations'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'invalidate_all':
                invalidate_all_quote_caches()
                self.stdout.write(self.style.SUCCESS('Successfully invalidated all quote caches'))
                
            elif action == 'invalidate_corridor':
                source_country = options.get('source_country')
                dest_country = options.get('dest_country')
                
                invalidate_corridor_caches(source_country, dest_country)
                
                if source_country and dest_country:
                    msg = f'Successfully invalidated corridor cache for {source_country}->{dest_country}'
                elif source_country:
                    msg = f'Successfully invalidated all corridor caches from {source_country}'
                elif dest_country:
                    msg = f'Successfully invalidated all corridor caches to {dest_country}'
                else:
                    msg = 'Successfully invalidated all corridor caches'
                    
                self.stdout.write(self.style.SUCCESS(msg))
                
            elif action == 'invalidate_provider':
                provider_id = options.get('provider_id')
                
                invalidate_provider_caches(provider_id)
                
                if provider_id:
                    msg = f'Successfully invalidated provider cache for {provider_id}'
                else:
                    msg = 'Successfully invalidated all provider caches'
                    
                self.stdout.write(self.style.SUCCESS(msg))
                
            elif action == 'preload_corridors':
                count = preload_corridor_caches()
                self.stdout.write(self.style.SUCCESS(f'Successfully preloaded {count} corridor caches'))
                
        except Exception as e:
            logger.exception(f"Error in cache_utils command: {str(e)}")
            raise CommandError(f'An error occurred: {str(e)}') 