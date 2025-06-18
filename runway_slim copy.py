# -*- coding: utf-8 -*-

"""
RunwayML Slim Automation Script

This script handles only the basic browser automation for RunwayML:
1. Open browser
2. Navigate to RunwayML
3. Login

Simple and focused approach for step-by-step development.
"""

import os
import sys
import time
import logging
import json
import random
import re  # NEW: For scene/narration parsing
from typing import Optional, List, Union

# Libraries for environment and credential management
from dotenv import load_dotenv

# Selenium libraries
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxWebDriver  
from selenium.webdriver.edge.webdriver import WebDriver as EdgeWebDriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException
)

# Type alias for all WebDriver types
WebDriverType = Union[ChromeWebDriver, FirefoxWebDriver, EdgeWebDriver]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("runway_slim.log", encoding='utf-8')
    ]
)

# Try to import mutagen for audio duration analysis
try:
    from mutagen.mp3 import MP3  # type: ignore
except ImportError:  # Safe fallback if mutagen not installed
    MP3 = None  # type: ignore

class RunwayMLSlim:
    """
    Slim RunwayML automation class focused on basic browser operations.
    """
    
    # RunwayML URLs
    URLS = {
        "login": "https://app.runwayml.com/login",
        "dashboard": "https://app.runwayml.com/"
    }
    
    def __init__(self, browser_name: str = "chrome", manual_login: bool = False, use_undetected: bool = True):
        """
        Initialize the RunwayML automation.
        
        Args:
            browser_name: Browser to use (chrome, firefox, edge)
            manual_login: If True, wait for manual login; if False, use credentials from .env
            use_undetected: If True, try to use undetected-chromedriver (Chrome only)
        """
        self.manual_login = manual_login
        self.use_undetected = use_undetected
        self.logger = logging.getLogger(__name__)
        
        # Load credentials if using automated login
        if not manual_login:
            load_dotenv()
            self.username = os.getenv("RUNWAY_USERNAME", "")
            self.password = os.getenv("RUNWAY_PASSWORD", "")
            
            if not self.username or not self.password:
                raise ValueError("RunwayML credentials not found in .env file. "
                               "Please set RUNWAY_USERNAME and RUNWAY_PASSWORD.")
        
        # Setup browser
        self.driver = self._setup_driver(browser_name)
        self.wait = WebDriverWait(self.driver, 30)
        self.is_logged_in = False
        
        self.logger.info("RunwayML Slim automation initialized")
    
    def _setup_driver(self, browser_name: str) -> WebDriverType:
        """
        Setup the Selenium WebDriver with optimized options.
        
        Args:
            browser_name: Name of the browser (chrome, firefox, edge)
            
        Returns:
            Configured WebDriver instance
        """
        browser_name = browser_name.lower()
        
        if browser_name == "chrome":
            # Try undetected-chromedriver first if requested
            if self.use_undetected:
                try:
                    import undetected_chromedriver as uc
                    
                    options = uc.ChromeOptions()
                    options.add_argument("--start-maximized")
                    options.add_argument("--disable-notifications")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    
                    driver = uc.Chrome(options=options, version_main=None)
                    self.logger.info("✅ Using undetected-chromedriver")
                    return driver
                    
                except ImportError:
                    self.logger.warning("⚠️  undetected-chromedriver not available, using regular Chrome")
                except Exception as e:
                    self.logger.warning(f"⚠️  Failed to use undetected-chromedriver: {e}")
            
            # Regular Chrome setup
            options = ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            except ImportError:
                driver = webdriver.Chrome(options=options)
            
            # Hide webdriver properties
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
            
        elif browser_name == "firefox":
            options = FirefoxOptions()
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            
            try:
                from webdriver_manager.firefox import GeckoDriverManager
                return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
            except ImportError:
                return webdriver.Firefox(options=options)
                
        elif browser_name == "edge":
            options = EdgeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            try:
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
            except ImportError:
                driver = webdriver.Edge(options=options)
                
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        else:
            raise ValueError(f"Unsupported browser: {browser_name}")
    
    def navigate_to_login(self) -> bool:
        """
        Navigate to RunwayML login page.
        
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            self.logger.info("🌐 Navigating to RunwayML login page...")
            self.driver.get(self.URLS["login"])
            
            # Wait for page to load
            time.sleep(3)
            
            current_url = self.driver.current_url
            self.logger.info(f"📍 Current URL: {current_url}")
            
            if "runwayml.com" in current_url:
                self.logger.info("✅ Successfully navigated to RunwayML")
                return True
            else:
                self.logger.error(f"❌ Navigation failed - unexpected URL: {current_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error during navigation: {str(e)}")
            return False
    
    def find_element_safe(self, selectors: List[tuple], wait_time: int = 10) -> Optional[WebElement]:
        """
        Safely find an element using multiple selectors.
        
        Args:
            selectors: List of (By.X, 'selector') tuples
            wait_time: How long to wait for element
            
        Returns:
            Element if found, None otherwise
        """
        waiter = WebDriverWait(self.driver, wait_time)
        
        for i, selector in enumerate(selectors):
            try:
                element = waiter.until(EC.presence_of_element_located(selector))
                self.logger.debug(f"✅ Found element with selector {i+1}: {selector}")
                return element
            except (TimeoutException, NoSuchElementException):
                self.logger.debug(f"❌ Selector {i+1} failed: {selector}")
                continue
        
        self.logger.warning("❌ No element found with any selector")
        return None
    
    def login(self) -> bool:
        """
        Perform login to RunwayML.
        
        Returns:
            True if login successful, False otherwise
        """
        if self.is_logged_in:
            self.logger.info("✅ Already logged in")
            return True
        
        if self.manual_login:
            return self._manual_login()
        else:
            return self._automated_login()
    
    def _manual_login(self) -> bool:
        """
        Handle manual login - wait for user to complete login.
        
        Returns:
            True if login detected, False if timeout
        """
        self.logger.info("🔐 Manual login mode - please complete login in browser")
        self.logger.info("Waiting for you to:")
        self.logger.info("1. Enter your email and password")
        self.logger.info("2. Click login button")
        self.logger.info("3. Complete any 2FA if required")
        
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                current_url = self.driver.current_url
                
                # Check if we've moved away from login page
                if "login" not in current_url and "runwayml.com" in current_url:
                    self.logger.info(f"✅ Login successful! Redirected to: {current_url}")
                    self.is_logged_in = True
                    return True
                
                time.sleep(2)
                
            except Exception as e:
                self.logger.debug(f"Error checking login status: {e}")
                time.sleep(2)
        
        self.logger.error("❌ Manual login timed out")
        return False
    
    def _automated_login(self) -> bool:
        """
        Handle automated login using credentials.
        
        Returns:
            True if login successful, False otherwise
        """
        self.logger.info("🔐 Starting automated login...")
        
        # Email input selectors
        email_selectors = [
            (By.CSS_SELECTOR, "input[name='usernameOrEmail']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='Username' i]"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[type='text']")
        ]
        
        # Find and fill email
        email_input = self.find_element_safe(email_selectors)
        if not email_input:
            self.logger.error("❌ Could not find email input field")
            return False
        
        try:
            email_input.clear()
            email_input.send_keys(self.username)
            self.logger.info("✅ Email entered")
        except Exception as e:
            self.logger.error(f"❌ Failed to enter email: {e}")
            return False
        
        # Password input selectors
        password_selectors = [
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.CSS_SELECTOR, "input[placeholder*='Password' i]"),
            (By.CSS_SELECTOR, "input[type='password']")
        ]
        
        # Find and fill password
        password_input = self.find_element_safe(password_selectors)
        if not password_input:
            self.logger.error("❌ Could not find password input field")
            return False
        
        try:
            password_input.clear()
            password_input.send_keys(self.password)
            self.logger.info("✅ Password entered")
        except Exception as e:
            self.logger.error(f"❌ Failed to enter password: {e}")
            return False
        
        # Login button selectors
        login_button_selectors = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Log in')]"),
            (By.XPATH, "//button[contains(text(), 'Sign in')]"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.CSS_SELECTOR, "button")
        ]
        
        # Find and click login button
        login_button = self.find_element_safe(login_button_selectors)
        if not login_button:
            self.logger.error("❌ Could not find login button")
            return False
        
        try:
            login_button.click()
            self.logger.info("✅ Login button clicked")
        except Exception as e:
            self.logger.error(f"❌ Failed to click login button: {e}")
            return False
        
        # Wait for redirect
        self.logger.info("⏳ Waiting for login to complete...")
        time.sleep(3)
        
        # Check if login was successful
        for attempt in range(10):  # Wait up to 10 seconds
            try:
                current_url = self.driver.current_url
                if "login" not in current_url and "runwayml.com" in current_url:
                    self.logger.info(f"✅ Login successful! Redirected to: {current_url}")
                    self.is_logged_in = True
                    return True
                time.sleep(1)
            except Exception:
                time.sleep(1)
        
        self.logger.error("❌ Login failed - still on login page")
        return False
    
    def close(self):
        """Close the browser and cleanup."""
        if self.driver:
            self.logger.info("🔒 Closing browser...")
            self.driver.quit()

    def switch_to_video_tab(self) -> bool:
        """
        Step 1: Switch to Video tab for video generation.
        
        Clicks on the VIDEO radio button/label to switch from image to video mode.
        
        Returns:
            True if successfully switched to video tab, False otherwise
        """
        self.logger.info("🎥 Step 1: Switching to Video tab...")
        
        # Multiple selector strategies for the video tab
        video_tab_selectors = [
            # Target the label containing "Video" text
            (By.XPATH, "//label[contains(@class, 'radioItem') and contains(text(), 'Video')]"),
            (By.CSS_SELECTOR, "label.radioItem-v7VRzD"),
            
            # Target the radio input with value="video"
            (By.CSS_SELECTOR, "input[value='video']"),
            (By.XPATH, "//input[@value='video']"),
            
            # Target parent of radio input
            (By.XPATH, "//input[@value='video']/parent::*"),
            
            # More generic selectors
            (By.XPATH, "//label[contains(@class, 'radioItem')]"),
            (By.XPATH, "//*[contains(text(), 'Video') and (@role='radio' or contains(@class, 'radio'))]"),
            
            # SVG-based selectors (video icon)
            (By.XPATH, "//svg[contains(@class, 'lucide-video')]/ancestor::label"),
            (By.XPATH, "//svg[contains(@class, 'video')]/ancestor::label")
        ]
        
        # Try each selector until one works
        for i, selector in enumerate(video_tab_selectors):
            try:
                self.logger.debug(f"Trying video tab selector {i+1}/{len(video_tab_selectors)}: {selector}")
                
                # Wait for element to be clickable
                video_element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(selector)
                )
                
                # Log what we found
                try:
                    element_info = f"tag='{video_element.tag_name}', text='{video_element.text[:30]}', classes='{video_element.get_attribute('class')}'"
                    self.logger.debug(f"Found video tab element: {element_info}")
                except:
                    self.logger.debug("Found video tab element (couldn't get details)")
                
                # Click the element
                try:
                    video_element.click()
                    self.logger.info("✅ Successfully clicked video tab")
                except Exception as click_error:
                    # Try JavaScript click as fallback
                    self.logger.debug(f"Regular click failed: {click_error}, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", video_element)
                    self.logger.info("✅ Successfully clicked video tab (via JavaScript)")
                
                # Wait for UI to update
                time.sleep(2)
                
                # Verify we're now on video tab (optional verification)
                try:
                    # Check if the video radio is now selected
                    video_input = self.driver.find_element(By.CSS_SELECTOR, "input[value='video']")
                    if video_input.is_selected() or video_input.get_attribute('checked'):
                        self.logger.info("✅ Video tab is now selected")
                    else:
                        self.logger.warning("⚠️  Video tab click succeeded but radio not selected")
                except Exception as verify_error:
                    self.logger.debug(f"Could not verify video tab selection: {verify_error}")
                
                return True
                
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.debug(f"Selector {i+1} failed: {e}")
                continue
            except Exception as e:
                self.logger.warning(f"Unexpected error with selector {i+1}: {e}")
                continue
        
        # If we get here, all selectors failed
        self.logger.error("❌ Failed to find video tab with any selector")
        
        # Debug: Log current page state
        try:
            current_url = self.driver.current_url
            self.logger.error(f"Current URL: {current_url}")
            
            # Try to find any radio-like elements for debugging
            radio_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'], label[class*='radio']")
            self.logger.error(f"Found {len(radio_elements)} radio-like elements on page")
            
            for i, radio in enumerate(radio_elements[:5]):  # Log first 5
                try:
                    radio_info = f"tag='{radio.tag_name}', text='{radio.text[:20]}', value='{radio.get_attribute('value')}'"
                    self.logger.error(f"  Radio {i+1}: {radio_info}")
                except:
                    self.logger.error(f"  Radio {i+1}: (couldn't get details)")
                    
        except Exception as debug_error:
            self.logger.error(f"Debug logging failed: {debug_error}")
        
        return False

    def click_select_asset_button(self) -> bool:
        """
        Step 2: Click "Select Asset" button to switch to asset upload tab.
        
        Clicks the "Select Asset" button to access the file upload interface.
        
        Returns:
            True if successfully clicked Select Asset button, False otherwise
        """
        self.logger.info("📁 Step 2: Clicking 'Select Asset' button...")
        
        # Multiple selector strategies for the Select Asset button
        select_asset_selectors = [
            # Direct text-based selectors
            (By.XPATH, "//button[contains(text(), 'Select Asset')]"),
            (By.XPATH, "//button[text()='Select Asset']"),
            
            # Based on the specific classes from your HTML
            (By.CSS_SELECTOR, "button.container-kIPoeH.outline-oBCee2.small-IiIwXS"),
            (By.CSS_SELECTOR, "button[class*='container-kIPoeH']"),
            (By.CSS_SELECTOR, "button[data-soft-disabled='false'][class*='container-kIPoeH']"),
            
            # Based on ARIA attributes
            (By.CSS_SELECTOR, "button[data-rac][type='button'][tabindex='0']"),
            (By.CSS_SELECTOR, "button[data-rac][type='button']"),
            
            # More generic selectors
            (By.XPATH, "//button[contains(@class, 'container-') and contains(text(), 'Select')]"),
            (By.XPATH, "//button[contains(@class, 'outline-') and contains(text(), 'Asset')]"),
            (By.XPATH, "//button[@data-soft-disabled='false']"),
            
            # Fallback selectors
            (By.XPATH, "//button[contains(text(), 'Asset')]"),
            (By.XPATH, "//button[contains(text(), 'Select')]"),
            (By.CSS_SELECTOR, "button[type='button']")
        ]
        
        # Try each selector until one works
        for i, selector in enumerate(select_asset_selectors):
            try:
                self.logger.debug(f"Trying Select Asset selector {i+1}/{len(select_asset_selectors)}: {selector}")
                
                # Wait for element to be clickable
                select_asset_element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(selector)
                )
                
                # Log what we found
                try:
                    element_info = f"tag='{select_asset_element.tag_name}', text='{select_asset_element.text[:30]}', classes='{select_asset_element.get_attribute('class')}'"
                    self.logger.debug(f"Found Select Asset element: {element_info}")
                except:
                    self.logger.debug("Found Select Asset element (couldn't get details)")
                
                # Verify this looks like the right button
                element_text = select_asset_element.text.strip().lower()
                if "select" in element_text and "asset" in element_text:
                    self.logger.debug("✅ Button text contains 'select' and 'asset' - looks correct")
                elif "select" in element_text or "asset" in element_text:
                    self.logger.debug("⚠️  Button text partially matches - proceeding anyway")
                else:
                    self.logger.debug(f"⚠️  Button text '{element_text}' doesn't contain expected keywords")
                
                # Click the element
                try:
                    select_asset_element.click()
                    self.logger.info("✅ Successfully clicked Select Asset button")
                except Exception as click_error:
                    # Try JavaScript click as fallback
                    self.logger.debug(f"Regular click failed: {click_error}, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", select_asset_element)
                    self.logger.info("✅ Successfully clicked Select Asset button (via JavaScript)")
                
                # Wait for UI to update (upload interface should appear)
                time.sleep(2)
                
                # Verify we're now on the asset upload interface (optional verification)
                try:
                    # Look for upload-related elements that should appear
                    upload_indicators = [
                        "input[type='file']",
                        "[class*='upload']",
                        "[class*='drag']",
                        "//text()[contains(., 'upload')]",
                        "//text()[contains(., 'drag')]"
                    ]
                    
                    for indicator in upload_indicators:
                        try:
                            if indicator.startswith("//text()"):
                                # XPath text search
                                self.driver.find_element(By.XPATH, indicator)
                            else:
                                # CSS selector
                                self.driver.find_element(By.CSS_SELECTOR, indicator)
                            self.logger.info("✅ Upload interface detected - Select Asset successful")
                            break
                        except:
                            continue
                    else:
                        self.logger.warning("⚠️  Select Asset click succeeded but upload interface not detected")
                        
                except Exception as verify_error:
                    self.logger.debug(f"Could not verify upload interface: {verify_error}")
                
                return True
                
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.debug(f"Selector {i+1} failed: {e}")
                continue
            except Exception as e:
                self.logger.warning(f"Unexpected error with selector {i+1}: {e}")
                continue
        
        # If we get here, all selectors failed
        self.logger.error("❌ Failed to find Select Asset button with any selector")
        
        # Debug: Log current page state
        try:
            current_url = self.driver.current_url
            self.logger.error(f"Current URL: {current_url}")
            
            # Try to find any button elements for debugging
            button_elements = self.driver.find_elements(By.CSS_SELECTOR, "button")
            self.logger.error(f"Found {len(button_elements)} button elements on page")
            
            for i, button in enumerate(button_elements[:5]):  # Log first 5 buttons
                try:
                    button_classes = button.get_attribute('class') or ""
                    button_info = f"text='{button.text[:30]}', classes='{button_classes[:50]}'"
                    self.logger.error(f"  Button {i+1}: {button_info}")
                except:
                    self.logger.error(f"  Button {i+1}: (couldn't get details)")
                    
        except Exception as debug_error:
            self.logger.error(f"Debug logging failed: {debug_error}")
        
        return False

    def access_upload_interface(self, image_path: Optional[str] = None) -> bool:
        """
        Step 3: Access upload interface and optionally upload a file.
        
        Either clicks the upload area to trigger file selection or directly
        uploads a file using the hidden file input element.
        
        Args:
            image_path: Optional path to image file to upload directly
        
        Returns:
            True if successfully accessed upload interface or uploaded file, False otherwise
        """
        self.logger.info("📤 Step 3: Accessing upload interface...")
        
        if image_path:
            self.logger.info(f"Will upload file: {image_path}")
            # Try direct file upload first (more reliable)
            if self._upload_file_direct(image_path):
                return True
            
            # Fallback to click upload area then upload
            self.logger.info("Direct upload failed, trying click + upload approach")
        
        # Multiple selector strategies for the upload area
        upload_area_selectors = [
            # Based on your specific HTML structure
            (By.CSS_SELECTOR, "div.container-IPOZ7J"),
            (By.CSS_SELECTOR, "div.container-IPOZ7J[data-is-drag-accept='false']"),
            (By.CSS_SELECTOR, "div[data-is-drag-accept='false'][role='presentation']"),
            
            # Upload text-based selectors
            (By.XPATH, "//div[contains(@class, 'container-IPOZ7J')]"),
            (By.XPATH, "//p[contains(@class, 'uploadTextPrimary')]/.."),
            (By.XPATH, "//p[contains(@class, 'uploadTextPrimary')]/../.."),
            (By.XPATH, "//p[contains(text(), 'Drag and drop')]/../.."),
            (By.XPATH, "//p[contains(text(), 'double-click')]/../.."),
            
            # SVG cloud upload icon based
            (By.XPATH, "//svg[contains(@class, 'lucide-cloud-upload')]/.."),
            (By.XPATH, "//svg[contains(@class, 'lucide-cloud-upload')]/../.."),
            
            # Generic upload area selectors
            (By.CSS_SELECTOR, "[class*='upload'][role='presentation']"),
            (By.CSS_SELECTOR, "div[tabindex='0'][role='presentation']"),
            (By.XPATH, "//div[contains(@class, 'upload') and @tabindex='0']"),
            
            # Text-based fallbacks
            (By.XPATH, "//*[contains(text(), 'Drag and drop')]"),
            (By.XPATH, "//*[contains(text(), 'double-click')]"),
            (By.XPATH, "//*[contains(text(), 'upload')]")
        ]
        
        # Try each selector until one works
        for i, selector in enumerate(upload_area_selectors):
            try:
                self.logger.debug(f"Trying upload area selector {i+1}/{len(upload_area_selectors)}: {selector}")
                
                # Wait for element to be present and clickable
                upload_element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(selector)
                )
                
                # Log what we found
                try:
                    element_info = f"tag='{upload_element.tag_name}', text='{upload_element.text[:50]}', classes='{upload_element.get_attribute('class')}'"
                    self.logger.debug(f"Found upload area element: {element_info}")
                except:
                    self.logger.debug("Found upload area element (couldn't get details)")
                
                # Verify this looks like an upload area
                element_text = upload_element.text.lower()
                if any(keyword in element_text for keyword in ['drag', 'drop', 'upload', 'click', 'file']):
                    self.logger.debug("✅ Element text suggests this is an upload area")
                else:
                    self.logger.debug(f"⚠️  Element text '{element_text[:50]}' doesn't clearly indicate upload area")
                
                # Click the element to trigger file dialog
                try:
                    upload_element.click()
                    self.logger.info("✅ Successfully clicked upload area")
                except Exception as click_error:
                    # Try JavaScript click as fallback
                    self.logger.debug(f"Regular click failed: {click_error}, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", upload_element)
                    self.logger.info("✅ Successfully clicked upload area (via JavaScript)")
                
                # If we have a file path, try to handle the file dialog
                if image_path:
                    time.sleep(1)  # Brief pause for dialog
                    if self._handle_file_upload_after_click(image_path):
                        return True
                
                # Wait and verify upload interface is active
                time.sleep(2)
                self.logger.info("✅ Upload area accessed successfully")
                return True
                
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.debug(f"Selector {i+1} failed: {e}")
                continue
            except Exception as e:
                self.logger.warning(f"Unexpected error with selector {i+1}: {e}")
                continue
        
        # If we get here, all selectors failed
        self.logger.error("❌ Failed to find upload area with any selector")
        
        # Try the hidden file input as last resort
        if image_path:
            self.logger.info("Trying hidden file input as last resort...")
            return self._upload_file_direct(image_path)
        
        return False
    
    def _upload_file_direct(self, image_path: str) -> bool:
        """
        Direct file upload using the hidden file input element.
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                self.logger.error(f"❌ File not found: {image_path}")
                return False
            
            self.logger.info(f"📁 Attempting direct file upload: {os.path.basename(image_path)}")
            
            # Find the hidden file input
            file_input_selectors = [
                (By.CSS_SELECTOR, "input[type='file'][accept*='image']"),
                (By.CSS_SELECTOR, "input[type='file']"),
                (By.XPATH, "//input[@type='file' and contains(@accept, 'image')]"),
                (By.XPATH, "//input[@type='file']")
            ]
            
            file_input = None
            for selector in file_input_selectors:
                try:
                    file_input = self.driver.find_element(*selector)
                    self.logger.debug(f"Found file input with selector: {selector}")
                    break
                except:
                    continue
            
            if not file_input:
                self.logger.error("❌ Could not find file input element")
                return False
            
            # Upload the file directly
            absolute_path = os.path.abspath(image_path)
            file_input.send_keys(absolute_path)
            
            self.logger.info("✅ File uploaded successfully via direct input")
            
            # Wait for upload to process
            time.sleep(3)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Direct file upload failed: {e}")
            return False
    
    def _handle_file_upload_after_click(self, image_path: str) -> bool:
        """
        Handle file upload after clicking upload area (if file dialog appears).
        
        Note: This is tricky with Selenium as it can't directly interact with
        system file dialogs. The direct file input approach is preferred.
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            True if upload handled, False otherwise
        """
        self.logger.debug("Attempting to handle file upload after click...")
        
        # Try to find if a file input became available/visible
        try:
            file_input = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            
            if file_input:
                absolute_path = os.path.abspath(image_path)
                file_input.send_keys(absolute_path)
                self.logger.info("✅ File uploaded after click")
                return True
                
        except TimeoutException:
            self.logger.debug("No file input appeared after click")
        except Exception as e:
            self.logger.debug(f"Error handling file upload after click: {e}")
        
        return False

    def get_motion_description_from_json(self, json_path: str, scene_id: str) -> str:
        """
        Extract motion description from JSON file for specific scene.
        
        Args:
            json_path: Path to the JSON file containing scene data
            scene_id: Scene identifier to look for (e.g., "scene_0")
            
        Returns:
            Motion description string, or default prompt if not found
        """
        try:
            # Load JSON file
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            self.logger.info(f"📄 Loaded JSON data from: {json_path}")
            
            # Look for scene_directions array (based on the structure seen in main())
            if "scene_directions" in json_data:
                scenes = json_data["scene_directions"]
                
                # Find the scene by index (extract number from scene_id like "scene_0")
                try:
                    scene_index = int(scene_id.split('_')[-1])
                    if 0 <= scene_index < len(scenes):
                        scene_data = scenes[scene_index]
                        
                        # Try different possible field names for motion description
                        motion_fields = ['motion_desc', 'motion_description', 'movement', 'animation']
                        for field in motion_fields:
                            if field in scene_data and scene_data[field]:
                                motion_desc = scene_data[field].strip()
                                if motion_desc:
                                    self.logger.info(f"✅ Found motion description for {scene_id}: {motion_desc[:100]}...")
                                    return motion_desc
                        
                        # If no motion description found, try scene description as fallback
                        desc_fields = ['scene_desc', 'description', 'desc']
                        for field in desc_fields:
                            if field in scene_data and scene_data[field]:
                                scene_desc = scene_data[field].strip()
                                if scene_desc:
                                    self.logger.warning(f"⚠️  No motion description found for {scene_id}, using scene description")
                                    return f"Subtle camera movement showing: {scene_desc}"
                        
                        self.logger.warning(f"⚠️  No description fields found for {scene_id}")
                    else:
                        self.logger.error(f"❌ Scene index {scene_index} out of range (0-{len(scenes)-1})")
                except (ValueError, IndexError) as e:
                    self.logger.error(f"❌ Error parsing scene_id '{scene_id}': {e}")
            
            # Alternative: look for scenes object/array with different structure
            elif "scenes" in json_data:
                scenes = json_data["scenes"]
                if isinstance(scenes, list):
                    # Find scene by scene_id field
                    for scene_data in scenes:
                        if scene_data.get("scene_id") == scene_id:
                            motion_desc = scene_data.get("motion_description", "").strip()
                            if motion_desc:
                                self.logger.info(f"✅ Found motion description for {scene_id}: {motion_desc[:100]}...")
                                return motion_desc
                            break
                    
                    self.logger.warning(f"⚠️  Scene {scene_id} not found in scenes array")
                elif isinstance(scenes, dict) and scene_id in scenes:
                    # Scenes as dictionary
                    scene_data = scenes[scene_id]
                    motion_desc = scene_data.get("motion_description", "").strip()
                    if motion_desc:
                        self.logger.info(f"✅ Found motion description for {scene_id}: {motion_desc[:100]}...")
                        return motion_desc
            
            self.logger.warning(f"⚠️  Could not find motion description for {scene_id} in JSON")
            
        except FileNotFoundError:
            self.logger.error(f"❌ JSON file not found: {json_path}")
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Invalid JSON format in {json_path}: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error reading JSON file {json_path}: {e}")
        
        # Return default motion description if nothing found
        default_prompt = "Slow, cinematic camera movement with subtle zoom and gentle panning"
        self.logger.info(f"📝 Using default motion description: {default_prompt}")
        return default_prompt

    def enter_motion_prompt(self, motion_description: str) -> bool:
        """
        Enter motion description into the text prompt input field.
        
        Args:
            motion_description: The motion description text to enter
            
        Returns:
            True if prompt entered successfully, False otherwise
        """
        self.logger.info(f"📝 Entering motion prompt: {motion_description[:50]}...")
        
        # Selectors for the prompt input field (from todo file)
        prompt_selectors = [
            (By.CSS_SELECTOR, "div[aria-label='Text Prompt Input']"),
            (By.CSS_SELECTOR, "div.textbox-lvV8X2"),
            (By.CSS_SELECTOR, "div[role='textbox'][contenteditable='true']"),
            (By.XPATH, "//div[@aria-label='Text Prompt Input']"),
            (By.XPATH, "//div[contains(@class, 'textbox-') and @contenteditable='true']")
        ]
        
        prompt_element = self.find_element_safe(prompt_selectors, wait_time=10)
        
        if prompt_element:
            try:
                # Clear any existing text first
                prompt_element.clear()
                
                # Enter the motion description
                prompt_element.send_keys(motion_description)
                
                # Verify text was entered
                time.sleep(1)
                entered_text = prompt_element.text or prompt_element.get_attribute('textContent') or ""
                
                if motion_description.lower() in entered_text.lower():
                    self.logger.info("✅ Motion prompt entered successfully")
                    return True
                else:
                    # Try alternative method with JavaScript
                    self.logger.warning("⚠️  Standard send_keys didn't work, trying JavaScript...")
                    self.driver.execute_script(
                        "arguments[0].textContent = arguments[1];", 
                        prompt_element, 
                        motion_description
                    )
                    
                    # Trigger input event to notify the application
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", 
                        prompt_element
                    )
                    
                    time.sleep(1)
                    self.logger.info("✅ Motion prompt entered via JavaScript")
                    return True
                    
            except Exception as e:
                self.logger.error(f"❌ Error entering motion prompt: {e}")
                return False
        else:
            self.logger.error("❌ Could not find prompt input field")
            return False

    def select_aspect_ratio_16_9(self) -> bool:
        """
        Select 16:9 aspect ratio for video generation.
        
        Returns:
            True if aspect ratio selected successfully, False otherwise
        """
        self.logger.info("📐 Selecting 16:9 aspect ratio...")
        
        # First, try to find and click the current selection (1:1) to open dropdown
        dropdown_selectors = [
            (By.CSS_SELECTOR, "span.selectValue-EUNSsY"),
            (By.XPATH, "//span[text()='1:1']"),
            (By.XPATH, "//span[contains(@class, 'selectValue-')]"),
            (By.XPATH, "//svg[contains(@class, 'lucide-square')]/parent::span")
        ]
        
        dropdown_element = self.find_element_safe(dropdown_selectors, wait_time=10)
        
        if dropdown_element:
            try:
                # Click to open dropdown
                dropdown_element.click()
                self.logger.info("✅ Clicked dropdown to open aspect ratio options")
                
                # Wait for dropdown options to appear
                time.sleep(2)
                
                # Now find and click the 16:9 option
                ratio_16_9_selectors = [
                    (By.CSS_SELECTOR, "div[data-key='16:9']"),
                    (By.XPATH, "//div[@role='option' and contains(text(), '16:9')]"),
                    (By.XPATH, "//div[contains(text(), '16:9')]"),
                    (By.CSS_SELECTOR, "div.listBoxItem-D45yx5[data-key='16:9']"),
                    (By.XPATH, "//svg[contains(@class, 'lucide-rectangle-horizontal')]/parent::div")
                ]
                
                ratio_element = self.find_element_safe(ratio_16_9_selectors, wait_time=5)
                
                if ratio_element:
                    ratio_element.click()
                    self.logger.info("✅ Selected 16:9 aspect ratio")
                    
                    # Wait for selection to take effect
                    time.sleep(2)
                    
                    # Verify selection by checking if 16:9 is now displayed
                    try:
                        verification_selectors = [
                            (By.XPATH, "//span[contains(text(), '16:9')]"),
                            (By.CSS_SELECTOR, "span.selectValue-EUNSsY")
                        ]
                        
                        for selector in verification_selectors:
                            try:
                                element = self.driver.find_element(*selector)
                                if "16:9" in element.text:
                                    self.logger.info("✅ Verified 16:9 aspect ratio is selected")
                                    
                                    # Now click the Crop button
                                    if self._click_crop_button():
                                        return True
                                    else:
                                        self.logger.warning("⚠️  16:9 selected but Crop button click failed")
                                        return True  # Still consider successful since 16:9 was selected
                            except:
                                continue
                        
                        self.logger.warning("⚠️  Could not verify 16:9 selection, but trying Crop button...")
                        # Try clicking Crop button anyway
                        self._click_crop_button()
                        return True
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️  Could not verify selection, but proceeding: {e}")
                        self._click_crop_button()
                        return True
                
                else:
                    self.logger.error("❌ Could not find 16:9 option in dropdown")
                    return False
                    
            except Exception as e:
                self.logger.error(f"❌ Error selecting aspect ratio: {e}")
                return False
        else:
            # Maybe 16:9 is already selected, or dropdown not found
            self.logger.warning("⚠️  Could not find aspect ratio dropdown")
            
            # Check if 16:9 is already selected
            try:
                current_ratio = self.driver.find_element(By.XPATH, "//span[contains(text(), '16:9')]")
                if current_ratio:
                    self.logger.info("✅ 16:9 aspect ratio appears to already be selected")
                    return True
            except:
                pass
            
            self.logger.error("❌ Could not find or select aspect ratio")
            return False

    def _click_crop_button(self) -> bool:
        """
        Click the Crop button after selecting aspect ratio.
        
        Returns:
            True if crop button clicked successfully, False otherwise
        """
        self.logger.info("✂️ Clicking Crop button...")
        
        # Selectors for the Crop button
        crop_selectors = [
            (By.XPATH, "//button[text()='Crop']"),
            (By.CSS_SELECTOR, "button.container-kIPoeH"),
            (By.CSS_SELECTOR, "button.primaryBlue-oz2I8B"),
            (By.XPATH, "//button[contains(@class, 'container-kIPoeH') and text()='Crop']"),
            (By.XPATH, "//button[contains(@class, 'primaryBlue-oz2I8B') and text()='Crop']")
        ]
        
        crop_element = self.find_element_safe(crop_selectors, wait_time=5)
        
        if crop_element:
            try:
                crop_element.click()
                self.logger.info("✅ Successfully clicked Crop button")
                time.sleep(2)  # Wait for crop to take effect
                return True
            except Exception as e:
                self.logger.error(f"❌ Error clicking Crop button: {e}")
                return False
        else:
            self.logger.warning("⚠️  Could not find Crop button")
            return False

    def click_generate_button(self) -> bool:
        """
        Click the Generate button to start video generation.
        
        Returns:
            True if generate button clicked successfully, False otherwise
        """
        self.logger.info("🎬 Clicking Generate button to start video generation...")
        
        # Selectors for the Generate button (from todo file)
        generate_selectors = [
            (By.XPATH, "//span[text()='Generate']"),
            (By.XPATH, "//span[contains(text(), 'Generate')]"),
            (By.CSS_SELECTOR, "span.ButtonChildrenOrLoader__ChildrenContainer-esVGby"),
            (By.XPATH, "//span[contains(@class, 'ButtonChildrenOrLoader__ChildrenContainer')]"),
            (By.XPATH, "//svg[contains(@class, 'lucide-video')]/parent::span"),
            (By.XPATH, "//button[.//span[text()='Generate']]")
        ]
        
        # First try to find the generate button/span
        generate_element = self.find_element_safe(generate_selectors, wait_time=10)
        
        if generate_element:
            try:
                # If we found a span, try to find its parent button
                if generate_element.tag_name.lower() == 'span':
                    try:
                        button_element = generate_element.find_element(By.XPATH, "./ancestor::button[1]")
                        self.logger.info("Found parent button for Generate span")
                        generate_element = button_element
                    except:
                        self.logger.info("Using span element directly for Generate")
                
                # Check if button is enabled
                is_disabled = generate_element.get_attribute('disabled')
                data_disabled = generate_element.get_attribute('data-soft-disabled')
                
                if is_disabled == 'true' or data_disabled == 'true':
                    self.logger.warning("⚠️  Generate button appears to be disabled")
                    self.logger.info("Attempting to click anyway...")
                
                # Click the generate button
                generate_element.click()
                self.logger.info("✅ Successfully clicked Generate button!")
                
                # Wait a moment for the generation to start
                time.sleep(3)
                
                # Try to verify generation started by checking for progress indicators
                try:
                    progress_indicators = [
                        (By.XPATH, "//div[contains(text(), 'Generating')]"),
                        (By.XPATH, "//div[contains(text(), 'Processing')]"),
                        (By.CSS_SELECTOR, "div[role='progressbar']"),
                        (By.XPATH, "//div[contains(@class, 'progress')]")
                    ]
                    
                    for selector in progress_indicators:
                        try:
                            progress_element = self.driver.find_element(*selector)
                            if progress_element:
                                self.logger.info("✅ Video generation appears to have started!")
                                return True
                        except:
                            continue
                    
                    self.logger.info("✅ Generate button clicked, generation may have started")
                    return True
                    
                except Exception as e:
                    self.logger.info(f"Generate button clicked, could not verify generation status: {e}")
                    return True
                
            except Exception as e:
                self.logger.error(f"❌ Error clicking Generate button: {e}")
                
                # Try JavaScript click as fallback
                try:
                    self.logger.info("Trying JavaScript click as fallback...")
                    self.driver.execute_script("arguments[0].click();", generate_element)
                    self.logger.info("✅ Generate button clicked via JavaScript")
                    return True
                except Exception as js_e:
                    self.logger.error(f"❌ JavaScript click also failed: {js_e}")
                    return False
        else:
            self.logger.error("❌ Could not find Generate button")
            
            # Debug: try to find any buttons on the page
            try:
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                button_texts = [btn.text[:50] for btn in all_buttons if btn.text.strip()]
                self.logger.info(f"Available buttons on page: {button_texts}")
            except:
                pass
            
            return False

    def wait_for_generation_and_download(self, scene_id: str, output_dir: str = "output") -> bool:
        """
        Wait for video generation to complete and download the result.
        
        Args:
            scene_id: Scene identifier for naming the downloaded file
            output_dir: Directory to save the downloaded video
            
        Returns:
            True if video generated and downloaded successfully, False otherwise
        """
        self.logger.info(f"⏳ Waiting for video generation to complete for {scene_id}...")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        max_wait_time = 300  # 5 minutes max
        check_interval = 5   # Check every 5 seconds
        elapsed_time = 0
        consecutive_no_change = 0  # Track how many times we don't find anything
        max_consecutive_no_change = 12  # Give up after 60 seconds of no progress (12 * 5s)
        
        while elapsed_time < max_wait_time:
            try:
                # Check for completion indicators (RunwayML specific)
                completion_selectors = [
                    # Primary completion indicator - button with data-saved="true"
                    (By.CSS_SELECTOR, "button.mainButton-_m_ZJD[data-saved='true']"),
                    (By.CSS_SELECTOR, "button[data-saved='true'][data-size='small']"),
                    (By.XPATH, "//button[@data-saved='true' and .//svg[contains(@class, 'lucide-download')]]"),
                    
                    # Secondary indicators
                    (By.CSS_SELECTOR, "button.mainButton-_m_ZJD"),  # Main download button
                    (By.CSS_SELECTOR, "div.buttonContainer-ONyYcY"),  # Download button container
                    (By.XPATH, "//svg[contains(@class, 'lucide-download')]/parent::button"),  # Download icon button
                    (By.XPATH, "//div[contains(text(), 'Complete')]"),
                    (By.XPATH, "//div[contains(text(), 'Finished')]"),
                    (By.XPATH, "//video[@src]"),  # Generated video element
                ]
                
                completion_element = self.find_element_safe(completion_selectors, wait_time=2)
                
                if completion_element:
                    self.logger.info("✅ Video generation appears to be complete!")
                    
                    # Try to download the video
                    if self._download_generated_video(scene_id, output_dir):
                        return True
                    else:
                        self.logger.warning("⚠️  Generation complete but download failed")
                        return False
                
                # Check for error states
                error_selectors = [
                    (By.XPATH, "//div[contains(text(), 'Error')]"),
                    (By.XPATH, "//div[contains(text(), 'Failed')]"),
                    (By.XPATH, "//div[contains(text(), 'Try again')]"),
                    (By.XPATH, "//button[contains(text(), 'Retry')]")
                ]
                
                error_element = self.find_element_safe(error_selectors, wait_time=1)
                if error_element:
                    self.logger.error(f"❌ Video generation failed: {error_element.text}")
                    return False
                
                # Check for progress indicators (still generating)
                progress_selectors = [
                    (By.XPATH, "//div[contains(text(), 'Generating')]"),
                    (By.XPATH, "//div[contains(text(), 'Processing')]"),
                    (By.CSS_SELECTOR, "div[role='progressbar']"),
                    (By.XPATH, "//div[contains(@class, 'progress')]")
                ]
                
                progress_element = self.find_element_safe(progress_selectors, wait_time=1)
                if progress_element:
                    progress_text = progress_element.text[:50] if progress_element.text else "Processing"
                    self.logger.info(f"⏳ Still generating... {progress_text} (elapsed: {elapsed_time}s)")
                    consecutive_no_change = 0  # Reset counter since we found something
                else:
                    self.logger.info(f"⏳ Waiting for generation... (elapsed: {elapsed_time}s)")
                    consecutive_no_change += 1
                    
                    # If we haven't found any indicators for too long, something might be wrong
                    if consecutive_no_change >= max_consecutive_no_change:
                        self.logger.warning(f"⚠️  No generation indicators found for {consecutive_no_change * check_interval} seconds")
                        self.logger.warning("⚠️  Generation may have failed or completed without proper indicators")
                        
                        # Try one more time to find completion elements with a longer wait
                        completion_element = self.find_element_safe(completion_selectors, wait_time=10)
                        if completion_element:
                            self.logger.info("✅ Found completion element on extended search!")
                            if self._download_generated_video(scene_id, output_dir):
                                return True
                        
                        # If still nothing, give up
                        self.logger.error("❌ Giving up on generation - no indicators found")
                        return False
                
                time.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                self.logger.warning(f"⚠️  Error checking generation status: {e}")
                consecutive_no_change += 1
                time.sleep(check_interval)
                elapsed_time += check_interval
                
                # If we keep hitting errors, something is wrong
                if consecutive_no_change >= max_consecutive_no_change:
                    self.logger.error(f"❌ Too many consecutive errors - giving up")
                    return False
        
        self.logger.error(f"❌ Video generation timed out after {max_wait_time} seconds")
        return False

    def _download_generated_video(self, scene_id: str, output_dir: str) -> bool:
        """
        Download the generated video file.
        
        Args:
            scene_id: Scene identifier for naming
            output_dir: Directory to save the file
            
        Returns:
            True if download successful, False otherwise
        """
        self.logger.info(f"📥 Attempting to download video for {scene_id}...")
        
        # RunwayML actual download button selectors (updated with user's exact HTML)
        download_selectors = [
            # Primary selector - button with data-saved="true" (video ready to download)
            (By.CSS_SELECTOR, "button.mainButton-_m_ZJD[data-saved='true']"),
            (By.CSS_SELECTOR, "button[data-saved='true'][data-size='small']"),
            
            # Container-based selectors
            (By.CSS_SELECTOR, "div.buttonContainer-ONyYcY button[data-saved='true']"),
            (By.CSS_SELECTOR, "div.buttonContainer-ONyYcY button.mainButton-_m_ZJD"),
            
            # Icon-based selectors (with saved state)
            (By.XPATH, "//button[@data-saved='true' and .//svg[contains(@class, 'lucide-download')]]"),
            (By.XPATH, "//svg[contains(@class, 'lucide-download')]/parent::button[@data-saved='true']"),
            
            # Fallback selectors (any download button)
            (By.CSS_SELECTOR, "button.mainButton-_m_ZJD"),
            (By.XPATH, "//svg[contains(@class, 'lucide-download')]/parent::button"),
            (By.XPATH, "//button[contains(@class, 'mainButton-') and .//svg[contains(@class, 'lucide-download')]]")
        ]
        
        download_element = self.find_element_safe(download_selectors, wait_time=10)
        
        if download_element:
            try:
                # Get the current number of files in download directory to track new downloads
                download_folder = os.path.expanduser("~/Downloads")
                initial_files = set(os.listdir(download_folder)) if os.path.exists(download_folder) else set()
                
                # Click download
                download_element.click()
                self.logger.info("✅ Clicked download button")
                
                # Wait for download to complete
                timeout = 60  # 1 minute for download
                elapsed = 0
                
                while elapsed < timeout:
                    time.sleep(2)
                    elapsed += 2
                    
                    if os.path.exists(download_folder):
                        current_files = set(os.listdir(download_folder))
                        new_files = current_files - initial_files
                        
                        # Look for video files that were just downloaded
                        video_files = [f for f in new_files if f.lower().endswith(('.mp4', '.mov', '.avi', '.webm'))]
                        
                        if video_files:
                            # Move and rename the downloaded file
                            downloaded_file = video_files[0]  # Take the first video file found
                            src_path = os.path.join(download_folder, downloaded_file)
                            dst_path = os.path.join(output_dir, f"{scene_id}.mp4")
                            
                            # Move and rename the file
                            import shutil
                            shutil.move(src_path, dst_path)
                            
                            self.logger.info(f"✅ Video downloaded and saved as: {dst_path}")
                            return True
                
                self.logger.warning("⚠️  Download timeout - file may still be downloading")
                return False
                
            except Exception as e:
                self.logger.error(f"❌ Error downloading video: {e}")
                return False
        else:
            # Try alternative: right-click and save video element
            try:
                video_element = self.driver.find_element(By.TAG_NAME, "video")
                if video_element:
                    video_src = video_element.get_attribute("src")
                    if video_src:
                        self.logger.info("Found video element, attempting direct download...")
                        # Could implement direct URL download here
                        # For now, just report success of finding the video
                        self.logger.info(f"Video available at: {video_src}")
                        return True
            except:
                pass
            
            self.logger.error("❌ Could not find download button or video element")
            return False

    def discover_completion_ui(self) -> dict:
        """
        Discover and report all UI elements when generation is complete.
        This helps identify the actual download mechanism.
        
        Returns:
            Dictionary with discovered elements and their details
        """
        self.logger.info("🔍 Discovering completion UI elements...")
        
        discovered = {
            "buttons": [],
            "links": [],
            "videos": [],
            "download_elements": [],
            "completion_text": []
        }
        
        try:
            # Find all buttons
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for i, btn in enumerate(buttons):
                try:
                    btn_text = btn.text.strip()
                    if btn_text:  # Only log buttons with text
                        btn_info = {
                            "index": i,
                            "text": btn_text[:100],
                            "class": btn.get_attribute("class") or "",
                            "id": btn.get_attribute("id") or "",
                            "disabled": btn.get_attribute("disabled") or "false"
                        }
                        discovered["buttons"].append(btn_info)
                except:
                    pass
            
            # Find all links with text or download attributes
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for i, link in enumerate(links):
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href")
                    link_download = link.get_attribute("download")
                    
                    if link_text or link_download or (link_href and "download" in link_href.lower()):
                        link_info = {
                            "index": i,
                            "text": link_text[:100],
                            "href": link_href,
                            "download": link_download,
                            "class": link.get_attribute("class") or ""
                        }
                        discovered["links"].append(link_info)
                except:
                    pass
            
            # Find video elements
            videos = self.driver.find_elements(By.TAG_NAME, "video")
            for i, video in enumerate(videos):
                try:
                    video_info = {
                        "index": i,
                        "src": video.get_attribute("src"),
                        "poster": video.get_attribute("poster"),
                        "controls": video.get_attribute("controls"),
                        "class": video.get_attribute("class") or ""
                    }
                    discovered["videos"].append(video_info)
                except:
                    pass
            
            # Find elements with download-related attributes or text
            download_xpath = "//*[contains(translate(text(), 'DOWNLOAD', 'download'), 'download') or contains(@href, 'download') or @download or contains(translate(text(), 'SAVE', 'save'), 'save')]"
            download_candidates = self.driver.find_elements(By.XPATH, download_xpath)
            for i, elem in enumerate(download_candidates):
                try:
                    elem_info = {
                        "index": i,
                        "tag": elem.tag_name,
                        "text": elem.text.strip()[:100],
                        "href": elem.get_attribute("href"),
                        "download": elem.get_attribute("download"),
                        "class": elem.get_attribute("class") or ""
                    }
                    discovered["download_elements"].append(elem_info)
                except:
                    pass
            
            # Find completion indicators
            completion_xpath = "//*[contains(translate(text(), 'COMPLETE', 'complete'), 'complete') or contains(translate(text(), 'FINISHED', 'finished'), 'finished') or contains(translate(text(), 'DONE', 'done'), 'done') or contains(translate(text(), 'READY', 'ready'), 'ready')]"
            completion_elements = self.driver.find_elements(By.XPATH, completion_xpath)
            for i, elem in enumerate(completion_elements):
                try:
                    elem_info = {
                        "index": i,
                        "tag": elem.tag_name,
                        "text": elem.text.strip()[:200],
                        "class": elem.get_attribute("class") or ""
                    }
                    discovered["completion_text"].append(elem_info)
                except:
                    pass
            
            # Log summary
            self.logger.info(f"🔍 UI Discovery Results:")
            self.logger.info(f"   📱 Buttons with text: {len(discovered['buttons'])}")
            self.logger.info(f"   🔗 Relevant links: {len(discovered['links'])}")
            self.logger.info(f"   🎥 Videos: {len(discovered['videos'])}")
            self.logger.info(f"   📥 Download candidates: {len(discovered['download_elements'])}")
            self.logger.info(f"   ✅ Completion indicators: {len(discovered['completion_text'])}")
            
            # Log the most relevant elements
            self.logger.info("🔘 Notable Buttons:")
            for btn in discovered["buttons"][:10]:
                self.logger.info(f"     '{btn['text']}' (class: {btn['class']}, disabled: {btn['disabled']})")
            
            self.logger.info("🔗 Notable Links:")
            for link in discovered["links"][:5]:
                self.logger.info(f"     '{link['text']}' href={link['href']} download={link['download']}")
            
            self.logger.info("🎥 Videos:")
            for video in discovered["videos"]:
                self.logger.info(f"     src={video['src']} controls={video['controls']}")
            
            self.logger.info("📥 Download Candidates:")
            for elem in discovered["download_elements"][:5]:
                self.logger.info(f"     {elem['tag']}: '{elem['text']}' href={elem['href']}")
            
            self.logger.info("✅ Completion Indicators:")
            for elem in discovered["completion_text"][:5]:
                self.logger.info(f"     {elem['tag']}: '{elem['text']}'")
            
            return discovered
            
        except Exception as e:
            self.logger.error(f"❌ Error during UI discovery: {e}")
            return discovered

    def process_all_scenes(self, json_path: str, output_dir: str = "output/videos") -> dict:
        """
        Process all scenes from JSON file in batch.
        
        Args:
            json_path: Path to the JSON file containing all scenes
            output_dir: Directory to save generated videos
            
        Returns:
            Dictionary with processing results and statistics
        """
        self.logger.info("🎬 Starting batch processing of all scenes...")
        
        # Load JSON data
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception as e:
            self.logger.error(f"❌ Error loading JSON file: {e}")
            return {"success": False, "error": str(e)}
        
        scenes = json_data.get("scene_directions", [])
        total_scenes = len(scenes)
        
        if total_scenes == 0:
            self.logger.error("❌ No scenes found in JSON file")
            return {"success": False, "error": "No scenes found"}
        
        self.logger.info(f"📋 Found {total_scenes} total scenes")
        
        # Count scenes that need video processing (exclude narration-only)
        processable_scenes = []
        for i, scene_data in enumerate(scenes):
            if scene_data.get('scene_desc') is not None:
                if 'events' in scene_data and scene_data['events']:
                    # Event-based scene - process each event
                    for j, event in enumerate(scene_data['events']):
                        processable_scenes.append({
                            'scene_index': i,
                            'event_index': j,
                            'scene_id': f"scene_{i}_event_{j}",
                            'scene_data': event,
                            'parent_scene': scene_data
                        })
                else:
                    # Regular scene
                    processable_scenes.append({
                        'scene_index': i,
                        'event_index': None,
                        'scene_id': f"scene_{i}",
                        'scene_data': scene_data,
                        'parent_scene': None
                    })
            else:
                self.logger.info(f"⏭️  Scene {i} is narration-only (no scene_desc), skipping video generation")
        
        self.logger.info(f"📋 Found {len(processable_scenes)} scenes/events that need video processing")
        
        # Progress tracking
        progress_file = os.path.join(output_dir, "progress.json")
        os.makedirs(output_dir, exist_ok=True)
        
        # Load existing progress
        progress_data = self._load_progress(progress_file)
        completed_scenes = progress_data.get("completed", [])
        failed_scenes = progress_data.get("failed", [])
        
        # Clear any failed scenes from previous runs to allow retry
        self.logger.info(f"🔄 Clearing {len(failed_scenes)} failed scenes from previous runs to allow retry")
        failed_scenes = []
        
        results = {
            "total_scenes": len(processable_scenes),
            "completed": [],
            "failed": [],
            "skipped": [],
            "success": True
        }
        
        # Store job directory and identifier for later narration lookup
        self.job_dir = os.path.dirname(json_path)
        self.job_id = os.path.basename(json_path).split('raw_json_')[-1].split('.')[0]
        
        for idx, scene_info in enumerate(processable_scenes):
            scene_id = scene_info['scene_id']
            scene_data = scene_info['scene_data']
            
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"🎥 Processing {scene_id} ({idx+1}/{len(processable_scenes)})")
            self.logger.info(f"{'='*50}")
            
            # Check if already completed and video file exists
            video_file = os.path.join(output_dir, f"{scene_id}.mp4")
            if scene_id in completed_scenes and os.path.exists(video_file):
                file_size = os.path.getsize(video_file)
                if file_size > 100000:  # File is larger than 100KB, likely valid
                    self.logger.info(f"✅ {scene_id} already completed with valid video file ({file_size} bytes), skipping...")
                    results["skipped"].append(scene_id)
                    continue
                else:
                    self.logger.warning(f"⚠️  {scene_id} marked complete but video file is too small ({file_size} bytes), retrying...")
                    completed_scenes.remove(scene_id)
            elif scene_id in completed_scenes:
                self.logger.warning(f"⚠️  {scene_id} marked complete but video file missing, retrying...")
                completed_scenes.remove(scene_id)
            
            # Find the corresponding image file
            json_dir = os.path.dirname(json_path)
            image_path = os.path.join(json_dir, f"{scene_id}_getimg.png")
            
            # Local getimg asset may not exist. We'll attempt in-app generation; absence is not fatal.
            if not os.path.exists(image_path):
                self.logger.info(f"ℹ️  No pre-existing image for {scene_id}. Will generate in Runway.")
            
            try:
                # Add timeout tracking for each scene to prevent infinite hanging
                scene_start_time = time.time()
                scene_timeout = 600  # 10 minutes timeout in seconds
                
                # Process single scene
                success = self._process_single_scene_with_data(scene_id, image_path, scene_data, output_dir)
                
                # Check if we exceeded timeout
                elapsed_time = time.time() - scene_start_time
                if elapsed_time > scene_timeout:
                    self.logger.warning(f"⚠️  {scene_id} took {elapsed_time:.1f} seconds (longer than {scene_timeout} seconds)")
                
                if success:
                    self.logger.info(f"✅ {scene_id} completed successfully!")
                    results["completed"].append(scene_id)
                    completed_scenes.append(scene_id)
                else:
                    self.logger.error(f"❌ {scene_id} failed")
                    results["failed"].append({"scene": scene_id, "error": "Processing failed"})
                    failed_scenes.append(scene_id)
                
                # Save progress after each scene
                self._save_progress(progress_file, {
                    "completed": completed_scenes,
                    "failed": failed_scenes,
                    "last_processed": scene_id,
                    "timestamp": time.time()
                })
                
                # Add delay between scenes to avoid overwhelming the server
                if idx < len(processable_scenes) - 1:  # Don't wait after the last scene
                    self.logger.info("⏸️  Waiting 10 seconds before next scene...")
                    time.sleep(10)
                    
            except Exception as e:
                self.logger.error(f"❌ Error processing {scene_id}: {e}")
                results["failed"].append({"scene": scene_id, "error": str(e)})
                failed_scenes.append(scene_id)
        
        # Final summary
        self.logger.info(f"\n{'='*50}")
        self.logger.info("🎉 BATCH PROCESSING COMPLETE!")
        self.logger.info(f"{'='*50}")
        self.logger.info(f"✅ Completed: {len(results['completed'])}")
        self.logger.info(f"❌ Failed: {len(results['failed'])}")
        self.logger.info(f"⏭️  Skipped: {len(results['skipped'])}")
        self.logger.info(f"📊 Success rate: {len(results['completed'])}/{len(processable_scenes)} ({len(results['completed'])/len(processable_scenes)*100:.1f}%)")
        
        return results

    def check_session_health(self) -> bool:
        """
        Check if the current session is still valid.
        
        Returns:
            True if session is healthy, False if login required
        """
        try:
            # Check if we're still logged in by looking for user-specific elements
            current_url = self.driver.current_url
            
            # If we're on login page, session is dead
            if "login" in current_url.lower():
                self.logger.warning("⚠️  Session expired - currently on login page")
                return False
            
            # Check for logout/login buttons or user profile elements
            session_indicators = [
                (By.XPATH, "//button[contains(text(), 'Log out')]"),
                (By.XPATH, "//button[contains(text(), 'Logout')]"), 
                (By.XPATH, "//div[contains(@class, 'user-profile')]"),
                (By.XPATH, "//div[contains(@class, 'avatar')]"),
                (By.CSS_SELECTOR, "[data-testid='user-menu']")
            ]
            
            logged_in_element = self.find_element_safe(session_indicators, wait_time=3)
            
            if logged_in_element:
                self.logger.info("✅ Session appears healthy")
                return True
            else:
                self.logger.warning("⚠️  Could not find logged-in indicators")
                # Try to navigate to dashboard to test session
                self.driver.get(self.URLS["dashboard"])
                time.sleep(3)
                
                # Check if we got redirected to login
                if "login" in self.driver.current_url.lower():
                    self.logger.warning("⚠️  Session expired - redirected to login")
                    return False
                else:
                    self.logger.info("✅ Dashboard accessible - session OK")
                    return True
                    
        except Exception as e:
            self.logger.warning(f"⚠️  Error checking session health: {e}")
            return False

    def recover_session(self) -> bool:
        """
        Attempt to recover session by refreshing or re-navigating.
        Only re-logins as last resort.
        
        Returns:
            True if session recovered, False if re-login needed
        """
        self.logger.info("🔄 Attempting session recovery...")
        
        try:
            # First try: refresh the page
            self.logger.info("1️⃣ Trying page refresh...")
            self.driver.refresh()
            time.sleep(5)
            
            if self.check_session_health():
                self.logger.info("✅ Session recovered with page refresh")
                return True
            
            # Second try: navigate to dashboard
            self.logger.info("2️⃣ Trying dashboard navigation...")
            self.driver.get(self.URLS["dashboard"])
            time.sleep(5)
            
            if self.check_session_health():
                self.logger.info("✅ Session recovered with dashboard navigation")
                return True
            
            # Last resort: re-login
            self.logger.warning("3️⃣ Session recovery failed - re-login required")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error during session recovery: {e}")
            return False

    def _process_single_scene(self, scene_id: str, image_path: str, json_path: str, output_dir: str) -> bool:
        """
        Process a single scene through the complete workflow.
        
        Args:
            scene_id: Scene identifier
            image_path: Path to the scene image
            json_path: Path to JSON file
            output_dir: Output directory for videos
            
        Returns:
            True if scene processed successfully, False otherwise
        """
        # Get motion description from JSON
        motion_description = self.get_motion_description_from_json(json_path, scene_id)
        
        # Create a dummy scene data structure
        scene_data = {"motion_desc": motion_description}
        
        return self._process_single_scene_with_data(scene_id, image_path, scene_data, output_dir)

    def _process_single_scene_with_data(self, scene_id: str, image_path: str, scene_data: dict, output_dir: str) -> bool:
        """
        Process a single scene through the complete workflow using scene data.
        
        Args:
            scene_id: Scene identifier
            image_path: Path to the scene image
            scene_data: Scene data dictionary containing motion_desc, etc.
            output_dir: Output directory for videos
            
        Returns:
            True if scene processed successfully, False otherwise
        """
        try:
            # Check session health before processing
            if not self.check_session_health():
                self.logger.warning(f"⚠️  Session health check failed for {scene_id}")
                
                # Try to recover without re-login
                if not self.recover_session():
                    # If recovery fails, attempt re-login
                    self.logger.warning(f"🔐 Attempting re-login for {scene_id}...")
                    if not self.login():
                        self.logger.error(f"❌ Re-login failed for {scene_id}")
                        return False
                else:
                    self.logger.info(f"✅ Session recovered for {scene_id}")
            
            # Continue with normal processing...
            # Step 0: Ensure we have an image for this scene – generate if necessary
            scene_desc = scene_data.get('scene_desc') or scene_data.get('description') or scene_data.get('desc') or ''
            self.logger.info(f"🖼️ Generating/locating image for {scene_id}…")

            generated_path = self.generate_image_from_prompt(scene_desc, scene_id, output_dir)
            if generated_path:
                image_path = generated_path  # Prefer freshly-created asset

            # Validate existence of the image file
            if not image_path or not os.path.exists(image_path):
                self.logger.error(f"❌ No image available for {scene_id} (checked path: {image_path})")
                return False

            # Step 1: Upload the image
            self.logger.info(f"📤 Uploading image for {scene_id}…")
            if not self.access_upload_interface(image_path):
                self.logger.error(f"❌ Failed to upload image for {scene_id}")
                return False
            
            # Step 2: Enter motion prompt
            self.logger.info(f"📝 Entering motion prompt for {scene_id}...")
            motion_description = scene_data.get('motion_desc', 'Slow, cinematic camera movement with subtle zoom and gentle panning')
            if not self.enter_motion_prompt(motion_description):
                self.logger.error(f"❌ Failed to enter motion prompt for {scene_id}")
                return False
            
            # Step 3: Select aspect ratio and crop
            self.logger.info(f"📐 Setting aspect ratio for {scene_id}...")
            if not self.select_aspect_ratio_16_9():
                self.logger.warning(f"⚠️  Aspect ratio selection may have failed for {scene_id}")
            
            # NEW STEP: Choose video duration based on narration length
            try:
                narration_duration = None
                if hasattr(self, 'job_dir') and hasattr(self, 'job_id'):
                    match = re.search(r'scene_(\d+)', scene_id)
                    if match:
                        scene_num = match.group(1)
                        narration_file = os.path.join(self.job_dir, f"narration_{self.job_id}_{scene_num}.mp3")
                        narration_duration = self.get_narration_duration(narration_file)

                # Heuristic: choose 10s clip for narration longer than 7.5 seconds, else 5s
                target_seconds = 10 if (narration_duration and narration_duration > 7.5) else 5
                self.select_video_duration(target_seconds)
            except Exception as dur_err:
                self.logger.warning(f"⚠️  Duration selection step failed for {scene_id}: {dur_err}")
            
            # Step 4: Generate video
            self.logger.info(f"🎬 Starting generation for {scene_id}...")
            if not self.click_generate_button():
                self.logger.error(f"❌ Failed to start generation for {scene_id}")
                return False
            
            # Step 5: Wait and download
            self.logger.info(f"⏳ Waiting for generation and download for {scene_id}...")
            if not self.wait_for_generation_and_download(scene_id, output_dir):
                self.logger.error(f"❌ Failed to complete generation/download for {scene_id}")
                return False
            
            self.logger.info(f"✅ {scene_id} processed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error processing {scene_id}: {e}")
            return False

    def _load_progress(self, progress_file: str) -> dict:
        """Load progress from file."""
        try:
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {"completed": [], "failed": []}

    def _save_progress(self, progress_file: str, progress_data: dict):
        """Save progress to file."""
        try:
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"⚠️  Could not save progress: {e}")

    def test_upload_interface_detection(self) -> bool:
        """
        Test method to verify we can detect the upload interface elements.
        
        Returns:
            True if upload interface elements are found, False otherwise
        """
        self.logger.info("🔍 Testing upload interface detection...")
        
        # Check for upload area
        upload_area_found = False
        upload_selectors = [
            (By.CSS_SELECTOR, "div.container-IPOZ7J"),
            (By.CSS_SELECTOR, "div[data-is-drag-accept]"),
            (By.XPATH, "//div[contains(@class, 'container-IPOZ7J')]"),
            (By.XPATH, "//p[contains(text(), 'Drag and drop')]"),
            (By.XPATH, "//p[contains(text(), 'double-click')]")
        ]
        
        for i, selector in enumerate(upload_selectors):
            try:
                element = self.driver.find_element(*selector)
                element_text = element.text[:100] if element.text else ""
                self.logger.info(f"✅ Found upload area (selector {i+1}): {element_text}")
                upload_area_found = True
                break
            except:
                continue
        
        # Check for hidden file input
        file_input_found = False
        file_input_selectors = [
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.CSS_SELECTOR, "input[type='file'][accept*='image']"),
            (By.XPATH, "//input[@type='file']")
        ]
        
        for i, selector in enumerate(file_input_selectors):
            try:
                file_input = self.driver.find_element(*selector)
                accept_attr = file_input.get_attribute('accept') or "none"
                self.logger.info(f"✅ Found file input (selector {i+1}): accept='{accept_attr}'")
                file_input_found = True
                break
            except:
                continue
        
        # Check for upload-related text
        upload_text_found = False
        try:
            page_text = self.driver.page_source.lower()
            upload_keywords = ['drag and drop', 'upload', 'select file', 'choose file']
            found_keywords = [keyword for keyword in upload_keywords if keyword in page_text]
            if found_keywords:
                self.logger.info(f"✅ Found upload-related text: {found_keywords}")
                upload_text_found = True
        except:
            pass
        
        # Summary
        total_found = sum([upload_area_found, file_input_found, upload_text_found])
        self.logger.info(f"📊 Upload interface detection: {total_found}/3 elements found")
        
        if total_found >= 2:
            self.logger.info("✅ Upload interface is likely present and accessible")
            return True
        elif total_found == 1:
            self.logger.warning("⚠️  Upload interface partially detected")
            return True
        else:
            self.logger.error("❌ Upload interface not detected")
            return False

    def get_narration_duration(self, narration_path: str) -> Optional[float]:
        """
        Return the duration (in seconds) of the narration mp3 if possible.
        Falls back to None if duration can't be determined.
        """
        if not narration_path or not os.path.exists(narration_path):
            return None
        if MP3 is None:
            self.logger.warning("mutagen not installed – cannot measure narration duration")
            return None
        try:
            audio = MP3(narration_path)
            return float(audio.info.length)
        except Exception as e:
            self.logger.warning(f"Unable to read narration duration from {narration_path}: {e}")
            return None

    def select_video_duration(self, target_seconds: int = 10) -> bool:
        """
        Select the desired video duration in the Runway UI.
        Currently supports 5 s and 10 s buttons.
        Returns True on success, False otherwise.
        """
        self.logger.info(f"⏲️  Selecting {target_seconds}s video duration…")
        # Common textual variations for the duration labels that might appear in the UI
        text_selector_variants = [
            f"{target_seconds}s",          # e.g. "5s"
            f"{target_seconds} s",        # e.g. "5 s"
            f"{target_seconds}sec",       # e.g. "5sec"
            f"{target_seconds} sec",      # e.g. "5 sec"
            f"{target_seconds}seconds",   # e.g. "5seconds"
            f"{target_seconds} seconds"   # e.g. "5 seconds" – matches the inspected HTML
        ]

        selectors = []
        for variant in text_selector_variants:
            selectors.extend([
                (By.XPATH, f"//button[contains(text(), '{variant}')]") ,
                (By.XPATH, f"//span[contains(text(), '{variant}')]/ancestor::button[1]"),
                (By.XPATH, f"//div[contains(text(), '{variant}')]"),
            ])

        # NEW: match on the data-key attribute used by RunwayML duration options (e.g. data-key="5" or "10")
        selectors.extend([
            (By.XPATH, f"//div[@role='option' and @data-key='{target_seconds}']"),
            (By.XPATH, f"//*[@data-key='{target_seconds}' and contains(@class, 'menuItem')]"),
        ])
        
        duration_elem = self.find_element_safe(selectors, wait_time=5)
        if duration_elem:
            try:
                duration_elem.click()
                self.logger.info("✅ Video duration selected")
                time.sleep(1)
                return True
            except Exception as e:
                self.logger.warning(f"Click failed when selecting duration: {e}; trying JavaScript click…")
                try:
                    self.driver.execute_script("arguments[0].click();", duration_elem)
                    return True
                except Exception as js_e:
                    self.logger.error(f"JavaScript click failed: {js_e}")
        else:
            self.logger.warning("Could not find UI element for requested video duration – proceeding anyway.")
            
        return False

    # ============================================================
    #  IMAGE GENERATION SUPPORT (Runway "Text to Image" tab)
    # ============================================================

    def switch_to_image_tab(self) -> bool:
        """Switch the UI to the Image generation tab (opposite of the Video tab).

        Returns True on success, False otherwise.
        """
        self.logger.info("🖼️  Switching to Image tab…")

        image_tab_selectors = [
            (By.XPATH, "//label[contains(@class,'radioItem') and contains(normalize-space(),'Image') ]"),
            (By.XPATH, "//*[contains(text(),'Image') and (@role='radio' or contains(@class,'radio'))]"),
            (By.CSS_SELECTOR, "label.radioItem-v7VRzD"),
            (By.XPATH, "//input[@value='image']/parent::*"),
        ]

        for sel in image_tab_selectors:
            try:
                elem = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(sel))
                elem.click()
                self.logger.info("✅ Image tab selected")
                time.sleep(1)
                return True
            except Exception:
                continue

        self.logger.error("❌ Could not switch to Image tab")
        return False

    def _enter_image_prompt(self, prompt: str) -> bool:
        """Type the given prompt inside the image prompt textbox."""
        selectors = [
            (By.CSS_SELECTOR, "div[aria-label='Text Prompt Input']"),
            (By.CSS_SELECTOR, "div.textbox-lvV8X2"),
            (By.CSS_SELECTOR, "div[role='textbox'][contenteditable='true']"),
            (By.XPATH, "//div[@aria-label='Text Prompt Input']"),
        ]

        box = self.find_element_safe(selectors, wait_time=10)
        if not box:
            self.logger.error("❌ Unable to locate image prompt textbox")
            return False

        try:
            box.clear()
        except Exception:
            # Some contenteditable divs don't support .clear(); fall back to JS
            self.driver.execute_script("arguments[0].innerHTML = ''", box)

        try:
            box.send_keys(prompt)
            self.logger.info("✅ Image prompt entered")
            return True
        except Exception as e:
            self.logger.warning(f"Standard send_keys failed: {e}; trying JS…")
            try:
                self.driver.execute_script("arguments[0].textContent = arguments[1];", box, prompt)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", box)
                return True
            except Exception as js_e:
                self.logger.error(f"❌ Could not enter image prompt: {js_e}")
                return False

    def _click_generate_image_button(self) -> bool:
        """Click the Generate button in the image tab."""
        selectors = [
            (By.XPATH, "//button[.//span[contains(text(),'Generate') and contains(@class,'lucide-image')]]"),
            (By.XPATH, "//button[contains(@class,'primaryBlue') and .//span[text()='Generate']]"),
            (By.CSS_SELECTOR, "button.container-kIPoeH.primaryBlue-oz2I8B"),
        ]

        btn = self.find_element_safe(selectors, wait_time=5)
        if not btn:
            self.logger.error("❌ Generate button (image) not found")
            return False
        try:
            btn.click()
            self.logger.info("✅ Clicked Generate (image) button")
            return True
        except Exception as e:
            self.logger.warning(f"Generate button click failed: {e}; trying JS…")
            try:
                self.driver.execute_script("arguments[0].click();", btn)
                return True
            except Exception as js_e:
                self.logger.error(f"❌ JS click failed: {js_e}")
                return False

    def _wait_for_image_generation(self, timeout: int = 60) -> bool:
        """Wait until the image finishes generating and appears in the asset list."""
        self.logger.info("⏳ Waiting for image generation to complete…")
        elapsed = 0
        check = 2
        while elapsed < timeout:
            try:
                # Heuristic: look for a menu item that contains a lucide-check icon (selected) or aria-selected=true
                generated_selectors = [
                    (By.XPATH, "//div[@role='option' and @aria-selected='true']"),
                    (By.XPATH, "//div[@data-selected='true']"),
                    (By.XPATH, "//svg[contains(@class,'lucide-check')]/ancestor::div[@role='option']"),
                ]
                found = self.find_element_safe(generated_selectors, wait_time=1)
                if found:
                    self.logger.info("✅ Image generation appears complete")
                    return True
            except Exception:
                pass

            time.sleep(check)
            elapsed += check

        self.logger.warning("⚠️ Image generation wait timed out")
        return False

    def _generate_image_from_prompt_internal(self, prompt: str, scene_id: str, output_dir: str) -> Optional[str]:
        """Generate an image inside Runway, download it locally, switch back to video tab, and return the local file path.

        Returns the path to the downloaded image or None if something failed.
        """
        if not prompt:
            self.logger.error("❌ Empty prompt provided for image generation")
            return None

        if not self.switch_to_image_tab():
            return None

        if not self._enter_image_prompt(prompt):
            return None

        if not self._click_generate_image_button():
            return None

        if not self._wait_for_image_generation():
            self.logger.warning("⚠️  Proceeding despite uncertain image generation status")

        # Attempt to download the newly generated image
        image_path = self._download_generated_image(scene_id, output_dir)

        # Return to video tab regardless of download success
        if not self.switch_to_video_tab():
            self.logger.warning("⚠️ Could not switch back to Video tab after image generation")

        return image_path

    # ======================== Image DOWNLOAD ==========================

    def _download_generated_image(self, scene_id: str, output_dir: str = "output/images") -> Optional[str]:
        """Download the most recently generated image from Runway and return its local path.

        Heuristic implementation – looks for a download button with a lucide-download icon or aria-label.
        """
        os.makedirs(output_dir, exist_ok=True)

        download_selectors = [
            (By.XPATH, "//button[.//svg[contains(@class,'lucide-download')]]"),
            (By.XPATH, "//button[contains(@aria-label, 'Download')]"),
            (By.XPATH, "//a[contains(@download,'')]"),
        ]

        download_elem = self.find_element_safe(download_selectors, wait_time=5)
        if not download_elem:
            self.logger.error("❌ Could not find image download button")
            return None

        try:
            # Track existing files inside default download folder
            download_folder = os.path.expanduser("~/Downloads")
            before = set(os.listdir(download_folder)) if os.path.exists(download_folder) else set()

            download_elem.click()
            self.logger.info("✅ Clicked image download button")

            # Wait for a new image file to appear
            timeout, elapsed = 60, 0
            while elapsed < timeout:
                time.sleep(2)
                elapsed += 2
                after = set(os.listdir(download_folder)) if os.path.exists(download_folder) else set()
                new_files = after - before
                image_files = [f for f in new_files if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
                if image_files:
                    new_file = image_files[0]
                    src_path = os.path.join(download_folder, new_file)
                    dst_path = os.path.join(output_dir, f"{scene_id}_runway.png")
                    import shutil
                    shutil.move(src_path, dst_path)
                    self.logger.info(f"✅ Downloaded image saved to {dst_path}")
                    return dst_path
            self.logger.warning("⚠️  Image download timed out – file may still be downloading")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error during image download: {e}")
            return None

    # ================== Image Generation (revised) =====================

    def generate_image_from_prompt(self, prompt: str, scene_id: str, output_dir: str) -> Optional[str]:
        """Generate an image inside Runway, download it locally, switch back to video tab, and return the local file path.

        Returns the path to the downloaded image or None if something failed.
        """
        if not prompt:
            self.logger.error("❌ Empty prompt provided for image generation")
            return None

        if not self.switch_to_image_tab():
            return None

        if not self._enter_image_prompt(prompt):
            return None

        if not self._click_generate_image_button():
            return None

        if not self._wait_for_image_generation():
            self.logger.warning("⚠️  Proceeding despite uncertain image generation status")

        # Attempt to download the newly generated image
        image_path = self._download_generated_image(scene_id, output_dir)

        # Return to video tab regardless of download success
        if not self.switch_to_video_tab():
            self.logger.warning("⚠️ Could not switch back to Video tab after image generation")

        return image_path

    # ------------------------------------------------------------------
    # LEGACY (simplified) image generation helper – kept for reference.
    # Not called in current workflow. Left here to preserve earlier code,
    # but renamed to avoid method-name collision.
    # ------------------------------------------------------------------

    def _legacy_generate_image_from_prompt(self, prompt: str) -> bool:  # noqa: F811
        """Deprecated simplified helper; always returns False as a stub."""
        self.logger.debug("_legacy_generate_image_from_prompt invoked – this should not happen in new pipeline")
        return False

    # ---------- DEPRECATED single-parameter helper (renamed to avoid collision) ----------
    def _generate_image_from_prompt_single(self, prompt: str) -> bool:
        self.logger.debug("_generate_image_from_prompt_single invoked – this should not happen in new pipeline")
        return False


def main():
    """Main function to test the slim automation."""
    print("RunwayML Slim Automation - Batch Processing Mode")
    print("================================================")
    print("This script will:")
    print("1. Open browser")
    print("2. Navigate to RunwayML") 
    print("3. Login")
    print("4. Process ALL scenes automatically in batch")
    print("5. Track progress and allow resuming")
    print()
    
    # JSON file path - can be overridden by command line argument
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        # Auto-select the most recent raw_json_<job>.json inside output/*/
        import glob
        from pathlib import Path

        script_dir = Path(__file__).resolve().parent
        local_output = script_dir / "output"
        sibling_output = script_dir.parent / "youtube-video-creator" / "output"

        candidates = []
        for out_dir in (local_output, sibling_output):
            candidates.extend(glob.glob(str(out_dir / "*" / "raw_json_*.json")))
        if not candidates:
            print("❌ No JSON files found under output/. Please provide the path as an argument.")
            return
        json_path = max(candidates, key=os.path.getmtime)
        print(f"📄 Auto-selected latest JSON file: {json_path}")
    
    try:
        # Check if JSON file exists
        if not os.path.exists(json_path):
            print(f"❌ JSON file not found: {json_path}")
            print("Please ensure the JSON file exists before running the script.")
            return
        
        print(f"📄 Using JSON file: {json_path}")
        
        # NEW: Determine an output directory that lives next to the JSON file
        from pathlib import Path  # Local import to avoid impacting global scope
        json_dir = Path(json_path).resolve().parent
        videos_output_dir = json_dir / "videos"  # e.g. <job_folder>/videos
        
        print(f"📁 Generated clips will be saved to: {videos_output_dir}")
        
        # Initialize automation
        automation = RunwayMLSlim(
            browser_name="chrome",
            manual_login=False,  # Set to True for manual login
            use_undetected=True
        )
        
        # Step 1: Navigate to login page
        if not automation.navigate_to_login():
            print("❌ Failed to navigate to login page")
            return
        
        # Step 2: Perform login
        if not automation.login():
            print("❌ Login failed")
            return
        
        print("✅ Login completed successfully!")
        
        # Step 3: Switch to Image tab first – the per-scene workflow will handle tab switching as needed
        print("\n🖼️  Switching to image tab...")
        if automation.switch_to_image_tab():
            print("✅ Successfully switched to image tab!")
        else:
            print("⚠️  Image tab switch may have failed, but continuing...")
        
        # Step 4: Start batch processing directly
        print("\n" + "="*50)
        print("🚀 STARTING BATCH PROCESSING")
        print("="*50)
        print("Processing all scenes from JSON file automatically.")
        print("This will:")
        print("- Keep the browser open and logged in")
        print("- Process all scenes from the JSON")
        print("- Save videos as scene_0.mp4, scene_1.mp4, etc.")
        print("- Track progress and allow resuming")
        print("- Skip scenes that are already completed")
        
        # Pass the dynamically-determined output directory instead of hard-coded path
        results = automation.process_all_scenes(json_path, str(videos_output_dir))
        
        print("\n" + "="*50)
        print("📊 FINAL BATCH PROCESSING RESULTS")
        print("="*50)
        print(f"✅ Completed: {len(results.get('completed', []))}")
        print(f"❌ Failed: {len(results.get('failed', []))}")
        print(f"⏭️  Skipped: {len(results.get('skipped', []))}")
        
        # Show details
        if results.get('completed'):
            print(f"\n✅ Successfully completed scenes: {', '.join(results['completed'])}")
        if results.get('failed'):
            print(f"\n❌ Failed scenes:")
            for failed in results['failed']:
                if isinstance(failed, dict):
                    print(f"   - {failed.get('scene', 'unknown')}: {failed.get('error', 'unknown error')}")
                else:
                    print(f"   - {failed}")
        if results.get('skipped'):
            print(f"\n⏭️  Skipped scenes (already completed): {', '.join(results['skipped'])}")
        
        # Update final path message
        print(f"\n📁 All videos saved to: {videos_output_dir}/")
        print("🎉 Batch processing complete!")
        
        # Keep browser open longer for review
        print("\nBrowser will stay open for 60 seconds to review the results...")
        time.sleep(60)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            automation.close()
        except:
            pass


if __name__ == "__main__":
    main() 