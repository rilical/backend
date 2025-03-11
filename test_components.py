#!/usr/bin/env python3
"""
Test script for RemitScout components.
This script tests the core functionality without requiring the API server to be running.
"""
import os
import sys
import logging
import json
import traceback
from decimal import Decimal
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'remit_scout.settings')
django.setup()

# Now import Django components
from django.core.cache import cache
from apps.aggregator.aggregator import Aggregator, get_provider_quote_cache_key
from quotes.models import FeeQuote, Provider, QuoteQueryLog
from quotes.signals import get_quote_cache_key, get_corridor_cache_key
from quotes.cache_utils import preload_corridor_caches, invalidate_all_quote_caches

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_providers():
    """Test the providers' ability to return quotes."""
    logger.info("Testing providers...")
    
    # Test parameters
    source_country = "US"
    dest_country = "MX"
    source_currency = "USD"
    dest_currency = "MXN"
    amount = Decimal("1000.00")
    
    try:
        # Call the aggregator to get quotes from providers
        result = Aggregator.get_all_quotes(
            source_country=source_country,
            dest_country=dest_country,
            source_currency=source_currency,
            dest_currency=dest_currency,
            amount=amount,
            use_cache=False
        )
        
        all_providers = len(result.get('all_results', []))
        successful_providers = len([p for p in result.get('results', []) if p.get('success', False)])
        
        logger.info(f"Tested {all_providers} providers")
        logger.info(f"Successful providers: {successful_providers}")
        logger.info(f"Failed providers: {all_providers - successful_providers}")
        
        if successful_providers > 0:
            logger.info("Provider test passed! At least one provider returned a quote.")
            
            # Print the successful providers
            for quote in result.get('results', []):
                if quote.get('success', False):
                    provider = quote.get('provider_id', 'Unknown')
                    rate = quote.get('exchange_rate', 'N/A')
                    fee = quote.get('fee', 'N/A')
                    logger.info(f"  • {provider}: Rate = {rate}, Fee = {fee}")
                    
            return True
        else:
            logger.info("All providers failed to return quotes. This may be expected if the providers are not properly configured.")
            return False
    
    except Exception as e:
        logger.error(f"Error testing providers: {str(e)}")
        traceback.print_exc()
        return False

def test_caching():
    """Test the caching functionality."""
    logger.info("Testing caching...")
    
    # Test parameters
    source_country = "US"
    dest_country = "MX"
    source_currency = "USD"
    dest_currency = "MXN"
    amount = Decimal("1000.00")
    
    # Generate cache keys
    quote_key = get_quote_cache_key(
        source_country, 
        dest_country, 
        source_currency, 
        dest_currency, 
        amount
    )
    corridor_key = get_corridor_cache_key(source_country, dest_country)
    
    logger.info(f"Quote cache key: {quote_key}")
    logger.info(f"Corridor cache key: {corridor_key}")
    
    # Test setting and getting cache values
    test_data = {"test": True, "timestamp": "2023-01-01T00:00:00Z"}
    cache.set(quote_key, test_data, timeout=60)
    
    # Get the value back
    cached_data = cache.get(quote_key)
    if cached_data and cached_data.get('test') is True:
        logger.info("Cache set/get test successful!")
    else:
        logger.error("Cache set/get test failed!")
        return False
    
    # Test cache invalidation
    invalidate_all_quote_caches()
    cached_data = cache.get(quote_key)
    if cached_data is None:
        logger.info("Cache invalidation test successful!")
    else:
        logger.error("Cache invalidation test failed!")
        return False
    
    return True

def test_database():
    """Test the database models."""
    logger.info("Testing database models...")
    
    # Test creating a provider
    provider_id = "TestProvider"
    try:
        provider, created = Provider.objects.get_or_create(
            id=provider_id,
            defaults={"name": "Test Provider"}
        )
        logger.info(f"Provider {'created' if created else 'already exists'}: {provider.id}")
        
        # Test creating a quote
        quote_count_before = FeeQuote.objects.count()
        
        quote = FeeQuote.objects.create(
            provider=provider,
            source_country="US",
            destination_country="MX",
            source_currency="USD",
            destination_currency="MXN",
            payment_method="Card",
            delivery_method="bank_deposit",
            send_amount=Decimal("1000.00"),
            fee_amount=Decimal("5.00"),
            exchange_rate=Decimal("18.50"),
            delivery_time_minutes=1440,
            destination_amount=Decimal("18500.00")
        )
        
        # Verify the quote was saved
        quote_count_after = FeeQuote.objects.count()
        if quote_count_after > quote_count_before:
            logger.info(f"Successfully created quote in database: {quote.id}")
        else:
            logger.error("Failed to create quote in database")
            return False
        
        # Test query log creation
        log_count_before = QuoteQueryLog.objects.count()
        
        log = QuoteQueryLog.objects.create(
            source_country="US",
            destination_country="MX",
            source_currency="USD",
            destination_currency="MXN",
            send_amount=Decimal("1000.00"),
            user_ip="127.0.0.1"
        )
        
        # Verify the log was saved
        log_count_after = QuoteQueryLog.objects.count()
        if log_count_after > log_count_before:
            logger.info(f"Successfully created query log in database: {log.id}")
        else:
            logger.error("Failed to create query log in database")
            return False
        
        # Clean up test data
        quote.delete()
        log.delete()
        if not created:
            # Don't delete if it existed before the test
            logger.info(f"Not deleting provider {provider.id} as it existed before the test")
        else:
            provider.delete()
            logger.info(f"Deleted test provider {provider.id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing database: {str(e)}")
        return False

def run_tests():
    """Run available tests."""
    tests = [
        ("Providers", test_providers),
        ("Caching", test_caching),
        ("Database", test_database)
    ]
    
    results = []
    
    print("\n" + "="*80)
    print("REMITSCOUT COMPONENT TESTS")
    print("="*80)
    print("\nThis script tests the core components of RemitScout.")
    print("\nNotice: Some tests might fail if Redis or PostgreSQL are not properly configured.")
    print("These failures don't necessarily mean the code is broken - just that the environment")
    print("might not be fully set up.\n")
    
    for name, test_func in tests:
        logger.info(f"\n{'=' * 50}\nRUNNING TEST: {name}\n{'=' * 50}")
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"Exception in {name} test: {str(e)}")
            traceback.print_exc()
            results.append((name, False))
    
    # Print summary
    logger.info("\n\n" + "=" * 50)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    
    all_passed = True
    for name, success in results:
        status = "PASSED" if success else "FAILED"
        all_passed = all_passed and success
        logger.info(f"{name}: {status}")
    
    # Print deployment steps
    print("\n" + "="*80)
    print("NEXT STEPS FOR DEPLOYMENT")
    print("="*80)
    print("""
To deploy RemitScout to production:

1. Configure PostgreSQL database:
   - Make sure PostgreSQL is running 
   - Create a database with: createdb remitscout
   - Apply migrations: python manage.py migrate

2. Configure Redis:
   - Install Redis server: brew install redis (MacOS) or apt install redis-server (Ubuntu)
   - Start Redis: redis-server

3. Test the API:
   - Start the Django server: python manage.py runserver
   - Test the endpoint: curl "http://localhost:8000/api/quotes/?source_country=US&dest_country=MX&source_currency=USD&dest_currency=MXN&amount=1000"

4. For production deployment:
   - Follow the deployment guide to deploy with Gunicorn/Nginx
   - Set up Celery for background tasks
   - Configure proper SSL/TLS
    """)
    
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 