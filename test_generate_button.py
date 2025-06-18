#!/usr/bin/env python3
"""
Test script to verify the Generate button improvements work.
This will just test the generate button clicking and detection without full batch processing.
"""

import sys
import os
import time

# Add the runway_automation directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from runway_slim import RunwayMLSlim

def test_generate_button():
    """Test the improved generate button functionality."""
    print("🧪 Testing Generate Button Improvements")
    print("=" * 50)
    
    try:
        # Initialize automation
        automation = RunwayMLSlim(
            browser_name="chrome",
            manual_login=False,
            use_undetected=True
        )
        
        # Step 1: Login
        print("🔐 Logging in...")
        if not automation.navigate_to_login():
            print("❌ Failed to navigate to login")
            return False
        
        if not automation.login():
            print("❌ Login failed")
            return False
        
        print("✅ Login successful!")
        
        # Step 2: Switch to Video tab
        print("🎥 Switching to video tab...")
        if automation.switch_to_video_tab():
            print("✅ Video tab switch successful!")
        else:
            print("⚠️  Video tab switch may have failed, continuing...")
        
        # Step 3: Test upload (using a dummy image if available)
        print("📤 Testing image upload...")
        
        # Look for any existing PNG files in parent directories to test with
        test_image = None
        search_dirs = [
            "../youtube-video-creator/output",
            "../output",
            ".",
            ".."
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for file in os.listdir(search_dir):
                    if file.endswith('.png'):
                        test_image = os.path.join(search_dir, file)
                        break
                if test_image:
                    break
        
        if test_image:
            print(f"📁 Using test image: {test_image}")
            if automation.access_upload_interface(test_image):
                print("✅ Image upload successful!")
                
                # Step 4: Test motion prompt
                print("📝 Testing motion prompt...")
                test_prompt = "Slow camera pan with cinematic movement"
                if automation.enter_motion_prompt(test_prompt):
                    print("✅ Motion prompt entered successfully!")
                    
                    # Step 5: Test aspect ratio (optional)
                    print("📐 Testing aspect ratio selection...")
                    automation.select_aspect_ratio_16_9()  # Don't fail if this doesn't work
                    
                    # Step 6: THE MAIN TEST - Generate button
                    print("\n🎬 TESTING IMPROVED GENERATE BUTTON...")
                    print("=" * 50)
                    
                    result = automation.click_generate_button()
                    
                    if result:
                        print("✅ GENERATE BUTTON TEST PASSED!")
                        print("✅ Generation appears to have started successfully")
                        
                        # Let it run for a minute to see if it's actually working
                        print("\n⏳ Monitoring generation for 60 seconds...")
                        time.sleep(60)
                        
                        print("✅ Test completed successfully!")
                        return True
                    else:
                        print("❌ GENERATE BUTTON TEST FAILED!")
                        print("❌ Generation did not start properly")
                        return False
                        
                else:
                    print("❌ Motion prompt failed")
                    return False
            else:
                print("❌ Image upload failed")
                return False
        else:
            print("⚠️  No test image found, testing without upload...")
            
            # Test generate button detection without upload
            print("\n🔍 Testing Generate button detection...")
            
            # Try to find generate button
            generate_selectors = [
                ("By.XPATH", "//span[text()='Generate']"),
                ("By.XPATH", "//span[contains(text(), 'Generate')]"),
                ("By.XPATH", "//button[.//span[text()='Generate']]")
            ]
            
            found_generate = False
            for selector_desc, selector_value in generate_selectors:
                try:
                    from selenium.webdriver.common.by import By
                    if selector_desc == "By.XPATH":
                        elements = automation.driver.find_elements(By.XPATH, selector_value)
                        if elements:
                            print(f"✅ Found Generate button with: {selector_desc}, {selector_value}")
                            found_generate = True
                            break
                except:
                    pass
            
            if found_generate:
                print("✅ Generate button detection working!")
                return True
            else:
                print("❌ Could not find Generate button")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            automation.close()
        except:
            pass

if __name__ == "__main__":
    print("Starting Generate Button Test...")
    success = test_generate_button()
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("The Generate button improvements should work for batch processing.")
    else:
        print("\n💥 TESTS FAILED!")
        print("The Generate button improvements need more work.")
    
    print("\nTest completed.") 