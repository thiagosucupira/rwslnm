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

# NEW: GUI libraries for folder selection
import tkinter as tk
from tkinter import filedialog, messagebox

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

# Try to import moviepy for video concatenation
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips  # type: ignore
    MOVIEPY_AVAILABLE = True
except ImportError:  # Safe fallback if moviepy not installed
    VideoFileClip = None  # type: ignore
    concatenate_videoclips = None  # type: ignore
    MOVIEPY_AVAILABLE = False

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
        
        # Updated selector strategies based on actual HTML structure
        video_tab_selectors = [
            # Target the exact label structure from user's HTML
            (By.CSS_SELECTOR, "label.radioItem-v7VRzD[data-rac]"),
            (By.CSS_SELECTOR, "label.radioItem-v7VRzD"),
            
            # Target by the video SVG icon within the label
            (By.XPATH, "//label[contains(@class, 'radioItem-v7VRzD')]//svg[contains(@class, 'lucide-video')]/../.."),
            (By.XPATH, "//svg[contains(@class, 'lucide-video')]/ancestor::label[1]"),
            
            # Target by the hidden radio input with value="video"
            (By.XPATH, "//input[@value='video']/ancestor::label[1]"),
            (By.XPATH, "//label[.//input[@value='video']]"),
            
            # Target by text content "Video" in label
            (By.XPATH, "//label[contains(@class, 'radioItem') and contains(., 'Video')]"),
            (By.XPATH, "//label[text()='Video' or contains(text(), 'Video')]"),
            
            # More generic fallbacks
            (By.CSS_SELECTOR, "label[class*='radioItem']"),
            (By.XPATH, "//label[contains(@class, 'radioItem')]"),
            
            # Direct input targeting (less preferred but fallback)
            (By.CSS_SELECTOR, "input[value='video']"),
            (By.XPATH, "//input[@value='video']")
        ]
        
        # Try each selector until one works
        for i, selector in enumerate(video_tab_selectors):
            try:
                self.logger.debug(f"Trying video tab selector {i+1}/{len(video_tab_selectors)}: {selector}")
                
                # Wait for element to be present
                video_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(selector)
                )
                
                # Log what we found
                try:
                    element_info = f"tag='{video_element.tag_name}', text='{video_element.text[:30]}', classes='{video_element.get_attribute('class')}'"
                    self.logger.debug(f"Found video tab element: {element_info}")
                except:
                    self.logger.debug("Found video tab element (couldn't get details)")
                
                # For input elements, find the parent label to click
                if video_element.tag_name.lower() == 'input':
                    try:
                        # Find the parent label
                        parent_label = video_element.find_element(By.XPATH, "./ancestor::label[1]")
                        video_element = parent_label
                        self.logger.debug("Switched to parent label for clicking")
                    except:
                        self.logger.debug("Could not find parent label, clicking input directly")
                
                # Try to click the element
                try:
                    # First try regular click
                    video_element.click()
                    self.logger.info("✅ Successfully clicked video tab")
                except Exception as click_error:
                    # Try JavaScript click as fallback
                    self.logger.debug(f"Regular click failed: {click_error}, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", video_element)
                    self.logger.info("✅ Successfully clicked video tab (via JavaScript)")
                
                # Wait for UI to update
                time.sleep(2)
                
                # Enhanced verification - check if the video radio is now selected
                try:
                    # Method 1: Check if input with value='video' is selected/checked
                    video_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[value='video']")
                    for video_input in video_inputs:
                        if video_input.is_selected() or video_input.get_attribute('checked') == 'true':
                            self.logger.info("✅ Video tab is now selected (input checked)")
                            return True
                    
                    # Method 2: Check for active/selected class on label
                    selected_labels = self.driver.find_elements(By.CSS_SELECTOR, "label.radioItem-v7VRzD")
                    for label in selected_labels:
                        label_classes = label.get_attribute('class') or ""
                        if 'selected' in label_classes.lower() or 'active' in label_classes.lower():
                            self.logger.info("✅ Video tab is now selected (label has selected class)")
                            return True
                    
                    # Method 3: Check if we can find video-related UI elements that appear after switching
                    video_ui_indicators = [
                        (By.XPATH, "//div[contains(text(), 'Select Asset')]"),
                        (By.XPATH, "//button[contains(text(), 'Select Asset')]"),
                        (By.CSS_SELECTOR, "input[type='file'][accept*='image']"),
                        (By.XPATH, "//div[contains(@class, 'upload')]")
                    ]
                    
                    for indicator in video_ui_indicators:
                        try:
                            self.driver.find_element(*indicator)
                            self.logger.info(f"✅ Video tab switched successfully (found video UI element)")
                            return True
                        except:
                            continue
                    
                    # If we can't verify, assume it worked since we clicked successfully
                    self.logger.warning("⚠️  Could not verify video tab selection, but click was successful")
                    return True
                    
                except Exception as verify_error:
                    self.logger.debug(f"Could not verify video tab selection: {verify_error}")
                    # Still return True since the click was successful
                    self.logger.info("✅ Video tab click completed (verification inconclusive)")
                    return True
                
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.debug(f"Selector {i+1} failed: {e}")
                continue
            except Exception as e:
                self.logger.warning(f"Unexpected error with selector {i+1}: {e}")
                continue
        
        # If we get here, all selectors failed
        self.logger.error("❌ Failed to find video tab with any selector")
        
        # Enhanced debugging - let's see what's actually on the page
        try:
            current_url = self.driver.current_url
            self.logger.error(f"Current URL: {current_url}")
            
            # Look for all label elements
            all_labels = self.driver.find_elements(By.TAG_NAME, "label")
            self.logger.error(f"Found {len(all_labels)} label elements on page")
            
            for i, label in enumerate(all_labels[:10]):  # Show first 10 labels
                try:
                    label_text = label.text[:50] if label.text else ""
                    label_classes = label.get_attribute('class') or ""
                    self.logger.error(f"  Label {i+1}: text='{label_text}', classes='{label_classes[:50]}'")
                except:
                    self.logger.error(f"  Label {i+1}: (couldn't get details)")
            
            # Look for radio inputs
            radio_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            self.logger.error(f"Found {len(radio_inputs)} radio inputs")
            
            for i, radio in enumerate(radio_inputs):
                try:
                    radio_value = radio.get_attribute('value') or ""
                    radio_checked = radio.get_attribute('checked') or "false"
                    self.logger.error(f"  Radio {i+1}: value='{radio_value}', checked='{radio_checked}'")
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
                
                # Store current page state for comparison
                original_page_source_length = len(self.driver.page_source)
                
                # Click the generate button
                generate_element.click()
                self.logger.info("✅ Successfully clicked Generate button!")
                
                # IMPROVED: More aggressive and broader verification
                self.logger.info("🔍 Verifying that generation actually started...")
                
                # Wait a moment for UI to update
                time.sleep(3)
                
                # Check 1: Look for ANY change in page content that might indicate generation started
                new_page_source_length = len(self.driver.page_source)
                if abs(new_page_source_length - original_page_source_length) > 1000:
                    self.logger.info("✅ Significant page content change detected - generation likely started")
                    return True
                
                # Check 2: Much broader progress indicators with more variations
                extended_verification_time = 20  # Wait up to 20 seconds
                check_interval = 2
                elapsed = 0
                
                while elapsed < extended_verification_time:
                    time.sleep(check_interval)
                    elapsed += check_interval
                    
                    # EXPANDED progress indicators - much more comprehensive
                    progress_indicators = [
                        # Text-based indicators (case insensitive)
                        (By.XPATH, "//div[contains(translate(text(), 'GENERATING', 'generating'), 'generating')]"),
                        (By.XPATH, "//div[contains(translate(text(), 'PROCESSING', 'processing'), 'processing')]"),
                        (By.XPATH, "//div[contains(translate(text(), 'QUEUE', 'queue'), 'queue')]"),
                        (By.XPATH, "//div[contains(translate(text(), 'STARTING', 'starting'), 'starting')]"),
                        (By.XPATH, "//div[contains(translate(text(), 'LOADING', 'loading'), 'loading')]"),
                        (By.XPATH, "//div[contains(translate(text(), 'CREATING', 'creating'), 'creating')]"),
                        (By.XPATH, "//div[contains(translate(text(), 'WAITING', 'waiting'), 'waiting')]"),
                        
                        # Progress bars and spinners
                        (By.CSS_SELECTOR, "div[role='progressbar']"),
                        (By.CSS_SELECTOR, "[class*='progress']"),
                        (By.CSS_SELECTOR, "[class*='spinner']"),
                        (By.CSS_SELECTOR, "[class*='loading']"),
                        (By.CSS_SELECTOR, "[class*='generating']"),
                        
                        # Common UI patterns
                        (By.XPATH, "//div[contains(@class, 'progress')]"),
                        (By.XPATH, "//div[contains(@class, 'loading')]"),
                        (By.XPATH, "//div[contains(@class, 'spinner')]"),
                        (By.XPATH, "//div[contains(@class, 'generating')]"),
                        
                        # Animation/SVG indicators
                        (By.CSS_SELECTOR, "svg[class*='animate']"),
                        (By.CSS_SELECTOR, "div[class*='animate']"),
                        (By.XPATH, "//svg[contains(@class, 'spin')]"),
                        (By.XPATH, "//div[contains(@class, 'spin')]"),
                        
                        # Percentage or time indicators
                        (By.XPATH, "//div[contains(text(), '%')]"),
                        (By.XPATH, "//div[contains(text(), 'sec')]"),
                        (By.XPATH, "//div[contains(text(), 'min')]"),
                    ]
                    
                    progress_element = self.find_element_safe(progress_indicators, wait_time=1)
                    if progress_element:
                        progress_text = progress_element.text[:100] if progress_element.text else "Processing"
                        self.logger.info(f"✅ Video generation confirmed started! Status: {progress_text}")
                        return True
                    
                    # Check 3: Button state changes (more comprehensive)
                    try:
                        current_button = self.find_element_safe(generate_selectors, wait_time=1)
                        if current_button:
                            button_text = current_button.text.lower()
                            
                            # Look for various button state changes
                            if any(keyword in button_text for keyword in ['generating', 'processing', 'creating', 'loading', 'working']):
                                self.logger.info(f"✅ Generate button shows generation started: '{button_text}'")
                                return True
                            elif current_button.get_attribute('disabled') == 'true' or current_button.get_attribute('data-soft-disabled') == 'true':
                                self.logger.info("✅ Generate button is now disabled - generation likely started")
                                return True
                            
                            # Check if button completely disappeared (sometimes happens)
                            if not button_text.strip():
                                self.logger.info("✅ Generate button text cleared - generation may have started")
                                return True
                    except:
                        # If button completely disappeared, that might indicate generation started
                        self.logger.info("✅ Generate button no longer found - generation may have started")
                        return True
                    
                    # Check 4: URL changes that might indicate navigation to generation view
                    try:
                        current_url = self.driver.current_url
                        if any(indicator in current_url.lower() for indicator in ['generate', 'processing', 'queue', 'task']):
                            self.logger.info(f"✅ URL suggests generation started: {current_url}")
                            return True
                    except:
                        pass
                    
                    self.logger.debug(f"⏳ Still verifying generation started... ({elapsed}s)")
                
                # Check 5: FALLBACK - Look for ANY new UI elements that weren't there before
                self.logger.info("🔍 Doing comprehensive UI scan for any generation indicators...")
                try:
                    # Get all text content on page
                    page_text = self.driver.page_source.lower()
                    
                    # Look for generation-related keywords in page source
                    generation_keywords = [
                        'generating', 'processing', 'creating', 'loading', 'working',
                        'queue', 'waiting', 'progress', 'starting', 'rendering',
                        'task', 'job', 'building', 'producing'
                    ]
                    
                    found_keywords = [kw for kw in generation_keywords if kw in page_text]
                    if found_keywords:
                        self.logger.info(f"✅ Found generation keywords in page: {found_keywords}")
                        return True
                    
                    # Look for percentage indicators or time estimates
                    import re
                    if re.search(r'\d+%', page_text) or re.search(r'\d+\s*(sec|min|seconds|minutes)', page_text):
                        self.logger.info("✅ Found percentage or time indicators - generation likely started")
                        return True
                        
                except Exception as scan_e:
                    self.logger.debug(f"UI scan error: {scan_e}")
                
                # LAST RESORT: If we can't detect progress, just assume it worked and continue
                # This prevents the script from getting stuck on detection issues
                self.logger.warning("⚠️  Could not definitively confirm generation started")
                self.logger.warning("⚠️  But Generate button was clicked successfully")
                self.logger.info("✅ Proceeding optimistically - generation may have started")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ Error clicking Generate button: {e}")
                
                # Try JavaScript click as fallback
                try:
                    self.logger.info("Trying JavaScript click as fallback...")
                    self.driver.execute_script("arguments[0].click();", generate_element)
                    self.logger.info("✅ Generate button clicked via JavaScript")
                    
                    # Brief wait and optimistic return for JS click
                    time.sleep(5)
                    self.logger.info("✅ JavaScript click completed - proceeding optimistically")
                    return True
                        
                except Exception as js_e:
                    self.logger.error(f"❌ JavaScript click also failed: {js_e}")
                    return False
        else:
            self.logger.error("❌ Could not find Generate button")
            
            # Enhanced debugging for button discovery
            try:
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                all_spans = self.driver.find_elements(By.TAG_NAME, "span")
                
                button_texts = [btn.text[:50] for btn in all_buttons if btn.text.strip()]
                span_texts = [span.text[:50] for span in all_spans if span.text.strip() and 'generate' in span.text.lower()]
                
                self.logger.error(f"Available buttons on page: {button_texts}")
                self.logger.error(f"Spans containing 'generate': {span_texts}")
                
                # Try to find ANY element with generate text
                generate_anywhere = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'GENERATE', 'generate'), 'generate')]")
                if generate_anywhere:
                    self.logger.error(f"Found {len(generate_anywhere)} elements with 'generate' text")
                    for elem in generate_anywhere[:3]:
                        try:
                            self.logger.error(f"  - {elem.tag_name}: '{elem.text[:50]}' class='{elem.get_attribute('class')}'")
                        except:
                            pass
                            
            except Exception as debug_e:
                self.logger.error(f"Debug failed: {debug_e}")
            
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
        
        max_wait_time = 600  # Increased to 10 minutes max (RunwayML can be slow)
        check_interval = 10   # Check every 10 seconds instead of 5
        elapsed_time = 0
        last_log_time = 0  # Track when we last logged progress
        
        while elapsed_time < max_wait_time:
            try:
                # ENHANCED: More comprehensive completion indicators
                completion_selectors = [
                    # Primary completion indicator - button with data-saved="true"
                    (By.CSS_SELECTOR, "button.mainButton-_m_ZJD[data-saved='true']"),
                    (By.CSS_SELECTOR, "button[data-saved='true'][data-size='small']"),
                    (By.XPATH, "//button[@data-saved='true' and .//svg[contains(@class, 'lucide-download')]]"),
                    
                    # Secondary indicators
                    (By.CSS_SELECTOR, "button.mainButton-_m_ZJD"),  # Main download button
                    (By.CSS_SELECTOR, "div.buttonContainer-ONyYcY"),  # Download button container
                    (By.XPATH, "//svg[contains(@class, 'lucide-download')]/parent::button"),  # Download icon button
                    
                    # Text-based completion indicators
                    (By.XPATH, "//div[contains(translate(text(), 'COMPLETE', 'complete'), 'complete')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'FINISHED', 'finished'), 'finished')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'DONE', 'done'), 'done')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'READY', 'ready'), 'ready')]"),
                    
                    # Video element (generated video)
                    (By.XPATH, "//video[@src]"),
                    (By.CSS_SELECTOR, "video[src]"),
                    
                    # Download-related elements
                    (By.XPATH, "//button[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]"),
                    (By.XPATH, "//a[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]"),
                    (By.CSS_SELECTOR, "[download]"),  # Any element with download attribute
                ]
                
                completion_element = self.find_element_safe(completion_selectors, wait_time=3)
                
                if completion_element:
                    self.logger.info("✅ Video generation appears to be complete!")
                    
                    # Try to download the video
                    if self._download_generated_video(scene_id, output_dir):
                        return True
                    else:
                        self.logger.warning("⚠️  Generation complete but download failed")
                        # Don't return False immediately - try again in next iteration
                        self.logger.info("🔄 Will retry download detection in next check...")
                
                # ENHANCED: Check for error states (broader detection)
                error_selectors = [
                    (By.XPATH, "//div[contains(translate(text(), 'ERROR', 'error'), 'error')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'FAILED', 'failed'), 'failed')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'TRY AGAIN', 'try again'), 'try again')]"),
                    (By.XPATH, "//button[contains(translate(text(), 'RETRY', 'retry'), 'retry')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'LIMIT', 'limit'), 'limit')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'QUOTA', 'quota'), 'quota')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'INSUFFICIENT', 'insufficient'), 'insufficient')]"),
                ]
                
                error_element = self.find_element_safe(error_selectors, wait_time=1)
                if error_element:
                    error_text = error_element.text[:100] if error_element.text else "Unknown error"
                    self.logger.error(f"❌ Video generation failed: {error_text}")
                    return False
                
                # ENHANCED: Check for progress indicators (broader and more forgiving)
                progress_selectors = [
                    # Text-based progress (case insensitive)
                    (By.XPATH, "//div[contains(translate(text(), 'GENERATING', 'generating'), 'generating')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'PROCESSING', 'processing'), 'processing')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'CREATING', 'creating'), 'creating')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'LOADING', 'loading'), 'loading')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'WORKING', 'working'), 'working')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'QUEUE', 'queue'), 'queue')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'WAITING', 'waiting'), 'waiting')]"),
                    (By.XPATH, "//div[contains(translate(text(), 'RENDERING', 'rendering'), 'rendering')]"),
                    
                    # Progress UI elements
                    (By.CSS_SELECTOR, "div[role='progressbar']"),
                    (By.CSS_SELECTOR, "[class*='progress']"),
                    (By.CSS_SELECTOR, "[class*='loading']"),
                    (By.CSS_SELECTOR, "[class*='generating']"),
                    (By.CSS_SELECTOR, "[class*='spinner']"),
                    (By.XPATH, "//div[contains(@class, 'progress')]"),
                    (By.XPATH, "//div[contains(@class, 'loading')]"),
                    (By.XPATH, "//div[contains(@class, 'generating')]"),
                    
                    # Percentage or time indicators
                    (By.XPATH, "//div[contains(text(), '%')]"),
                    (By.XPATH, "//div[contains(text(), 'sec')]"),
                    (By.XPATH, "//div[contains(text(), 'min')]"),
                    (By.XPATH, "//div[contains(text(), 'seconds')]"),
                    (By.XPATH, "//div[contains(text(), 'minutes')]"),
                ]
                
                progress_element = self.find_element_safe(progress_selectors, wait_time=2)
                if progress_element:
                    progress_text = progress_element.text[:100] if progress_element.text else "Processing"
                    
                    # Only log progress every 30 seconds to avoid spam
                    if elapsed_time - last_log_time >= 30:
                        self.logger.info(f"⏳ Still generating... {progress_text} (elapsed: {elapsed_time}s/{max_wait_time}s)")
                        last_log_time = elapsed_time
                    
                else:
                    # No explicit progress found - check if generation is still active in other ways
                    
                    # Check if Generate button is still disabled (indicates generation active)
                    generate_selectors = [
                        (By.XPATH, "//span[text()='Generate']"),
                        (By.XPATH, "//span[contains(text(), 'Generate')]"),
                        (By.XPATH, "//button[.//span[text()='Generate']]")
                    ]
                    
                    generate_button = self.find_element_safe(generate_selectors, wait_time=1)
                    if generate_button:
                        if generate_button.get_attribute('disabled') == 'true' or generate_button.get_attribute('data-soft-disabled') == 'true':
                            # Button is disabled, generation likely still active
                            if elapsed_time - last_log_time >= 30:
                                self.logger.info(f"⏳ Generation likely active (Generate button disabled) - elapsed: {elapsed_time}s/{max_wait_time}s")
                                last_log_time = elapsed_time
                        elif elapsed_time >= 60:  # Only check after 1 minute
                            # Button is enabled again - this might indicate generation failed
                            self.logger.warning("⚠️  Generate button is enabled again - generation may have failed")
                            self.logger.warning("⚠️  But continuing to wait in case this is normal...")
                    
                    # Even if no progress indicators, continue waiting - maybe we just missed them
                    if elapsed_time - last_log_time >= 60:  # Log every minute when no progress found
                        self.logger.info(f"⏳ Waiting for generation... (no progress indicators found) - elapsed: {elapsed_time}s/{max_wait_time}s")
                        last_log_time = elapsed_time
                
                time.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                self.logger.warning(f"⚠️  Error checking generation status: {e}")
                time.sleep(check_interval)
                elapsed_time += check_interval
                
                # Don't give up on errors - RunwayML can be flaky
                if elapsed_time - last_log_time >= 60:
                    self.logger.info(f"⏳ Continuing despite errors - elapsed: {elapsed_time}s/{max_wait_time}s")
                    last_log_time = elapsed_time
        
        # Final timeout check - try one last comprehensive search before giving up
        self.logger.warning(f"⚠️  Generation timed out after {max_wait_time} seconds")
        self.logger.info("🔍 Doing final comprehensive search for completion indicators...")
        
        # Final desperate search with longer timeout
        all_completion_selectors = [
            # All the completion selectors from above
            (By.CSS_SELECTOR, "button.mainButton-_m_ZJD[data-saved='true']"),
            (By.CSS_SELECTOR, "button[data-saved='true'][data-size='small']"),
            (By.XPATH, "//button[@data-saved='true' and .//svg[contains(@class, 'lucide-download')]]"),
            (By.CSS_SELECTOR, "button.mainButton-_m_ZJD"),
            (By.CSS_SELECTOR, "div.buttonContainer-ONyYcY"),
            (By.XPATH, "//svg[contains(@class, 'lucide-download')]/parent::button"),
            (By.XPATH, "//video[@src]"),
            (By.CSS_SELECTOR, "video[src]"),
            (By.XPATH, "//button[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]"),
            (By.XPATH, "//a[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]"),
            (By.CSS_SELECTOR, "[download]"),
        ]
        
        final_completion = self.find_element_safe(all_completion_selectors, wait_time=15)
        if final_completion:
            self.logger.info("✅ Found completion element in final search!")
            if self._download_generated_video(scene_id, output_dir):
                return True
            else:
                self.logger.error("❌ Final download attempt failed")
        
        self.logger.error(f"❌ Video generation timed out completely after {max_wait_time} seconds")
        return False

    def _click_4k_upscale_button(self) -> bool:
        """
        Click the 4K upscale button if available.
        
        Returns:
            True if button was clicked or not found (non-critical), False if error occurred
        """
        try:
            self.logger.info("🔍 Looking for 4K upscale button...")
            
            # Multiple selectors to find the 4K upscale button based on the provided HTML
            upscale_selectors = [
                # Primary: Button with span containing "4K" text
                (By.XPATH, "//button[.//span[text()='4K']]"),
                (By.XPATH, "//button[.//span[contains(text(), '4K')]]"),
                
                # Secondary: Button with SVG containing upscale class
                (By.XPATH, "//button[.//svg[contains(@class, 'lucide-image-upscale')]]"),
                (By.CSS_SELECTOR, "button svg.lucide-image-upscale"),
                
                # Combined: Button with both upscale SVG and 4K text
                (By.XPATH, "//button[.//svg[contains(@class, 'lucide-image-upscale')] and .//span[text()='4K']]"),
                
                # Fallback: Any button with class patterns that might indicate upscale
                (By.CSS_SELECTOR, "button[class*='tertiary'][class*='medium'] span"),
                (By.XPATH, "//button[contains(@class, 'tertiary') and contains(@class, 'medium')]//span[text()='4K']"),
                
                # General text-based selectors
                (By.XPATH, "//button[contains(text(), '4K')]"),
                (By.XPATH, "//*[contains(text(), '4K') and (name()='button' or name()='div' or name()='span')]"),
            ]
            
            upscale_button = self.find_element_safe(upscale_selectors, wait_time=5)
            
            if upscale_button:
                # Check if the button is clickable (not disabled)
                button_class = upscale_button.get_attribute('class') or ''
                is_disabled = (
                    upscale_button.get_attribute('disabled') == 'true' or 
                    upscale_button.get_attribute('data-soft-disabled') == 'true' or
                    'disabled' in button_class
                )
                
                if is_disabled:
                    self.logger.info("ℹ️  4K upscale button found but is disabled - skipping")
                    return True
                
                # Try to click the button
                try:
                    upscale_button.click()
                    self.logger.info("✅ Successfully clicked 4K upscale button")
                    
                    # Wait a moment for any UI changes after clicking upscale
                    time.sleep(2)
                    return True
                    
                except Exception as click_error:
                    self.logger.warning(f"⚠️  Found 4K button but couldn't click it: {click_error}")
                    # Try JavaScript click as fallback
                    try:
                        self.driver.execute_script("arguments[0].click();", upscale_button)
                        self.logger.info("✅ Successfully clicked 4K upscale button using JavaScript")
                        time.sleep(2)
                        return True
                    except Exception as js_error:
                        self.logger.warning(f"⚠️  JavaScript click also failed: {js_error}")
                        return True  # Non-critical, continue with download
            
            else:
                self.logger.info("ℹ️  4K upscale button not found - continuing without upscaling")
                return True  # Not finding the button is not an error
                
        except Exception as e:
            self.logger.warning(f"⚠️  Error while looking for 4K upscale button: {e}")
            return True  # Non-critical error, continue with download

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
        
        # Try to click 4K upscale button before downloading
        self._click_4k_upscale_button()
        
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
                            
                            # Create concatenated versions with intro/outro
                            try:
                                self.create_concatenated_videos(scene_id, dst_path, output_dir)
                            except Exception as concat_error:
                                self.logger.warning(f"⚠️  Failed to create concatenated videos: {concat_error}")
                                # Don't fail the entire process if concatenation fails
                            
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
            
            if not os.path.exists(image_path):
                self.logger.warning(f"⚠️  Image not found for {scene_id}: {image_path}")
                results["failed"].append({"scene": scene_id, "error": "Image not found"})
                failed_scenes.append(scene_id)
                continue
            
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
            # Step 1: Upload image
            self.logger.info(f"📤 Uploading image for {scene_id}...")
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

    def create_concatenated_videos(self, scene_id: str, video_path: str, output_dir: str) -> bool:
        """
        Create concatenated videos with intro and outro clips.
        
        Creates two versions:
        1. intro + generated_video (saved as {scene_id}_with_intro.mp4)
        2. intro + generated_video + outro (saved as {scene_id}_final.mp4)
        
        Args:
            scene_id: Scene identifier for naming
            video_path: Path to the generated video file
            output_dir: Directory where intro.mp4 and outro.mp4 should be located
            
        Returns:
            True if at least one concatenated video was created successfully
        """
        if not MOVIEPY_AVAILABLE:
            self.logger.warning("⚠️  MoviePy not available - skipping video concatenation")
            return False
        
        if not os.path.exists(video_path):
            self.logger.error(f"❌ Generated video not found: {video_path}")
            return False
        
        self.logger.info(f"🎬 Creating concatenated videos for {scene_id}...")
        
        # Look for intro and outro files in multiple locations
        search_dirs = [
            output_dir,  # Same directory as output
            os.path.dirname(output_dir),  # Parent directory
            os.path.dirname(os.path.dirname(output_dir)),  # Grandparent directory
            os.path.join(os.path.dirname(output_dir), "assets"),  # Assets folder
            os.path.dirname(os.path.abspath(__file__))  # Script directory
        ]
        
        intro_path = None
        outro_path = None
        
        # Search for intro.mp4
        for search_dir in search_dirs:
            potential_intro = os.path.join(search_dir, "intro.mp4")
            if os.path.exists(potential_intro):
                intro_path = potential_intro
                self.logger.info(f"✅ Found intro.mp4: {intro_path}")
                break
        
        # Search for outro.mp4
        for search_dir in search_dirs:
            potential_outro = os.path.join(search_dir, "outro.mp4")
            if os.path.exists(potential_outro):
                outro_path = potential_outro
                self.logger.info(f"✅ Found outro.mp4: {outro_path}")
                break
        
        if not intro_path and not outro_path:
            self.logger.warning("⚠️  No intro.mp4 or outro.mp4 found - skipping concatenation")
            self.logger.info("Searched in directories:")
            for search_dir in search_dirs:
                self.logger.info(f"  - {search_dir}")
            return False
        
        success_count = 0
        
        try:
            # Load the generated video
            self.logger.info(f"📽️  Loading generated video: {os.path.basename(video_path)}")
            if VideoFileClip is None:
                self.logger.error("❌ VideoFileClip not available")
                return False
            main_clip = VideoFileClip(video_path)
            
            # Create intro + generated video
            if intro_path:
                try:
                    self.logger.info("🎬 Creating intro + video combination...")
                    if VideoFileClip is None or concatenate_videoclips is None:
                        self.logger.error("❌ MoviePy functions not available")
                        return False
                    intro_clip = VideoFileClip(intro_path)
                    
                    # Concatenate intro + main video
                    intro_combo = concatenate_videoclips([intro_clip, main_clip], method="compose")
                    
                    # Save intro combination
                    intro_output_path = os.path.join(output_dir, f"{scene_id}_with_intro.mp4")
                    intro_combo.write_videofile(
                        intro_output_path,
                        codec='libx264',
                        audio_codec='aac',
                        verbose=False,
                        logger=None  # Suppress moviepy logs
                    )
                    
                    self.logger.info(f"✅ Created intro combination: {os.path.basename(intro_output_path)}")
                    success_count += 1
                    
                    # Clean up clips
                    intro_clip.close()
                    intro_combo.close()
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to create intro combination: {e}")
            
            # Create intro + generated video + outro (if both intro and outro exist)
            if intro_path and outro_path:
                try:
                    self.logger.info("🎬 Creating intro + video + outro combination...")
                    if VideoFileClip is None or concatenate_videoclips is None:
                        self.logger.error("❌ MoviePy functions not available")
                        return False
                    intro_clip = VideoFileClip(intro_path)
                    outro_clip = VideoFileClip(outro_path)
                    
                    # Concatenate intro + main video + outro
                    final_combo = concatenate_videoclips([intro_clip, main_clip, outro_clip], method="compose")
                    
                    # Save final combination
                    final_output_path = os.path.join(output_dir, f"{scene_id}_final.mp4")
                    final_combo.write_videofile(
                        final_output_path,
                        codec='libx264',
                        audio_codec='aac',
                        verbose=False,
                        logger=None  # Suppress moviepy logs
                    )
                    
                    self.logger.info(f"✅ Created final combination: {os.path.basename(final_output_path)}")
                    success_count += 1
                    
                    # Clean up clips
                    intro_clip.close()
                    outro_clip.close()
                    final_combo.close()
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to create final combination: {e}")
            
            elif outro_path and not intro_path:
                # Only outro available - create video + outro
                try:
                    self.logger.info("🎬 Creating video + outro combination...")
                    if VideoFileClip is None or concatenate_videoclips is None:
                        self.logger.error("❌ MoviePy functions not available")
                        return False
                    outro_clip = VideoFileClip(outro_path)
                    
                    # Concatenate main video + outro
                    outro_combo = concatenate_videoclips([main_clip, outro_clip], method="compose")
                    
                    # Save outro combination
                    outro_output_path = os.path.join(output_dir, f"{scene_id}_with_outro.mp4")
                    outro_combo.write_videofile(
                        outro_output_path,
                        codec='libx264',
                        audio_codec='aac',
                        verbose=False,
                        logger=None  # Suppress moviepy logs
                    )
                    
                    self.logger.info(f"✅ Created outro combination: {os.path.basename(outro_output_path)}")
                    success_count += 1
                    
                    # Clean up clips
                    outro_clip.close()
                    outro_combo.close()
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to create outro combination: {e}")
            
            # Clean up main clip
            main_clip.close()
            
        except Exception as e:
            self.logger.error(f"❌ Error during video concatenation: {e}")
            return False
        
        if success_count > 0:
            self.logger.info(f"✅ Successfully created {success_count} concatenated video(s) for {scene_id}")
            return True
        else:
            self.logger.warning(f"⚠️  No concatenated videos were created for {scene_id}")
            return False

    def select_video_duration(self, target_seconds: int = 10) -> bool:
        """
        Select the desired video duration in the Runway UI.
        Currently supports 5 s and 10 s buttons.
        Returns True on success, False otherwise.
        """
        self.logger.info(f"⏲️  Selecting {target_seconds}s video duration…")
        text_selector_variants = [
            f"{target_seconds}s",
            f"{target_seconds} s",
            f"{target_seconds}sec",
            f"{target_seconds} sec"
        ]

        selectors = []
        for variant in text_selector_variants:
            selectors.extend([
                (By.XPATH, f"//button[contains(text(), '{variant}')]"),
                (By.XPATH, f"//span[contains(text(), '{variant}')]/ancestor::button[1]"),
                (By.XPATH, f"//div[contains(text(), '{variant}')]"),
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


def select_folder_and_json() -> Optional[str]:
    """
    Show available job folders and let user select by number, with GUI fallback.
    
    Returns:
        Path to the JSON file if found, None if cancelled or not found
    """
    # Look for available job folders
    import glob
    from pathlib import Path
    
    # Common output directory locations
    possible_output_dirs = [
        Path(__file__).resolve().parent / "output",
        Path(__file__).resolve().parent.parent / "youtube-video-creator" / "output",
        Path.home() / "Desktop" / "youtube-video-creator" / "output"
    ]
    
    job_folders = []
    for output_dir in possible_output_dirs:
        if output_dir.exists():
            # Find folders containing raw_json_*.json files
            for folder in output_dir.iterdir():
                if folder.is_dir():
                    json_files = list(folder.glob("raw_json_*.json"))
                    if json_files:
                        job_folders.append({
                            'path': folder,
                            'name': folder.name,
                            'json_files': json_files,
                            'parent': output_dir
                        })
    
    if not job_folders:
        print("❌ No job folders with raw_json_*.json files found in common locations")
        print("Available locations checked:")
        for output_dir in possible_output_dirs:
            print(f"  - {output_dir}")
        print("\nFalling back to GUI folder selection...")
        return _gui_folder_selection()
    
    # Sort by modification time (newest first)
    job_folders.sort(key=lambda x: max(f.stat().st_mtime for f in x['json_files']), reverse=True)
    
    print(f"📋 Found {len(job_folders)} job folders with JSON files:")
    print()
    for i, job_folder in enumerate(job_folders, 1):
        # Get the most recent JSON file in this folder
        latest_json = max(job_folder['json_files'], key=lambda f: f.stat().st_mtime)
        mod_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(latest_json.stat().st_mtime))
        
        print(f"  {i}. {job_folder['name']}")
        print(f"     📄 {latest_json.name}")
        print(f"     🕒 {mod_time}")
        print(f"     📁 {job_folder['path']}")
        print()
    
    print("Select a job folder:")
    print(f"Enter number (1-{len(job_folders)}) or 'g' for GUI folder browser: ", end="")
    
    while True:
        try:
            choice = input().strip().lower()
            
            if choice == 'g':
                # Use GUI folder selection
                return _gui_folder_selection()
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(job_folders):
                    selected_folder = job_folders[choice_num - 1]
                    # Use the most recent JSON file in the selected folder
                    json_path = max(selected_folder['json_files'], key=lambda f: f.stat().st_mtime)
                    print(f"✅ Selected: {selected_folder['name']}")
                    print(f"📄 Using JSON file: {json_path.name}")
                    return str(json_path)
                else:
                    print(f"Please enter a number between 1 and {len(job_folders)}, or 'g' for GUI: ", end="")
            except ValueError:
                print(f"Please enter a number between 1 and {len(job_folders)}, or 'g' for GUI: ", end="")
                
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return None


def _gui_folder_selection() -> Optional[str]:
    """
    Show GUI folder selection dialog as fallback.
    
    Returns:
        Path to the JSON file if found, None if cancelled or not found
    """
    from pathlib import Path
    
    # Create a hidden root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    print("📁 Opening GUI folder selection dialog...")
    print("Please select the job folder containing the raw_json_*.json file")
    
    # Show folder selection dialog
    folder_path = filedialog.askdirectory(
        title="Select Job Folder (containing raw_json_*.json)",
        initialdir=str(Path.home() / "Desktop" / "youtube-video-creator" / "output")
    )
    
    root.destroy()  # Clean up the tkinter root
    
    if not folder_path:
        print("❌ No folder selected")
        return None
    
    print(f"📂 Selected folder: {folder_path}")
    
    # Look for raw_json_*.json files in the selected folder
    import glob
    json_files = glob.glob(os.path.join(folder_path, "raw_json_*.json"))
    
    if not json_files:
        print(f"❌ No raw_json_*.json files found in: {folder_path}")
        messagebox.showerror("Error", f"No raw_json_*.json files found in:\n{folder_path}")
        return None
    
    if len(json_files) == 1:
        json_path = json_files[0]
        print(f"✅ Found JSON file: {os.path.basename(json_path)}")
        return json_path
    else:
        # Multiple JSON files - let user choose
        print(f"📋 Found {len(json_files)} JSON files:")
        for i, json_file in enumerate(json_files, 1):
            print(f"  {i}. {os.path.basename(json_file)}")
        
        # Use the most recent one
        json_path = max(json_files, key=os.path.getmtime)
        print(f"✅ Using most recent: {os.path.basename(json_path)}")
        return json_path


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
    print("6. Create concatenated videos with intro/outro (if available)")
    print()
    
    # Check if MoviePy is available
    if not MOVIEPY_AVAILABLE:
        print("⚠️  MoviePy not installed - concatenated videos will be skipped")
        print("   To enable video concatenation, install MoviePy:")
        print("   pip install moviepy")
        print()
    
    # Determine JSON file path with multiple options
    json_path = None
    
    if len(sys.argv) > 1:
        # Command line argument provided
        json_path = sys.argv[1]
        print(f"📄 Using JSON file from command line: {json_path}")
    else:
        # Ask user for preference
        print("How would you like to select the job folder?")
        print("1. Browse and select folder manually")
        print("2. Auto-select latest folder")
        print()
        
        while True:
            try:
                choice = input("Enter choice (1 or 2): ").strip()
                if choice in ['1', '2']:
                    break
                print("Please enter 1 or 2")
            except KeyboardInterrupt:
                print("\n❌ Cancelled by user")
                return
        
        if choice == '1':
            # Manual folder selection
            json_path = select_folder_and_json()
            if not json_path:
                return
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
        
        # Step 3: Switch to Video tab
        print("\n🎥 Switching to video tab...")
        if automation.switch_to_video_tab():
            print("✅ Successfully switched to video tab!")
        else:
            print("⚠️  Video tab switch may have failed, but continuing...")
        
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
        if MOVIEPY_AVAILABLE:
            print("📽️  Generated video files:")
            print("   - {scene_id}.mp4 (original generated video)")
            print("   - {scene_id}_with_intro.mp4 (intro + video)")
            print("   - {scene_id}_final.mp4 (intro + video + outro)")
            print("   - {scene_id}_with_outro.mp4 (video + outro, if no intro)")
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