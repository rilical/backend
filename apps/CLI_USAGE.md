# RemitScout CLI Usage Guide

## Overview

The RemitScout command-line interface (CLI) provides a convenient way to compare remittance rates across multiple providers without having to visit each provider's website individually. This guide will walk you through common usage scenarios and examples.

## Quick Start

To get a quick comparison of remittance rates for sending money from the US to India:

```bash
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR
```

This will display a table of available providers, sorted by the best exchange rate by default.

## Basic Options

The RemitScout CLI requires the following parameters:

- `--amount`: The amount you want to send
- `--from-country`: The source country code (e.g., US, GB, CA)
- `--to-country`: The destination country code (e.g., IN, MX, PH)
- `--from-currency`: The source currency code (e.g., USD, GBP, CAD)
- `--to-currency`: The destination currency code (e.g., INR, MXN, PHP)

## Sorting and Filtering

You can customize how results are sorted and filtered:

### Sorting Options

```bash
# Sort by lowest fee
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --sort-by lowest_fee

# Sort by fastest delivery time
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --sort-by fastest_time
```

### Filtering by Fee or Delivery Time

```bash
# Only show providers with fees under $5
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --max-fee 5

# Only show providers that deliver within 24 hours
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --max-delivery-time 24
```

## Working with Providers

### Listing All Available Providers

To see all available providers and their status:

```bash
python3 apps/cli.py --list-providers
```

### Including or Excluding Specific Providers

```bash
# Exclude specific providers
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --exclude-providers PangeaProvider,MukuruProvider,DahabshiilProvider

# Only include specific providers
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --include-only WiseProvider,XEProvider,RemitlyProvider
```

## Advanced Options

### Output Options

```bash
# Output in JSON format
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --json

# Save output to a file
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --output-file results.txt
```

### Performance Options

```bash
# Set timeout for provider requests
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --timeout 45

# Set maximum concurrent workers
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --max-workers 10

# Disable caching
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --disable-cache
```

### Saving Configuration

You can save your configuration for future use:

```bash
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --exclude-providers PangeaProvider,MukuruProvider --save-config
```

The next time you run the CLI, it will use these settings as defaults.

## Common Use Cases

### Finding the Cheapest Way to Send Money

```bash
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --sort-by best_rate --max-fee 10
```

### Finding the Fastest Way to Send Money

```bash
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --sort-by fastest_time --max-delivery-time 24
```

### Finding the Option with No Fees

```bash
python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --max-fee 0
```

## Popular Corridors

### US to Mexico

```bash
python3 apps/cli.py --amount 500 --from-country US --to-country MX --from-currency USD --to-currency MXN
```

### US to Philippines

```bash
python3 apps/cli.py --amount 300 --from-country US --to-country PH --from-currency USD --to-currency PHP
```

### UK to India

```bash
python3 apps/cli.py --amount 800 --from-country GB --to-country IN --from-currency GBP --to-currency INR
```

### Canada to India

```bash
python3 apps/cli.py --amount 1200 --from-country CA --to-country IN --from-currency CAD --to-currency INR
```

## Troubleshooting

If you encounter errors or no results:

1. Check that your country codes and currency codes are valid
2. Try disabling problematic providers with `--exclude-providers`
3. Try running with the `--json` flag to see raw results
4. Increase the timeout with `--timeout 60` for slower providers
5. Make sure you're connected to the internet and not behind a restrictive firewall

For more help or to report issues, please contact the RemitScout team or open an issue on the GitHub repository. 