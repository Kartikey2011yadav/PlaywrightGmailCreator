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
            "birth_month": "select[id='month'], select[aria-label*='Month'], div[data-value] >> nth=0",
            "birth_day": "input[id='day'], input[aria-label*='Day'], input[placeholder*='Day']",
            "birth_year": "input[id='year'], input[aria-label*='Year'], input[placeholder*='Year']",
            "gender": "select[id='gender'], select[aria-label*='Gender'], div[data-value] >> nth=1",
            "phone_skip": "span:has-text('Skip'), button:has-text('Skip')",
            "agree_button": "button:has-text('I agree'), button:has-text('Accept')",
            "recovery_email": "input[name='recovery'], input[type='email']:not([name='Username'])",
            "create_custom_email": "span:has-text('Create your own Gmail address'), button:has-text('Create your own Gmail address')",
            "username_available": ".o6cuMc",
            "username_taken": ".LXRPh, .dEOOab",
            "captcha_frame": "iframe[title*='recaptcha']",
            "phone_required": "input[type='tel'], input[placeholder*='phone']",
            "language_dropdown": "select[aria-label*='Language'], button[aria-label*='Language'], div[role='combobox'], ul[aria-label='Change language']",
            "language_english": "li[data-value='en-US'], option[value='en-US'], span:has-text('English (United States)')"
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
            
            # Step 0: Set language to English (United States)
            await self._set_language_to_english(page)
            
            # Step 1: Enter name information
            await self._enter_name_info(page, user_profile)
            
            # Step 2: Enter birth date and gender
            await self._enter_birth_and_gender(page, user_profile)

            # Step 3: Choose username
            username = await self._choose_username(page, user_profile)

            # Step 4: Set password
            await self._set_password(page, user_profile)
        
            
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
        
        # Generate Gmail-compliant username variations
        username_base = self._ensure_gmail_compliant_username(user_profile.username)
        username = username_base
        attempts = 0
        max_attempts = 8
        
        while attempts < max_attempts:
            try:
                logger.debug(f"Trying username: {username} (attempt {attempts + 1})")
                
                # Clear and enter username
                await page.fill(self.selectors["username"], "")
                await self._random_delay(0.3, 0.7)
                await page.type(self.selectors["username"], username, delay=random.randint(50, 150))
                await self._random_delay(1, 2)
                
                # Check availability
                await page.click(self.selectors["next_button"])
                
                # Wait for response
                await page.wait_for_timeout(3000)
                
                # Check if username is taken
                username_taken = await page.query_selector(self.selectors["username_taken"])
                if not username_taken:
                    logger.info(f"✅ Username '{username}' is available")
                    break
                else:
                    # Generate new Gmail-compliant username variation
                    attempts += 1
                    username = self._generate_username_variation(username_base, attempts)
                    logger.debug(f"Username taken, trying: {username}")
                    
            except Exception as e:
                logger.warning(f"Error checking username availability: {e}")
                attempts += 1
                if attempts < max_attempts:
                    username = self._generate_username_variation(username_base, attempts)
        
        if attempts >= max_attempts:
            raise GmailCreationError("Could not find available username")
        
        await page.wait_for_load_state("networkidle")
        await self._random_delay(2, 4)
        return username
    
    def _ensure_gmail_compliant_username(self, username: str) -> str:
        """Ensure username meets Gmail requirements"""
        import re
        
        # Convert to lowercase and remove invalid characters
        username = re.sub(r'[^a-z0-9.]', '', username.lower())
        
        # Remove consecutive periods
        while '..' in username:
            username = username.replace('..', '.')
            
        # Remove leading/trailing periods
        username = username.strip('.')
        
        # Ensure minimum length
        if len(username) < 6:
            username += str(random.randint(1000, 9999))
            
        # Ensure maximum length  
        if len(username) > 30:
            username = username[:25] + str(random.randint(10, 99))
            
        # Check for reserved terms
        reserved_terms = ['abuse', 'postmaster', 'admin', 'administrator', 'hostmaster']
        if username.lower() in reserved_terms:
            username = f"user{username}{random.randint(10, 99)}"
            
        return username
    
    def _generate_username_variation(self, base_username: str, attempt: int) -> str:
        """Generate Gmail-compliant username variations"""
        import re
        
        # Clean base username
        base = re.sub(r'[^a-z0-9.]', '', base_username.lower()).strip('.')
        
        variations = [
            f"{base}{random.randint(10, 99)}",
            f"{base}{random.randint(100, 999)}",
            f"{base}.{random.randint(10, 99)}",
            f"{base}{random.randint(1990, 2025)}",
            f"{base}.{random.randint(1, 999)}",
            f"{base[:8]}{random.randint(1000, 9999)}",
            f"{base}.user{random.randint(1, 99)}",
            f"user.{base}{random.randint(1, 99)}"
        ]
        
        # Select variation based on attempt number
        variation = variations[attempt % len(variations)]
        
        # Ensure it meets Gmail requirements
        return self._ensure_gmail_compliant_username(variation)
    
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
        """Enter birth date and gender information based on actual Gmail HTML structure"""
        logger.debug("Entering birth date and gender")
        
        try:
            # Wait for the birth date section to be visible
            await page.wait_for_selector('.HnFhQ', timeout=10000)
            await self._random_delay(1, 2)
            
            # === MONTH SELECTION ===
            logger.debug(f"Selecting month: {user_profile.birth_month}")
            
            # Find month dropdown using the exact HTML structure
            month_button_selectors = [
                '#month div[jsname="oYxtQd"][role="combobox"]',
                'div[id="month"] .VfPpkd-TkwUic[role="combobox"]',
                'div[jsname="byRamd"] div[role="combobox"]'
            ]
            
            month_button = None
            for selector in month_button_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        month_button = button
                        logger.debug(f"Found month button with selector: {selector}")
                        break
                except:
                    continue
            
            if not month_button:
                raise GmailCreationError("Could not find month dropdown button")
            
            # Click to open month dropdown
            await month_button.scroll_into_view_if_needed()
            await month_button.click()
            await self._random_delay(1, 2)
            
            # Wait for month dropdown to open and select the month (target specific month dropdown)
            month_name = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][user_profile.birth_month]
            month_option_selectors = [
                f'div[data-menu-uid="ucc-0"] li[data-value="{user_profile.birth_month}"][role="option"]',
                f'div[data-menu-uid="ucc-0"] li[role="option"] span[jsname="K4r5Ff"]:has-text("{month_name}")',
                f'#month ~ div ul[role="listbox"] li[data-value="{user_profile.birth_month}"]'
            ]
            
            month_selected = False
            for selector in month_option_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    option = await page.query_selector(selector)
                    if option and await option.is_visible():
                        await option.click()
                        logger.debug(f"Selected month with selector: {selector}")
                        month_selected = True
                        break
                except:
                    continue
            
            if not month_selected:
                logger.warning("Could not select month from dropdown")
            
            await self._random_delay(0.5, 1)
            
            # === DAY SELECTION ===
            logger.debug(f"Entering day: {user_profile.birth_day}")
            
            day_selectors = [
                'input[id="day"]',
                'input[name="day"]', 
                'input[aria-label="Day"]',
                'input[type="tel"][maxlength="2"]'
            ]
            
            day_filled = False
            for selector in day_selectors:
                try:
                    day_input = await page.query_selector(selector)
                    if day_input and await day_input.is_visible():
                        await day_input.scroll_into_view_if_needed()
                        await day_input.click()
                        await day_input.fill("")  # Clear any existing value
                        await day_input.type(str(user_profile.birth_day))
                        logger.debug(f"Filled day with selector: {selector}")
                        day_filled = True
                        break
                except Exception as e:
                    logger.debug(f"Error with day selector {selector}: {e}")
                    continue
            
            if not day_filled:
                logger.warning("Could not fill birth day field")
            
            await self._random_delay(0.5, 1)
            
            # === YEAR SELECTION ===
            logger.debug(f"Entering year: {user_profile.birth_year}")
            
            year_selectors = [
                'input[id="year"]',
                'input[name="year"]',
                'input[aria-label="Year"]', 
                'input[type="tel"][maxlength="4"]'
            ]
            
            year_filled = False
            for selector in year_selectors:
                try:
                    year_input = await page.query_selector(selector)
                    if year_input and await year_input.is_visible():
                        await year_input.scroll_into_view_if_needed()
                        await year_input.click()
                        await year_input.fill("")  # Clear any existing value
                        await year_input.type(str(user_profile.birth_year))
                        logger.debug(f"Filled year with selector: {selector}")
                        year_filled = True
                        break
                except Exception as e:
                    logger.debug(f"Error with year selector {selector}: {e}")
                    continue
            
            if not year_filled:
                logger.warning("Could not fill birth year field")
            
            await self._random_delay(0.5, 1)
            
            # === GENDER SELECTION ===
            logger.debug(f"Selecting gender: {user_profile.gender}")
            
            # Find gender dropdown using the exact HTML structure  
            gender_button_selectors = [
                '#gender div[jsname="oYxtQd"][role="combobox"]',
                'div[id="gender"] .VfPpkd-TkwUic[role="combobox"]',
                'div[jsname="ZU2VHd"] div[role="combobox"]'
            ]
            
            gender_button = None
            for selector in gender_button_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        gender_button = button
                        logger.debug(f"Found gender button with selector: {selector}")
                        break
                except:
                    continue
            
            if not gender_button:
                logger.warning("Could not find gender dropdown button")
                return
            
            # Click to open gender dropdown
            await gender_button.scroll_into_view_if_needed()
            await gender_button.click()
            await self._random_delay(1, 2)
            
            # Wait for the specific gender dropdown menu to be visible using unique identifier
            # Give some time for the dropdown to appear after clicking
            await page.wait_for_timeout(1000)
            
            # Try to find the gender dropdown menu by multiple approaches
            gender_dropdown_found = False
            for attempt in range(3):
                try:
                    # Look for the gender dropdown specifically
                    gender_dropdown = await page.query_selector('div[data-menu-uid="ucc-1"][jsname="xl07Ob"]')
                    if gender_dropdown and await gender_dropdown.is_visible():
                        gender_dropdown_found = True
                        logger.debug("Gender dropdown found and visible")
                        break
                    else:
                        # Alternative: check if any dropdown with gender options is visible
                        gender_list = await page.query_selector('ul[aria-label="Gender"][role="listbox"]')
                        if gender_list and await gender_list.is_visible():
                            gender_dropdown_found = True  
                            logger.debug("Gender listbox found and visible")
                            break
                except Exception as e:
                    logger.debug(f"Attempt {attempt + 1} to find gender dropdown failed: {e}")
                
                if attempt < 2:  # Don't wait after the last attempt
                    await page.wait_for_timeout(1000)
            
            if not gender_dropdown_found:
                logger.warning("Gender dropdown not found after clicking button")
                await page.keyboard.press('Escape')  # Close any open dropdown
                return
            
            # Map gender values based on the actual HTML structure
            gender_mapping = {
                "female": ("2", "Female"),
                "male": ("1", "Male"), 
                "other": ("3", "Rather not say"),
                "prefer not to say": ("3", "Rather not say"),
                "rather not say": ("3", "Rather not say"),
                "custom": ("4", "Custom")
            }
            
            # Get the gender value and display text
            gender_key = user_profile.gender.lower()
            gender_value, gender_text = gender_mapping.get(gender_key, ("3", "Rather not say"))  # Default to "Rather not say"
            
            logger.debug(f"Looking for gender option: {gender_text} (value={gender_value})")
            
            # Try multiple selector strategies for finding the gender option, targeting the specific gender dropdown
            gender_option_selectors = [
                # Most precise: target the specific gender dropdown by menu-uid
                f'div[data-menu-uid="ucc-1"] ul[role="listbox"][aria-label="Gender"] li[data-value="{gender_value}"]',
                # Backup: within the gender dropdown container
                f'div[data-menu-uid="ucc-1"] li[data-value="{gender_value}"][role="option"]',
                # Text-based match within the gender dropdown
                f'div[data-menu-uid="ucc-1"] li[role="option"] span[jsname="K4r5Ff"]:has-text("{gender_text}")',
                # More general approach within gender dropdown
                f'div[data-menu-uid="ucc-1"] li[role="option"]:has-text("{gender_text}")',
                # Fallback: use the gender container context
                f'#gender ~ div ul[role="listbox"] li[data-value="{gender_value}"]'
            ]
            
            gender_selected = False
            selected_option = None
            
            for i, selector in enumerate(gender_option_selectors):
                try:
                    logger.debug(f"Trying gender selector {i+1}/{len(gender_option_selectors)}: {selector}")
                    options = await page.query_selector_all(selector)
                    logger.debug(f"Found {len(options)} options with this selector")
                    
                    for j, option in enumerate(options):
                        try:
                            is_visible = await option.is_visible()
                            logger.debug(f"Option {j+1} visible: {is_visible}")
                            
                            if is_visible:
                                await option.scroll_into_view_if_needed()
                                await page.wait_for_timeout(500)
                                await option.click()
                                logger.info(f"✅ Successfully clicked gender option with selector: {selector}")
                                selected_option = option
                                gender_selected = True
                                break
                        except Exception as opt_e:
                            logger.debug(f"Failed to click option {j+1}: {opt_e}")
                            continue
                    
                    if gender_selected:
                        break
                        
                except Exception as e:
                    logger.debug(f"Gender selector failed {selector}: {e}")
                    continue
            
            if not gender_selected:
                logger.warning("Could not select gender from dropdown, trying fallback")
                # Fallback: try clicking "Rather not say" from the gender dropdown specifically
                try:
                    fallback_option = await page.query_selector('div[data-menu-uid="ucc-1"] li[role="option"][data-value="3"]')
                    if fallback_option and await fallback_option.is_visible():
                        await fallback_option.click()
                        logger.debug("Selected fallback gender option: Rather not say")
                        gender_selected = True
                except:
                    pass
            
            if not gender_selected:
                logger.warning("Could not select any gender option - closing dropdown")
                await page.keyboard.press('Escape')
            else:
                # Wait for dropdown to close after selection
                await page.wait_for_timeout(1000)
                
                # Handle custom gender if selected
                if gender_value == "4":  # Custom gender selected
                    try:
                        logger.debug("Custom gender selected, looking for additional fields")
                        
                        # Wait for custom gender input field to appear
                        custom_input = await page.wait_for_selector('#customGender input[type="text"]', timeout=3000)
                        if custom_input:
                            await custom_input.fill(user_profile.gender)
                            logger.debug(f"Filled custom gender: {user_profile.gender}")
                        
                        # Handle pronoun selection if it appears
                        pronoun_dropdown = await page.query_selector('#genderpronoun div[role="combobox"]')
                        if pronoun_dropdown and await pronoun_dropdown.is_visible():
                            await pronoun_dropdown.click()
                            await page.wait_for_timeout(1000)
                            
                            # Select appropriate pronoun (default to "Other" for custom)
                            pronoun_option = await page.query_selector('li[data-value="3"][role="option"]')  # Other
                            if pronoun_option and await pronoun_option.is_visible():
                                await pronoun_option.click()
                                logger.debug("Selected pronoun: Other")
                                
                    except Exception as e:
                        logger.debug(f"Error handling custom gender fields: {e}")
                
                logger.info(f"✅ Gender selected: {gender_text}")
            
            await self._random_delay(1, 2)
            logger.info("✅ Birth date and gender information entered")
            
        except Exception as e:
            logger.error(f"Error entering birth date and gender: {str(e)}")
            # Try to close any open dropdowns
            try:
                await page.keyboard.press('Escape')
            except:
                pass
            raise GmailCreationError(f"Failed to enter birth date and gender: {str(e)}")
        
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
    
    async def _set_language_to_english(self, page: Page):
        """Set the language to English (United States) based on actual Gmail HTML structure"""
        logger.debug("Setting language to English (United States)")
        
        try:
            # Wait for page to fully load
            await self._random_delay(2, 3)
            
            # First, check if page is already in English by looking for English text
            english_indicators = [
                "text=First name",
                "text=Last name", 
                "text=Next",
                "text=Create account",
                "text=Choose your username"
            ]
            
            for indicator in english_indicators:
                try:
                    element = await page.query_selector(indicator)
                    if element:
                        logger.debug("Page appears to be in English already")
                        return
                except:
                    continue
            
            logger.debug("Looking for language dropdown...")
            
            # Wait for footer to be present first
            try:
                await page.wait_for_selector('footer.FZfKCe', timeout=5000)
            except:
                logger.debug("Footer not found, continuing without language change")
                return
            
            # Look for language dropdown combobox using the exact HTML structure
            language_button_selectors = [
                # Most specific selector based on actual HTML structure
                'div[jsname="oYxtQd"][role="combobox"][aria-haspopup="listbox"]',
                # Fallback selectors
                'div[role="combobox"][aria-haspopup="listbox"]',
                '.VfPpkd-TkwUic[role="combobox"]',
                'div[jscontroller="yRXbo"] div[role="combobox"]'
            ]
            
            language_button = None
            successful_selector = None
            
            for selector in language_button_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        language_button = element
                        successful_selector = selector
                        logger.debug(f"Found language button with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            if not language_button:
                logger.debug("No language dropdown button found")
                return
            
            # Check if already showing English (United States) by looking at the display span
            try:
                display_span = await page.query_selector('#i3.VfPpkd-uusGie-fmcmS[jsname="Fb0Bif"]')
                if display_span:
                    current_text = await display_span.text_content()
                    if current_text and "English (United States)" in current_text:
                        logger.debug("Language already set to English (United States)")
                        return
            except:
                pass
            
            try:
                logger.debug(f"Attempting to click language button found with: {successful_selector}")
                
                # Scroll element into view if needed
                await language_button.scroll_into_view_if_needed()
                await self._random_delay(0.5, 1)
                
                # Click the language button
                await language_button.click(timeout=5000)
                await self._random_delay(1, 2)
                
                logger.debug("Language button clicked, waiting for dropdown...")
                
                # Wait for dropdown menu to appear using the specific class structure
                try:
                    await page.wait_for_selector('.VfPpkd-xl07Ob[jsname="xl07Ob"]', timeout=5000)
                    await self._random_delay(1, 2)  # Give time for all options to load
                except:
                    logger.debug("Dropdown menu did not appear")
                    await page.keyboard.press('Escape')
                    return
                
                # Look for English (United States) option using the exact HTML structure
                english_option_selectors = [
                    # Most specific - exact data-value match from the HTML
                    'li[data-value="en-US"][role="option"]',
                    # Backup using text content in the span
                    'li[role="option"] span[jsname="K4r5Ff"]:has-text("English (United States)")',
                    # More general text-based approach
                    'li[role="option"]:has-text("English (United States)")',
                    # Class-based selector
                    '.VfPpkd-rymPhb-ibnC6b[data-value="en-US"]'
                ]
                
                english_option = None
                for selector in english_option_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        option = await page.query_selector(selector)
                        if option and await option.is_visible():
                            english_option = option
                            logger.debug(f"Found English option with selector: {selector}")
                            break
                    except:
                        continue
                
                if english_option:
                    # Ensure the option is visible and clickable
                    await english_option.scroll_into_view_if_needed()
                    await self._random_delay(0.5, 1)
                    
                    await english_option.click(timeout=3000)
                    await self._random_delay(1, 2)
                    
                    # Verify the selection worked by checking the display text
                    try:
                        display_span = await page.query_selector('#i3.VfPpkd-uusGie-fmcmS[jsname="Fb0Bif"]')
                        if display_span:
                            updated_text = await display_span.text_content()
                            if updated_text and "English (United States)" in updated_text:
                                logger.info("✅ Language successfully set to English (United States)")
                                return
                    except:
                        pass
                    
                    logger.info("✅ Language set to English (United States)")
                else:
                    logger.debug("Could not find English (United States) option in dropdown")
                    # Try to close dropdown
                    await page.keyboard.press('Escape')
                    
            except Exception as click_error:
                logger.debug(f"Error interacting with language dropdown: {click_error}")
                # Try to close any open dropdown
                try:
                    await page.keyboard.press('Escape')
                except:
                    pass
                
        except Exception as e:
            logger.debug(f"Language setting failed (non-critical): {e}")
            # Continue anyway as this is not critical for account creation
    
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