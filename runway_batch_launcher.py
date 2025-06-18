#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RunwayML Batch Launcher

Interactive CLI launcher for selecting output folders and running runway automation.
Scans the youtube-video-creator/output directory for available jobs and lets you select one.
"""

import os
import sys
import json
import glob
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

def find_youtube_creator_root() -> Optional[str]:
    """
    Find the youtube-video-creator root directory.
    
    Returns:
        Path to youtube-video-creator root, or None if not found
    """
    # Direct path check first
    direct_path = r"C:\Users\thiago\Desktop\youtube-video-creator"
    if (os.path.exists(direct_path) and 
        os.path.exists(os.path.join(direct_path, "runway_automation")) and 
        os.path.exists(os.path.join(direct_path, "output"))):
        return direct_path
    
    # Search for youtube-video-creator directories
    search_locations = [
        r"C:\Users\thiago\Desktop",
        r"C:\Users\thiago\Documents", 
        r"C:\Users\thiago",
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~")
    ]
    
    for search_root in search_locations:
        try:
            if os.path.exists(search_root):
                for item in os.listdir(search_root):
                    if "youtube-video-creator" in item.lower():
                        candidate = os.path.join(search_root, item)
                        if (os.path.isdir(candidate) and
                            os.path.exists(os.path.join(candidate, "runway_automation")) and 
                            os.path.exists(os.path.join(candidate, "output"))):
                            return candidate
        except (OSError, PermissionError):
            continue
    
    return None

def scan_output_folders(output_dir: str) -> List[Dict[str, Any]]:
    """
    Scan the output directory for available job folders.
    
    Args:
        output_dir: Path to the output directory
        
    Returns:
        List of job info dictionaries
    """
    jobs = []
    
    if not os.path.exists(output_dir):
        print(f"❌ Output directory not found: {output_dir}")
        return jobs
    
    # Look for folders that match the pattern yout_YYYYMMDD_HHMMSS
    pattern = os.path.join(output_dir, "yout_*")
    job_folders = glob.glob(pattern)
    
    for job_folder in sorted(job_folders, reverse=True):  # Most recent first
        if not os.path.isdir(job_folder):
            continue
            
        job_id = os.path.basename(job_folder)
        
        # Look for required files
        json_pattern = os.path.join(job_folder, f"raw_json_{job_id}.json")
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            continue
            
        json_file = json_files[0]
        
        # Count getimg images
        image_pattern = os.path.join(job_folder, "*_getimg.png")
        image_files = glob.glob(image_pattern)
        
        # Try to get title from JSON
        title = "Unknown"
        total_scenes = 0
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                title = json_data.get('title', job_id)
                scene_directions = json_data.get('scene_directions', [])
                total_scenes = len(scene_directions)
        except:
            pass
        
        # Calculate folder size
        folder_size = 0
        try:
            for root, dirs, files in os.walk(job_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        folder_size += os.path.getsize(file_path)
        except:
            pass
        
        job_info = {
            'id': job_id,
            'folder': job_folder,
            'json_file': json_file,
            'title': title,
            'image_count': len(image_files),
            'total_scenes': total_scenes,
            'folder_size': folder_size,
            'created': os.path.getctime(job_folder)
        }
        
        jobs.append(job_info)
    
    return jobs

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def display_jobs(jobs: List[Dict[str, Any]]):
    """Display available jobs in a formatted table."""
    if not jobs:
        print("❌ No valid job folders found!")
        print("   Job folders should contain:")
        print("   - raw_json_<job_id>.json file")
        print("   - *_getimg.png image files")
        return
    
    print(f"\n📁 Found {len(jobs)} available job(s):")
    print("=" * 100)
    print(f"{'#':<3} {'Job ID':<25} {'Title':<30} {'Images':<8} {'Scenes':<8} {'Size':<10}")
    print("=" * 100)
    
    for i, job in enumerate(jobs, 1):
        title_short = job['title'][:27] + "..." if len(job['title']) > 30 else job['title']
        print(f"{i:<3} {job['id']:<25} {title_short:<30} {job['image_count']:<8} {job['total_scenes']:<8} {format_file_size(job['folder_size']):<10}")
    
    print("=" * 100)

def select_job(jobs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Let user select a job from the list.
    
    Args:
        jobs: List of available jobs
        
    Returns:
        Selected job info, or None if cancelled
    """
    while True:
        try:
            choice = input(f"\n🎯 Select job (1-{len(jobs)}, or 'q' to quit): ").strip()
            
            if choice.lower() in ['q', 'quit', 'exit']:
                return None
            
            job_index = int(choice) - 1
            if 0 <= job_index < len(jobs):
                return jobs[job_index]
            else:
                print(f"❌ Invalid choice. Please enter a number between 1 and {len(jobs)}")
        
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            return None

def validate_job(job: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that a job has all required files.
    
    Args:
        job: Job info dictionary
        
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    # Check JSON file exists
    if not os.path.exists(job['json_file']):
        issues.append(f"JSON file not found: {job['json_file']}")
        return False, issues
    
    # Load JSON to understand the structure
    try:
        with open(job['json_file'], 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        issues.append(f"Cannot parse JSON file: {e}")
        return False, issues
    
    scene_directions = json_data.get('scene_directions', [])
    expected_images = json_data.get('getimg_images', [])
    
    # Check that we have images
    image_pattern = os.path.join(job['folder'], "*_getimg.png")
    actual_image_files = glob.glob(image_pattern)
    actual_image_names = [os.path.basename(f) for f in actual_image_files]
    
    if not actual_image_files:
        issues.append(f"No getimg images found in {job['folder']}")
        return False, issues
    
    # Validate each scene has the required images
    missing_images = []
    scenes_needing_images = 0
    
    for i, scene_data in enumerate(scene_directions):
        scene_id = f"scene_{i}"
        
        # Skip narration-only scenes (null scene_desc)
        if scene_data.get('scene_desc') is None:
            continue
        
        scenes_needing_images += 1
        
        # Check if scene has events (multiple images)
        if 'events' in scene_data and scene_data['events']:
            # Event-based scene - check for event images
            for j, event in enumerate(scene_data['events']):
                expected_image = f"scene_{i}_event_{j}_getimg.png"
                if expected_image not in actual_image_names:
                    missing_images.append(expected_image)
        else:
            # Regular scene - check for single image
            expected_image = f"scene_{i}_getimg.png"
            if expected_image not in actual_image_names:
                missing_images.append(expected_image)
    
    if missing_images:
        issues.append(f"Missing scene images: {', '.join(missing_images[:5])}{'...' if len(missing_images) > 5 else ''}")
    
    # Check for unexpected images (not in expected list)
    unexpected_images = []
    for actual_name in actual_image_names:
        if actual_name not in expected_images:
            unexpected_images.append(actual_name)
    
    if unexpected_images:
        issues.append(f"Unexpected images found: {', '.join(unexpected_images[:3])}{'...' if len(unexpected_images) > 3 else ''}")
    
    # Summary
    print(f"📊 Validation Summary:")
    print(f"   Total scenes: {len(scene_directions)}")
    print(f"   Scenes needing images: {scenes_needing_images}")
    print(f"   Expected images: {len(expected_images)}")
    print(f"   Actual images found: {len(actual_image_files)}")
    print(f"   Missing images: {len(missing_images)}")
    
    return len(missing_images) == 0, issues

def main():
    """Main CLI application."""
    print("🎬 RunwayML Batch Launcher")
    print("=" * 50)
    print("Interactive launcher for RunwayML video generation")
    print()
    
    # Add debug info
    print(f"🔍 Current working directory: {os.getcwd()}")
    print(f"🔍 Script location: {os.path.dirname(os.path.abspath(__file__))}")
    print()
    
    # Find youtube-video-creator root
    print("🔍 Locating youtube-video-creator directory...")
    youtube_root = find_youtube_creator_root()
    
    if not youtube_root:
        print("❌ Could not auto-detect youtube-video-creator directory!")
        print()
        print("Please enter the full path to your youtube-video-creator folder:")
        print("Example: C:\\Users\\thiago\\Desktop\\youtube-video-creator")
        print()
        
        while True:
            manual_path = input("📁 Path (or 'q' to quit): ").strip()
            
            if manual_path.lower() in ['q', 'quit', 'exit']:
                print("👋 Exiting.")
                return 0
            
            if manual_path and os.path.exists(manual_path):
                output_path = os.path.join(manual_path, "output")
                if os.path.exists(output_path):
                    # Check if output folder has job folders
                    try:
                        output_contents = os.listdir(output_path)
                        has_job_folders = any(item.startswith("yout_") for item in output_contents 
                                            if os.path.isdir(os.path.join(output_path, item)))
                        if has_job_folders:
                            youtube_root = manual_path
                            break
                        else:
                            print("❌ Directory doesn't contain job folders (yout_*) in output folder")
                    except:
                        print("❌ Cannot read output folder")
                else:
                    print("❌ Directory doesn't contain 'output' folder")
            else:
                print("❌ Directory not found. Please check the path.")
        
        if not youtube_root:
            return 1
    
    print(f"✅ Found: {youtube_root}")
    
    # Find output directory
    output_dir = os.path.join(youtube_root, "output")
    
    # Scan for available jobs
    print(f"📂 Scanning for jobs in: {output_dir}")
    jobs = scan_output_folders(output_dir)
    
    # Display available jobs
    display_jobs(jobs)
    
    if not jobs:
        return 1
    
    # Let user select a job
    selected_job = select_job(jobs)
    
    if not selected_job:
        print("👋 No job selected. Exiting.")
        return 0
    
    print(f"\n🎯 Selected job: {selected_job['id']}")
    print(f"📝 Title: {selected_job['title']}")
    
    # Validate the selected job
    print("🔍 Validating job files...")
    is_valid, issues = validate_job(selected_job)
    
    if not is_valid:
        print("❌ Job validation failed:")
        for issue in issues:
            print(f"   - {issue}")
        
        proceed = input("\n⚠️  Continue anyway? (y/N): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("👋 Cancelled by user.")
            return 0
    else:
        print("✅ Job validation passed!")
    
    # Show what will happen and get confirmation
    print(f"\n🚀 Ready to process {selected_job['total_scenes']} scenes")
    print(f"📁 Videos will be saved to: {os.path.join(selected_job['folder'], 'videos')}")
    print("🎬 This will:")
    print("   - Open Chrome browser")
    print("   - Login to RunwayML")
    print("   - Process each scene automatically")
    print("   - Download videos to the job folder")
    
    confirm = input("\n▶️  Start processing? (Y/n): ").strip().lower()
    if confirm in ['n', 'no']:
        print("👋 Cancelled by user.")
        return 0
    
    # Import and run the automation
    print("\n🔧 Preparing automation...")
    
    try:
        # Add the runway_automation folder to Python path
        sys.path.insert(0, os.path.join(youtube_root, "runway_automation"))
        
        # Import runway_slim
        from runway_slim import RunwayMLSlim
        
        # Create custom version that uses our selected paths
        print("🌐 Starting browser automation...")
        
        automation = RunwayMLSlim(
            browser_name="chrome",
            manual_login=False,
            use_undetected=True
        )
        
        # Patch the automation to use our paths
        original_get_motion = automation.get_motion_description_from_json
        original_process_single = automation._process_single_scene
        
        def custom_get_motion(json_path, scene_id):
            return original_get_motion(selected_job['json_file'], scene_id)
        
        def custom_process_single(scene_id, image_path, json_path, output_dir):
            # Use the correct image path from our job folder
            correct_image_path = os.path.join(selected_job['folder'], f"{scene_id}_getimg.png")
            return original_process_single(
                scene_id, 
                correct_image_path, 
                selected_job['json_file'],
                os.path.join(selected_job['folder'], 'videos')
            )
        
        # Monkey patch the methods
        automation.get_motion_description_from_json = custom_get_motion
        automation._process_single_scene = custom_process_single
        
        # Navigate and login
        print("🔐 Logging in to RunwayML...")
        if not automation.navigate_to_login():
            print("❌ Failed to navigate to login page")
            return 1
        
        if not automation.login():
            print("❌ Login failed")
            return 1
        
        print("✅ Login successful!")
        
        # Switch to video tab
        print("🎥 Switching to video tab...")
        if automation.switch_to_video_tab():
            print("✅ Video tab selected!")
        else:
            print("⚠️  Video tab selection may have failed, continuing...")
        
        # Process scenes using the original batch method but with our custom paths
        video_output_dir = os.path.join(selected_job['folder'], 'videos')
        os.makedirs(video_output_dir, exist_ok=True)
        
        print(f"\n🎬 Starting batch processing of {selected_job['total_scenes']} scenes...")
        results = automation.process_all_scenes(selected_job['json_file'], video_output_dir)
        
        # Display results
        print("\n" + "="*50)
        print("📊 BATCH PROCESSING RESULTS")
        print("="*50)
        print(f"✅ Completed: {len(results.get('completed', []))}")
        print(f"❌ Failed: {len(results.get('failed', []))}")
        print(f"⏭️  Skipped: {len(results.get('skipped', []))}")
        
        if results.get('completed'):
            print(f"\n✅ Successfully completed: {', '.join(results['completed'])}")
        if results.get('failed'):
            print(f"\n❌ Failed scenes:")
            for failed in results['failed']:
                if isinstance(failed, dict):
                    print(f"   - {failed.get('scene', 'unknown')}: {failed.get('error', 'unknown error')}")
        
        success_rate = len(results.get('completed', [])) / selected_job['total_scenes'] * 100
        print(f"\n📈 Success rate: {success_rate:.1f}% ({len(results.get('completed', []))}/{selected_job['total_scenes']})")
        print(f"📁 Videos saved to: {video_output_dir}")
        
        automation.close()
        
        if success_rate > 0:
            print("\n🎉 Batch processing completed!")
            return 0
        else:
            print("\n❌ No scenes were processed successfully.")
            return 1
        
    except ImportError as e:
        print(f"❌ Failed to import runway_slim: {e}")
        print("   Make sure runway_slim.py is in the runway_automation folder")
        return 1
    except Exception as e:
        print(f"❌ Error running automation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 