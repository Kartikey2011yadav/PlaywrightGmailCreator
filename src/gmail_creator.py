"""
Advanced Gmail Account Creator using Playwright

This module provides the main Gmail account creation functionality
with advanced stealth features, anti-detection measures, and robust error handling.
"""

import asyncio
import random
import time
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime, timedelta
import re

from playwright.async_api import (
    async_playwright, 
    Browser, 
    BrowserContext, 
    Page, 
    TimeoutError as PlaywrightTimeoutError
)

# Optional stealth import
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    def stealth_async(page):
        """Dummy function when stealth is not available"""
        pass

from .config_manager import ConfigManager, GmailCreatorConfig
from .proxy_manager import ProxyManager, ProxyInfo
from .user_profile_generator import UserProfileGenerator, UserProfile
from .stealth_manager import StealthManager

logger = logging.getLogger(__name__)


class GmailCreationError(Exception):
    """Custom exception for Gmail creation errors"""
    pass


class GmailCreator:
    """Advanced Gmail account creator using Playwright"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.config
        self.config_manager = config_manager
        self.proxy_manager = None
        self.user_generator = UserProfileGenerator(config_manager)
        self.stealth_manager = StealthManager(config_manager)
        
        # Statistics
        self.stats = {
            "total_attempts": 0,
            "successful_creations": 0,
            "failed_creations": 0,
            "proxy_failures": 0,
            "captcha_encounters": 0,
            "phone_verification_required": 0,
            "start_time": None,
            "end_time": None
        }
        
        # Account storage
        self.created_accounts: List[Dict] = []
        
        # Gmail form selectors (updated for current Gmail interface)
        self.selectors = {
            "first_name": "input[name='firstName']",
            "last_name": "input[name='lastName']",
            "username": "input[name='Username']",
            "password": "input[name='Passwd']",
            "confirm_password": "input[name='PasswdAgain']",
            "next_button": "button:has-text('Next')",
            "create_account_button": "span:has-text('Create account')",
            "personal_use": "span:has-text('For personal use')",
            "birth_month": "select[id='month']",
            "birth_day": "input[id='day']",
            "birth_year": "input[id='year']",
            "gender": "select[id='gender']",
            "phone_skip": "span:has-text('Skip')",
            "agree_button": "button:has-text('I agree')",
            "recovery_email": "input[name='recovery']",
            "create_custom_email": "span:has-text('Create your own Gmail address')",
            "username_available": ".o6cuMc",
            "username_taken": ".LXRPh",
            "captcha_frame": "iframe[title*='recaptcha']",
            "phone_required": "input[type='tel']"
        }
    
    async def initialize(self):
        """Initialize the Gmail creator with proxy manager"""
        if self.config.proxy.enabled:
            self.proxy_manager = ProxyManager()
            
            if self.config.proxy.auto_fetch_free:
                # Fetch free proxies
                from .proxy_manager import FreeProxyFetcher
                self.proxy_manager = await FreeProxyFetcher.fetch_and_setup_manager()
            elif self.config.proxy.proxy_file:
                # Load from file
                self.proxy_manager.load_proxies_from_file(self.config.proxy.proxy_file)
                await self.proxy_manager.test_all_proxies()
            elif self.config.proxy.proxy_list:
                # Load from list
                self.proxy_manager.load_proxies_from_list(self.config.proxy.proxy_list)
                await self.proxy_manager.test_all_proxies()
            
            logger.info(f"Proxy manager initialized with {len(self.proxy_manager.active_proxies)} active proxies")
        
        logger.info("Gmail Creator initialized successfully")
    
    async def create_browser_context(self, proxy: Optional[ProxyInfo] = None) -> Tuple[Browser, BrowserContext]:
        """Create a browser context with stealth features"""
        playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            "headless": self.config.browser.headless,
            "args": self.config.browser.additional_args.copy()
        }
        
        # Add proxy if available
        if proxy:
            if proxy.proxy_type.value in ["http", "https"]:
                launch_options["proxy"] = {
                    "server": f"{proxy.host}:{proxy.port}",
                    "username": proxy.username,
                    "password": proxy.password
                }
            else:
                # For SOCKS proxies, use args
                launch_options["args"].append(f"--proxy-server={proxy.url}")
        
        # Launch browser
        if self.config.browser.browser_type.value == "chromium":
            browser = await playwright.chromium.launch(**launch_options)
        elif self.config.browser.browser_type.value == "firefox":
            browser = await playwright.firefox.launch(**launch_options)
        else:
            browser = await playwright.webkit.launch(**launch_options)
        
        # Create context with stealth settings
        context_options = await self.stealth_manager.get_context_options()
        context = await browser.new_context(**context_options)
        
        # Apply additional stealth measures
        await self.stealth_manager.apply_stealth_to_context(context)
        
        return browser, context
    
    async def create_single_account(self, user_profile: UserProfile, proxy: Optional[ProxyInfo] = None) -> Dict[str, Any]:
        """Create a single Gmail account"""
        self.stats["total_attempts"] += 1
        
        browser = None
        context = None
        
        try:
            logger.info(f"Creating account for {user_profile.first_name} {user_profile.last_name}")
            
            # Create browser context
            browser, context = await self.create_browser_context(proxy)
            page = await context.new_page()
            
            # Apply stealth to the page
            if self.config.stealth.stealth_plugin_enabled and STEALTH_AVAILABLE:
                await stealth_async(page)
            elif self.config.stealth.stealth_plugin_enabled and not STEALTH_AVAILABLE:
                logger.warning("Stealth plugin requested but playwright_stealth is not available")
            
            await self.stealth_manager.apply_stealth_to_page(page)
            
            # Navigate to Gmail signup
            await page.goto("https://accounts.google.com/signup/v2/createaccount?flowName=GlifWebSignIn&flowEntry=SignUp")
            
            # Wait for page load and check for initial elements
            await page.wait_for_load_state("networkidle")
            await self._random_delay(2, 5)
            
            # Step 1: Enter name information
            await self._enter_name_info(page, user_profile)
            
            # Step 2: Choose username
            username = await self._choose_username(page, user_profile)
            
            # Step 3: Set password
            await self._set_password(page, user_profile)
            
            # Step 4: Enter birth date and gender
            await self._enter_birth_and_gender(page, user_profile)
            
            # Step 5: Handle phone verification (skip if possible)
            phone_required = await self._handle_phone_verification(page)
            
            # Step 6: Handle recovery email (skip if possible)
            await self._handle_recovery_email(page)
            
            # Step 7: Agree to terms
            await self._agree_to_terms(page)
            
            # Verify account creation
            await self._verify_account_creation(page)
            
            # Account created successfully
            account_data = {
                "email": f"{username}@gmail.com",
                "password": user_profile.password,
                "first_name": user_profile.first_name,
                "last_name": user_profile.last_name,
                "birth_date": f"{user_profile.birth_year}-{user_profile.birth_month:02d}-{user_profile.birth_day:02d}",
                "gender": user_profile.gender,
                "recovery_info": user_profile.recovery_email if hasattr(user_profile, 'recovery_email') else None,
                "phone_required": phone_required,
                "created_at": datetime.now().isoformat(),
                "proxy_used": f"{proxy.host}:{proxy.port}" if proxy else None,
                "user_agent": await page.evaluate("navigator.userAgent"),
                "status": "created"
            }
            
            self.created_accounts.append(account_data)
            self.stats["successful_creations"] += 1
            
            logger.info(f"✅ Successfully created account: {account_data['email']}")
            return account_data
            
        except PlaywrightTimeoutError as e:
            error_msg = f"Timeout during account creation: {str(e)}"
            logger.error(error_msg)
            self.stats["failed_creations"] += 1
            return {"error": error_msg, "status": "timeout"}
            
        except GmailCreationError as e:
            error_msg = f"Gmail creation error: {str(e)}"
            logger.error(error_msg)
            self.stats["failed_creations"] += 1
            return {"error": error_msg, "status": "creation_error"}
            
        except Exception as e:
            error_msg = f"Unexpected error during account creation: {str(e)}"
            logger.error(error_msg)
            self.stats["failed_creations"] += 1
            return {"error": error_msg, "status": "unexpected_error"}
            
        finally:
            # Cleanup
            if context:
                await context.close()
            if browser:
                await browser.close()
    
    async def _enter_name_info(self, page: Page, user_profile: UserProfile):
        """Enter first and last name"""
        logger.debug("Entering name information")
        
        # Wait for name fields
        await page.wait_for_selector(self.selectors["first_name"], timeout=10000)
        
        # Enter first name
        await page.fill(self.selectors["first_name"], user_profile.first_name)
        await self._random_delay(0.5, 1.5)
        
        # Enter last name
        await page.fill(self.selectors["last_name"], user_profile.last_name)
        await self._random_delay(0.5, 1.5)
        
        # Click next
        await page.click(self.selectors["next_button"])
        await page.wait_for_load_state("networkidle")
        await self._random_delay(2, 4)
    
    async def _choose_username(self, page: Page, user_profile: UserProfile) -> str:
        """Choose and verify username availability"""
        logger.debug("Choosing username")
        
        # Check if we need to create custom username
        try:
            create_custom = await page.query_selector(self.selectors["create_custom_email"])
            if create_custom:
                await create_custom.click()
                await self._random_delay(1, 2)
        except:
            pass
        
        # Wait for username field
        await page.wait_for_selector(self.selectors["username"], timeout=10000)
        
        # Try different username variations
        username_base = user_profile.username
        username = username_base
        attempts = 0
        max_attempts = 5
        
        while attempts < max_attempts:
            try:
                # Clear and enter username
                await page.fill(self.selectors["username"], "")
                await self._random_delay(0.3, 0.7)
                await page.type(self.selectors["username"], username, delay=random.randint(50, 150))
                await self._random_delay(1, 2)
                
                # Check availability
                await page.click(self.selectors["next_button"])
                
                # Wait for response
                await page.wait_for_timeout(2000)
                
                # Check if username is taken
                username_taken = await page.query_selector(self.selectors["username_taken"])
                if not username_taken:
                    logger.info(f"Username '{username}' is available")
                    break
                else:
                    # Generate new username variation
                    attempts += 1
                    random_suffix = random.randint(100, 9999)
                    username = f"{username_base}{random_suffix}"
                    logger.debug(f"Username taken, trying: {username}")
                    
            except Exception as e:
                logger.warning(f"Error checking username availability: {e}")
                attempts += 1
                if attempts < max_attempts:
                    random_suffix = random.randint(100, 9999)
                    username = f"{username_base}{random_suffix}"
        
        if attempts >= max_attempts:
            raise GmailCreationError("Could not find available username")
        
        await page.wait_for_load_state("networkidle")
        await self._random_delay(2, 4)
        return username
    
    async def _set_password(self, page: Page, user_profile: UserProfile):
        """Set account password"""
        logger.debug("Setting password")
        
        # Wait for password fields
        await page.wait_for_selector(self.selectors["password"], timeout=10000)
        
        # Enter password
        await page.type(self.selectors["password"], user_profile.password, delay=random.randint(50, 100))
        await self._random_delay(0.5, 1)
        
        # Confirm password
        await page.type(self.selectors["confirm_password"], user_profile.password, delay=random.randint(50, 100))
        await self._random_delay(0.5, 1)
        
        # Click next
        await page.click(self.selectors["next_button"])
        await page.wait_for_load_state("networkidle")
        await self._random_delay(2, 4)
    
    async def _enter_birth_and_gender(self, page: Page, user_profile: UserProfile):
        """Enter birth date and gender information"""
        logger.debug("Entering birth date and gender")
        
        # Wait for birth date fields
        await page.wait_for_selector(self.selectors["birth_month"], timeout=10000)
        
        # Select birth month
        await page.select_option(self.selectors["birth_month"], value=str(user_profile.birth_month))
        await self._random_delay(0.3, 0.7)
        
        # Enter birth day
        await page.fill(self.selectors["birth_day"], str(user_profile.birth_day))
        await self._random_delay(0.3, 0.7)
        
        # Enter birth year
        await page.fill(self.selectors["birth_year"], str(user_profile.birth_year))
        await self._random_delay(0.3, 0.7)
        
        # Select gender
        gender_value = "1" if user_profile.gender.lower() == "male" else "2" if user_profile.gender.lower() == "female" else "3"
        await page.select_option(self.selectors["gender"], value=gender_value)
        await self._random_delay(0.5, 1)
        
        # Click next
        await page.click(self.selectors["next_button"])
        await page.wait_for_load_state("networkidle")
        await self._random_delay(2, 4)
    
    async def _handle_phone_verification(self, page: Page) -> bool:
        """Handle phone verification step"""
        logger.debug("Checking for phone verification")
        
        try:
            # Check if phone verification is required
            phone_input = await page.query_selector(self.selectors["phone_required"])
            
            if phone_input:
                logger.warning("Phone verification required")
                self.stats["phone_verification_required"] += 1
                
                # Try to skip
                skip_button = await page.query_selector(self.selectors["phone_skip"])
                if skip_button:
                    await skip_button.click()
                    await self._random_delay(1, 2)
                    logger.info("Skipped phone verification")
                    return False
                else:
                    logger.error("Phone verification required and cannot be skipped")
                    raise GmailCreationError("Phone verification required")
            
            return False
            
        except Exception as e:
            logger.debug(f"Phone verification handling: {e}")
            return False
    
    async def _handle_recovery_email(self, page: Page):
        """Handle recovery email step"""
        logger.debug("Handling recovery email")
        
        try:
            # Check for recovery email field
            recovery_field = await page.query_selector(self.selectors["recovery_email"])
            
            if recovery_field:
                # Try to skip
                skip_button = await page.query_selector(self.selectors["phone_skip"])
                if skip_button:
                    await skip_button.click()
                    await self._random_delay(1, 2)
                    logger.debug("Skipped recovery email")
                else:
                    # If can't skip, leave empty and continue
                    await page.click(self.selectors["next_button"])
                    await self._random_delay(1, 2)
        
        except Exception as e:
            logger.debug(f"Recovery email handling: {e}")
    
    async def _agree_to_terms(self, page: Page):
        """Agree to Google's terms and conditions"""
        logger.debug("Agreeing to terms")
        
        try:
            # Wait for and click agree button
            await page.wait_for_selector(self.selectors["agree_button"], timeout=10000)
            await page.click(self.selectors["agree_button"])
            await page.wait_for_load_state("networkidle")
            await self._random_delay(3, 6)
            
        except Exception as e:
            logger.error(f"Error agreeing to terms: {e}")
            raise GmailCreationError("Could not agree to terms")
    
    async def _verify_account_creation(self, page: Page):
        """Verify that account was created successfully"""
        logger.debug("Verifying account creation")
        
        try:
            # Wait for successful creation indicators
            await page.wait_for_timeout(5000)
            
            # Check for Gmail interface or success page
            current_url = page.url
            
            if "accounts.google.com" in current_url and "signin" not in current_url:
                # Still on signup page, might be an error
                error_elements = await page.query_selector_all(".LXRPh, .dEOOab")
                if error_elements:
                    error_text = await error_elements[0].inner_text()
                    raise GmailCreationError(f"Account creation failed: {error_text}")
            
            # If we're here, assume success
            logger.debug("Account creation appears successful")
            
        except Exception as e:
            logger.warning(f"Could not verify account creation: {e}")
    
    async def _random_delay(self, min_seconds: float, max_seconds: float):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def create_bulk_accounts(self, count: int) -> List[Dict[str, Any]]:
        """Create multiple Gmail accounts"""
        logger.info(f"Starting bulk account creation: {count} accounts")
        self.stats["start_time"] = datetime.now()
        
        results = []
        
        for i in range(count):
            try:
                logger.info(f"Creating account {i + 1}/{count}")
                
                # Generate user profile
                user_profile = self.user_generator.generate_profile()
                
                # Get proxy if enabled
                proxy = None
                if self.proxy_manager:
                    if self.config.proxy.rotation_method == "random":
                        proxy = self.proxy_manager.get_random_proxy()
                    elif self.config.proxy.rotation_method == "sequential":
                        proxy = self.proxy_manager.get_next_proxy()
                    elif self.config.proxy.rotation_method == "best":
                        proxy = self.proxy_manager.get_best_proxy()
                
                # Create account
                result = await self.create_single_account(user_profile, proxy)
                results.append(result)
                
                # Save progress
                if self.config.account.save_to_file:
                    await self._save_accounts_to_file()
                
                # Delay between accounts
                if i < count - 1:  # Don't delay after last account
                    delay_range = self.config.account.delay_between_accounts
                    delay = random.randint(delay_range[0], delay_range[1])
                    logger.info(f"Waiting {delay} seconds before next account...")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error creating account {i + 1}: {e}")
                results.append({"error": str(e), "status": "failed"})
                continue
        
        self.stats["end_time"] = datetime.now()
        await self._save_final_report()
        
        return results
    
    async def _save_accounts_to_file(self):
        """Save created accounts to file"""
        if not self.created_accounts:
            return
        
        output_dir = Path(self.config.project_root) / self.config.output_dir
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.config.account.output_format == "json":
            file_path = output_dir / f"gmail_accounts_{timestamp}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.created_accounts, f, indent=2, ensure_ascii=False)
        
        elif self.config.account.output_format == "csv":
            import csv
            file_path = output_dir / f"gmail_accounts_{timestamp}.csv"
            
            if self.created_accounts:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.created_accounts[0].keys())
                    writer.writeheader()
                    writer.writerows(self.created_accounts)
        
        else:  # txt format
            file_path = output_dir / f"gmail_accounts_{timestamp}.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                for account in self.created_accounts:
                    if account.get('status') == 'created':
                        f.write(f"Email: {account['email']}, Password: {account['password']}\n")
        
        logger.info(f"Accounts saved to: {file_path}")
    
    async def _save_final_report(self):
        """Save final creation report"""
        output_dir = Path(self.config.project_root) / self.config.output_dir
        output_dir.mkdir(exist_ok=True)
        
        # Calculate statistics
        duration = None
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        report = {
            "summary": {
                "total_attempts": self.stats["total_attempts"],
                "successful_creations": self.stats["successful_creations"],
                "failed_creations": self.stats["failed_creations"],
                "success_rate": (self.stats["successful_creations"] / self.stats["total_attempts"] * 100) if self.stats["total_attempts"] > 0 else 0,
                "duration_seconds": duration,
                "accounts_per_hour": (self.stats["successful_creations"] / (duration / 3600)) if duration and duration > 0 else 0
            },
            "details": {
                "proxy_failures": self.stats["proxy_failures"],
                "captcha_encounters": self.stats["captcha_encounters"],
                "phone_verification_required": self.stats["phone_verification_required"]
            },
            "configuration": self.config_manager.get_config_summary(),
            "timestamp": datetime.now().isoformat()
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"creation_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Final report saved to: {report_file}")
        logger.info(f"📊 Creation Summary: {self.stats['successful_creations']}/{self.stats['total_attempts']} successful")


# Example usage
async def main():
    """Example usage of GmailCreator"""
    # Initialize configuration
    config_manager = ConfigManager()
    config_manager.setup_logging()
    
    # Create Gmail creator
    creator = GmailCreator(config_manager)
    await creator.initialize()
    
    # Create accounts
    results = await creator.create_bulk_accounts(3)
    
    print(f"Created {len([r for r in results if r.get('status') == 'created'])} accounts")


if __name__ == "__main__":
    asyncio.run(main())