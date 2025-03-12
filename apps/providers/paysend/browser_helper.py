"""
Paysend Browser Automation Helper

This module provides browser automation capabilities to handle captcha challenges
and maintain authenticated sessions for the Paysend API integration.

USAGE GUIDE:
1. Automated Testing: In CI/CD environments where captchas cannot be manually solved,
   use a mock data fallback mechanism (as implemented in the integration.py).

2. Development Environment: Run the helper with headless=False to manually solve captchas
   and store cookies for future requests:
   
   ```python
   helper = PaysendBrowserHelper(headless=False, visible_for_seconds=30)
   result = await helper.get_quote("USD", "INR", 1000)
   print(result)
   ```

3. Production Environment:
   - Schedule a job to refresh cookies periodically during low-traffic hours
   - Consider integration with captcha-solving service APIs 
   - For scale, implement more sophisticated solutions with proxy rotation and
     multiple browser instances

IMPORTANT: Always comply with Paysend's terms of service and API usage policies.
This tool should not be used to bypass security measures in ways that violate
those terms.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Page, TimeoutError, async_playwright

logger = logging.getLogger(__name__)


class PaysendBrowserHelper:
    """
    Browser automation helper for Paysend API integration.

    This class uses Playwright to automate browser interactions with Paysend,
    handling captcha challenges and maintaining authenticated sessions.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout_seconds: int = 60,
        visible_for_seconds: int = 0,
        cookie_path: str = None,
    ):
        """
        Initialize the browser helper.

        Args:
            headless: Whether to run the browser in headless mode
            timeout_seconds: Maximum time to wait for operations
            visible_for_seconds: Time to keep browser visible after operations (for debugging)
            cookie_path: Path to store/load cookies
        """
        self.headless = headless
        self.timeout_seconds = timeout_seconds
        self.visible_for_seconds = visible_for_seconds
        self.cookie_path = cookie_path or os.path.join(
            os.path.dirname(__file__), "paysend_cookies.json"
        )

        self._playwright = None
        self._browser = None
        self._context = None
        self._browser_logs = []

        # Country name mappings for URL construction (ISO 2-letter code to URL-friendly name)
        self.COUNTRY_NAMES = {
            "US": "the-united-states-of-america",
            "IN": "india",
            "AM": "armenia",
            "DZ": "algeria",
            "GB": "the-united-kingdom",
            "CA": "canada",
            "AU": "australia",
            "DE": "germany",
            "FR": "france",
            "ES": "spain",
            "IT": "italy",
            "NL": "the-netherlands",
            "BE": "belgium",
            "CH": "switzerland",
            "AT": "austria",
            "SG": "singapore",
            "NZ": "new-zealand",
            "HK": "hong-kong",
            "JP": "japan",
            "KR": "south-korea",
            "TH": "thailand",
            "MY": "malaysia",
            "PH": "the-philippines",
            "ID": "indonesia",
            "CN": "china",
            "RU": "russia",
            "UA": "ukraine",
            "MX": "mexico",
            "BR": "brazil",
            "AR": "argentina",
            "CO": "colombia",
            "PE": "peru",
            "CL": "chile",
            "EG": "egypt",
            "ZA": "south-africa",
            "NG": "nigeria",
            "KE": "kenya",
            "GH": "ghana",
            "AE": "the-united-arab-emirates",
            "TR": "turkey",
            "SA": "saudi-arabia",
            "IL": "israel",
            "PK": "pakistan",
            "BD": "bangladesh",
            "LK": "sri-lanka",
            "NP": "nepal",
        }

        # Currency ID mappings (ISO code to numeric ID used by Paysend)
        self.CURRENCY_IDS = {
            "USD": "840",  # US Dollar
            "EUR": "978",  # Euro
            "GBP": "826",  # British Pound
            "CAD": "124",  # Canadian Dollar
            "AUD": "036",  # Australian Dollar
            "NZD": "554",  # New Zealand Dollar
            "JPY": "392",  # Japanese Yen
            "CHF": "756",  # Swiss Franc
            "HKD": "344",  # Hong Kong Dollar
            "SGD": "702",  # Singapore Dollar
            "AED": "784",  # UAE Dirham
            "SAR": "682",  # Saudi Riyal
            "INR": "356",  # Indian Rupee
            "PKR": "586",  # Pakistani Rupee
            "BDT": "050",  # Bangladeshi Taka
            "LKR": "144",  # Sri Lankan Rupee
            "NPR": "524",  # Nepalese Rupee
            "IDR": "360",  # Indonesian Rupiah
            "PHP": "608",  # Philippine Peso
            "THB": "764",  # Thai Baht
            "MYR": "458",  # Malaysian Ringgit
            "KRW": "410",  # South Korean Won
            "CNY": "156",  # Chinese Yuan
            "RUB": "643",  # Russian Ruble
            "UAH": "980",  # Ukrainian Hryvnia
            "MXN": "484",  # Mexican Peso
            "BRL": "986",  # Brazilian Real
            "ARS": "032",  # Argentine Peso
            "COP": "170",  # Colombian Peso
            "PEN": "604",  # Peruvian Sol
            "CLP": "152",  # Chilean Peso
            "EGP": "818",  # Egyptian Pound
            "ZAR": "710",  # South African Rand
            "NGN": "566",  # Nigerian Naira
            "KES": "404",  # Kenyan Shilling
            "GHS": "936",  # Ghanaian Cedi
            "TRY": "949",  # Turkish Lira
            "ILS": "376",  # Israeli Shekel
            "AMD": "051",  # Armenia Dram
            "DZD": "012",  # Algeria Dinar
        }

    async def __aenter__(self):
        """Context manager entry point"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point"""
        await self.close()

    async def start(self):
        """Initialize and start the browser"""
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-sandbox",
                ],
            )

            # Create a browser context with specific options to reduce fingerprinting
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                has_touch=False,
            )

            # Load cookies if they exist
            if os.path.exists(self.cookie_path):
                try:
                    with open(self.cookie_path, "r") as f:
                        cookies = json.load(f)
                        await self._context.add_cookies(cookies)
                        logger.info(f"Loaded {len(cookies)} cookies from {self.cookie_path}")
                except Exception as e:
                    logger.warning(f"Failed to load cookies: {str(e)}")

            return self
        except Exception as e:
            self._browser_logs.append(f"Browser startup error: {str(e)}")
            logger.error(f"Failed to start browser: {str(e)}")
            await self.close()
            raise

    async def close(self):
        """Close all browser resources"""
        try:
            if self._context:
                await self._context.close()
                self._context = None

            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

        except Exception as e:
            logger.warning(f"Error during browser cleanup: {str(e)}")

    async def save_cookies(self):
        """Save browser cookies to a file"""
        if not self._context:
            logger.warning("Cannot save cookies: Browser context not initialized")
            return False

        try:
            cookies = await self._context.cookies()
            with open(self.cookie_path, "w") as f:
                json.dump(cookies, f)
            logger.info(f"Saved {len(cookies)} cookies to {self.cookie_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {str(e)}")
            return False

    async def new_page(self) -> Tuple[Optional[Page], str]:
        """Create a new page with error handling"""
        if not self._context:
            error_msg = "Browser context not initialized"
            logger.error(error_msg)
            return None, error_msg

        try:
            page = await self._context.new_page()

            # Configure page to intercept console messages for logging
            page.on("console", lambda msg: self._browser_logs.append(f"CONSOLE: {msg.text}"))

            # Add event listeners for errors
            page.on("pageerror", lambda err: self._browser_logs.append(f"PAGE ERROR: {err}"))
            page.on("crash", lambda: self._browser_logs.append("PAGE CRASHED"))

            return page, ""
        except Exception as e:
            error_msg = f"Failed to create page: {str(e)}"
            self._browser_logs.append(error_msg)
            logger.error(error_msg)
            return None, error_msg

    async def navigate_to_paysend(self, retry_count: int = 2) -> Tuple[Optional[Page], str]:
        """Navigate to Paysend website with retry logic"""
        for attempt in range(retry_count + 1):
            try:
                page, error = await self.new_page()
                if not page:
                    return None, error

                # Construct a default URL for US to India as a fallback
                from_country_name = self.COUNTRY_NAMES.get("US", "the-united-states-of-america")
                to_country_name = self.COUNTRY_NAMES.get("IN", "india")
                from_curr_id = self.CURRENCY_IDS.get("USD", "840")
                to_curr_id = self.CURRENCY_IDS.get("INR", "356")

                default_url = f"https://paysend.com/en-us/send-money/from-{from_country_name}-to-{to_country_name}?fromCurrId={from_curr_id}&toCurrId={to_curr_id}&isFrom=true"

                logger.info(f"Navigating to default URL: {default_url}")

                await page.goto(
                    default_url,
                    wait_until="networkidle",
                    timeout=self.timeout_seconds * 1000,
                )

                # Check if we hit a captcha page
                if await self._is_captcha_page(page):
                    if self.headless:
                        return None, "Captcha detected in headless mode"
                    else:
                        logger.info("Captcha detected. Please solve it manually...")
                        # Wait for user to solve captcha
                        await asyncio.sleep(self.timeout_seconds)
                        if await self._is_captcha_page(page):
                            return None, "Captcha not solved within timeout"
                        logger.info("Captcha appears to be solved!")

                return page, ""

            except Exception as e:
                logger.warning(f"Navigation attempt {attempt+1}/{retry_count+1} failed: {str(e)}")
                if page:
                    await page.close()

                if attempt < retry_count:
                    await asyncio.sleep(2)
                else:
                    return (
                        None,
                        f"Navigation failed after {retry_count+1} attempts: {str(e)}",
                    )

    async def _is_captcha_page(self, page: Page) -> bool:
        """Check if the current page is a captcha challenge"""
        try:
            # Check for common captcha indicators
            captcha_selectors = [
                "#challenge-running",
                "iframe[src*='captcha']",
                "iframe[src*='cloudflare']",
                ".cf-browser-verification",
                "#cf-please-wait",
            ]

            for selector in captcha_selectors:
                if await page.locator(selector).count() > 0:
                    return True

            # Check page content for captcha keywords
            content = await page.content()
            captcha_keywords = [
                "captcha",
                "challenge",
                "security check",
                "cloudflare",
                "browser verification",
                "browser check",
            ]

            return any(keyword in content.lower() for keyword in captcha_keywords)

        except Exception as e:
            logger.warning(f"Error checking for captcha: {str(e)}")
            return False

    async def get_quote(
        self,
        from_currency: str,
        to_currency: str,
        amount: float,
        from_country: str = "US",
        to_country: str = "IN",
    ) -> Optional[Dict[str, Any]]:
        """
        Get a quote from Paysend using browser automation.

        Args:
            from_currency: Source currency code (e.g., "USD")
            to_currency: Destination currency code (e.g., "INR")
            amount: Amount to convert
            from_country: Source country code
            to_country: Destination country code

        Returns:
            Quote data dictionary or None if failed
        """
        if not self._browser:
            await self.start()

        # Build the proper URL with country and currency IDs
        # Get country names and currency IDs from our mappings
        from_country_name = self.COUNTRY_NAMES.get(from_country, from_country.lower())
        to_country_name = self.COUNTRY_NAMES.get(to_country, to_country.lower())
        from_curr_id = self.CURRENCY_IDS.get(from_currency, "840")  # Default to USD if not found
        to_curr_id = self.CURRENCY_IDS.get(to_currency)

        if not to_curr_id:
            logger.warning(f"Currency ID not found for {to_currency}, using default URL")
            page, error = await self.navigate_to_paysend()
        else:
            # Construct the URL with proper country names and currency IDs
            url = f"https://paysend.com/en-us/send-money/from-{from_country_name}-to-{to_country_name}?fromCurrId={from_curr_id}&toCurrId={to_curr_id}&isFrom=true"
            logger.info(f"Navigating to URL: {url}")

            page, error = await self.new_page()
            if page:
                try:
                    await page.goto(
                        url,
                        wait_until="networkidle",
                        timeout=self.timeout_seconds * 1000,
                    )

                    # Check if we hit a captcha page
                    if await self._is_captcha_page(page):
                        if self.headless:
                            await page.close()
                            return None, "Captcha detected in headless mode"
                        else:
                            logger.info("Captcha detected. Please solve it manually...")
                            # Wait for user to solve captcha
                            await asyncio.sleep(self.timeout_seconds)
                            if await self._is_captcha_page(page):
                                await page.close()
                                return None, "Captcha not solved within timeout"
                            logger.info("Captcha appears to be solved!")
                except Exception as e:
                    logger.error(f"Error navigating to {url}: {e}")
                    if page:
                        await page.close()
                    page, error = await self.navigate_to_paysend()

        if not page:
            logger.error(f"Failed to navigate to Paysend: {error}")
            self._browser_logs.append(f"Navigation error: {error}")
            return None

        try:
            # Try to interact with calculator form
            logger.info(f"Attempting to get quote for {from_currency} to {to_currency}")

            # Fill calculator form (implementation depends on actual Paysend UI)
            # This is a placeholder - actual implementation would need to adapt to Paysend's form
            await page.fill("#amount", str(amount))
            await page.select_option("#from-currency", from_currency)
            await page.select_option("#to-currency", to_currency)
            await page.click("#calculate-button")

            # Wait for results and extract data
            await page.wait_for_selector("#result-container", timeout=30000)

            # Extract quote data (implementation depends on actual Paysend UI)
            exchange_rate = await page.evaluate(
                "() => document.querySelector('#exchange-rate').textContent"
            )
            fee = await page.evaluate("() => document.querySelector('#fee').textContent")
            receive_amount = await page.evaluate(
                "() => document.querySelector('#receive-amount').textContent"
            )

            # Save cookies for future use
            await self.save_cookies()

            # Clean up
            await page.close()

            if self.visible_for_seconds > 0:
                logger.info(f"Keeping browser open for {self.visible_for_seconds} seconds")
                await asyncio.sleep(self.visible_for_seconds)

            return {
                "success": True,
                "exchange_rate": float(exchange_rate),
                "fee": float(fee),
                "receive_amount": float(receive_amount),
                "currency_from": from_currency,
                "currency_to": to_currency,
            }

        except Exception as e:
            if page:
                # Capture screenshot for debugging
                try:
                    screenshot_path = f"paysend_error_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"Error screenshot saved to {screenshot_path}")
                except Exception as screenshot_err:
                    logger.warning(f"Failed to capture error screenshot: {str(screenshot_err)}")

                # Close the page
                await page.close()

            logger.error(f"Error during quote retrieval: {str(e)}")
            self._browser_logs.append(f"Quote error: {str(e)}")

            return None

    def get_browser_logs(self) -> str:
        """Get browser logs as a string"""
        return "\n".join(self._browser_logs)


# Add the synchronous functions that are referenced in the integration.py file


def get_browser_cookies_sync() -> Optional[Dict]:
    """
    Synchronous wrapper for getting browser cookies.

    Returns:
        Dictionary of cookies or None if failed
    """
    # Path to cookie file
    cookie_path = os.path.join(os.path.dirname(__file__), "paysend_cookies.json")

    try:
        if os.path.exists(cookie_path):
            with open(cookie_path, "r") as f:
                cookies = json.load(f)
                return cookies
        return None
    except Exception as e:
        logger.error(f"Error getting browser cookies: {e}")
        return None


def run_browser_helper_sync(
    from_currency: str,
    to_currency: str,
    amount: float,
    from_country: str = "US",
    to_country: str = "IN",
    url: Optional[str] = None,
    headless: bool = True,
    timeout_seconds: int = 120,  # Increased timeout for manual captcha solving
) -> Optional[Dict[str, Any]]:
    """
    Synchronous wrapper for running browser automation to get a quote.

    Args:
        from_currency: Source currency code
        to_currency: Destination currency code
        amount: Amount to convert
        from_country: Source country code
        to_country: Destination country code
        url: Optional specific URL to navigate to
        headless: Whether to run browser in headless mode
        timeout_seconds: Timeout for browser operations

    Returns:
        Quote data dictionary or None if failed
    """
    try:
        # Create an event loop and run the async function
        result = asyncio.run(
            _run_browser_helper_async(
                from_currency=from_currency,
                to_currency=to_currency,
                amount=amount,
                from_country=from_country,
                to_country=to_country,
                url=url,
                headless=headless,
                timeout_seconds=timeout_seconds,
            )
        )
        return result
    except Exception as e:
        logger.error(f"Error running browser helper: {e}")
        return None


async def _run_browser_helper_async(
    from_currency: str,
    to_currency: str,
    amount: float,
    from_country: str = "US",
    to_country: str = "IN",
    url: Optional[str] = None,
    headless: bool = True,
    timeout_seconds: int = 120,
) -> Optional[Dict[str, Any]]:
    """
    Async function to run browser automation to get a quote.

    Args:
        from_currency: Source currency code
        to_currency: Destination currency code
        amount: Amount to convert
        from_country: Source country code
        to_country: Destination country code
        url: Optional specific URL to navigate to
        headless: Whether to run browser in headless mode
        timeout_seconds: Timeout for browser operations

    Returns:
        Quote data dictionary or None if failed
    """
    # Create browser helper with non-headless mode to allow manual captcha solving if needed
    helper = PaysendBrowserHelper(
        headless=headless,
        timeout_seconds=timeout_seconds,
        visible_for_seconds=30,  # Keep browser visible for 30 seconds after operation
    )

    try:
        # Start the browser
        await helper.start()

        # Get quote using the helper
        result = await helper.get_quote(
            from_currency=from_currency,
            to_currency=to_currency,
            amount=amount,
            from_country=from_country,
            to_country=to_country,
        )

        # Make sure to save cookies for future use
        await helper.save_cookies()

        return result
    except Exception as e:
        logger.error(f"Error in browser helper async: {e}")
        return None
    finally:
        # Make sure we close the browser
        await helper.close()
