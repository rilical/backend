import logging
import os
import sys
from datetime import datetime
from decimal import Decimal

from tabulate import tabulate

from aggregator.aggregator import Aggregator


def print_header(title):
    """Print a formatted header with the title centered"""
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        # Default width when running in non-interactive terminal
        terminal_width = 80

    print("\n" + "=" * terminal_width)
    print(title.center(terminal_width))
    print("=" * terminal_width)


def analyze_error_message(error_message: str) -> str:
    """
    Classify error_message strings into more descriptive categories
    (e.g. 'Unsupported corridor', 'Timeout', 'General error').
    """
    if not error_message:
        return "Unknown error"

    em_lower = error_message.lower()
    if "unsupported" in em_lower or "not support" in em_lower:
        return "🛑 Unsupported corridor"
    elif "timeout" in em_lower:
        return "⏰ Timeout"
    elif "Exception" in em_lower:
        return "💥 Exception"
    elif "could not" in em_lower or "failed" in em_lower or "error" in em_lower:
        return "❌ Error"
    else:
        return "❌ General failure"


def test_uk_india_corridor():
    """Test aggregator for UK→India (GBP→INR) with detailed table output."""
    # Configure logging to both console and file
    log_filename = f"uk_india_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    print_header("REMITSCOUT PROVIDER TEST: UK → INDIA (GBP → INR)")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"Logging output to: {log_filename}\n")

    # Test parameters
    test_params = {
        "source_country": "GB",  # Using the standard ISO code for UK
        "dest_country": "IN",
        "source_currency": "GBP",
        "dest_currency": "INR",
        "amount": Decimal("500.00"),
        # Exclude providers known not to support this corridor (if you like)
        "exclude_providers": [],
        "max_workers": 10,
        "sort_by": "best_rate",
    }

    logger.info(f"Testing UK->India corridor with parameters: {test_params}")

    start_time = datetime.now()
    result = Aggregator.get_all_quotes(**test_params)
    elapsed_time = (datetime.now() - start_time).total_seconds()

    logger.info(f"Got results in {elapsed_time:.2f} seconds")
    logger.debug(f"Raw result: {result}")

    table_data = []
    provider_count = len(result.get("all_results", []))
    success_count = 0

    # Keep track of working vs. non-working providers
    working_providers = []
    nonworking_providers = []

    logger.info(f"Processing results for {provider_count} providers")

    for provider in result.get("all_results", []):
        if not isinstance(provider, dict):
            logger.warning(f"Skipping invalid provider result: {provider}")
            continue  # skip if invalid result
        provider_id = provider.get("provider_id", "Unknown Provider")

        is_success = provider.get("success", False)
        if is_success:
            success_count += 1
            status = "✅ Success"

            # Extract numeric fields if present
            exchange_rate = provider.get("exchange_rate", "N/A")
            fee = provider.get("fee", "N/A")
            dest_amount = provider.get("destination_amount", "N/A")
            delivery_time = provider.get("delivery_time_minutes", "N/A")

            logger.info(
                f"Provider {provider_id} succeeded with rate: {exchange_rate}, fee: {fee}, "
                f"destination amount: {dest_amount}, delivery time: {delivery_time}"
            )

            # Make them strings if numeric
            exchange_rate_str = (
                f"{exchange_rate:.4f}"
                if isinstance(exchange_rate, (int, float, Decimal))
                else "N/A"
            )
            fee_str = f"£{fee:.2f}" if isinstance(fee, (int, float, Decimal)) else "N/A"
            dest_amount_str = (
                f"₹{dest_amount:.2f}" if isinstance(dest_amount, (int, float, Decimal)) else "N/A"
            )
            delivery_time_str = (
                f"{delivery_time} min" if isinstance(delivery_time, (int, float)) else "N/A"
            )

            row = [
                provider_id,
                status,
                exchange_rate_str,
                fee_str,
                dest_amount_str,
                delivery_time_str,
            ]
            working_providers.append(provider_id)
        else:
            status = "❌ Failed"
            error_msg = provider.get("error_message", "Unknown error")
            error_reason = analyze_error_message(error_msg)
            logger.warning(f"Provider {provider_id} failed with error: {error_msg}")
            row = [provider_id, status, "N/A", "N/A", "N/A", error_reason]
            nonworking_providers.append(provider_id)

        table_data.append(row)

    # Print the main table
    print_header("TEST RESULTS")
    headers = ["Provider", "Status", "Rate", "Fee", "Recipient Gets", "Details"]
    print(f"\nCorridor: UK→India / GBP→INR (Amount: £500.00)")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Summaries
    print_header("PROVIDER SUPPORT SUMMARY")
    # Working table
    print("\n✅ WORKING PROVIDERS")
    if working_providers:
        working_table = [[i, p] for i, p in enumerate(working_providers, 1)]
        print(tabulate(working_table, headers=["#", "Provider ID"], tablefmt="simple"))
    else:
        print("No working providers in this corridor.")

    # Non-working table
    print("\n❌ NON-WORKING PROVIDERS")
    if nonworking_providers:
        # We already have their errors from the main table,
        # so we can just list them by provider ID
        nonworking_table = [[i, p] for i, p in enumerate(nonworking_providers, 1)]
        print(tabulate(nonworking_table, headers=["#", "Provider ID"], tablefmt="simple"))
    else:
        print("All tested providers succeeded for this corridor!")

    # Summary
    print_header("SUMMARY")
    print(f"Total Providers: {provider_count}")
    print(f"Successful Providers: {success_count}")
    print(f"Failed Providers: {provider_count - success_count}")
    if provider_count > 0:
        print(f"Success Rate: {(success_count/provider_count)*100:.1f}%")
    print(f"Total Execution Time: {elapsed_time:.2f} seconds")

    logger.info(f"Test completed with {success_count}/{provider_count} successful providers")

    # Instead of failing if aggregator 'success' is false,
    # pass if at least one provider succeeded
    if success_count == 0:
        logger.error("No providers succeeded for this corridor!")
        raise AssertionError("No providers succeeded for this corridor!")

    # Check if RemitGuru provider worked specifically
    remitguru_result = next(
        (p for p in result.get("all_results", []) if p.get("provider_id") == "remitguru"),
        None,
    )
    if remitguru_result:
        remitguru_success = remitguru_result.get("success", False)
        if remitguru_success:
            logger.info("RemitGuru provider successfully handled the UK to India corridor")
        else:
            error_msg = remitguru_result.get("error_message", "Unknown error")
            logger.warning(f"RemitGuru provider failed with error: {error_msg}")
    else:
        logger.warning("RemitGuru provider was not found in the results")

    print("\n✅ Test completed successfully!")
    print(f"\nDetailed log file saved to: {log_filename}")


if __name__ == "__main__":
    test_uk_india_corridor()
