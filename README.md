# RunwayML Automation

Automates video generation on RunwayML using Selenium, optimized for Gen-4 in 2025.

## Setup

1. Install Python requirements:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your RunwayML credentials:

```
RUNWAY_USERNAME=your_email@example.com
RUNWAY_PASSWORD=your_password
```

You can rename the `env.example` file to `.env` and update it with your credentials.

3. For better compatibility, install undetected-chromedriver:

```bash
pip install undetected-chromedriver
```

## Usage

Run the script to process a JSON file containing scene descriptions:

```bash
python runway_automation.py
```

The script will:
1. Login to RunwayML using your credentials from the `.env` file
2. Process each scene in the JSON file
3. Generate images and videos
4. Save all output to a dedicated directory

## Configuration

- Edit `runway_automation.py` to change default paths or browser settings
- Adjust timeout values in the `RunwayMLAutomation` class if needed
- Default timeout for generation is 4 minutes (240 seconds)

## Supported Browsers

- Chrome (recommended)
- Firefox
- Edge

## Troubleshooting

### Login Issues

If you encounter login problems:

1. Verify your credentials in the `.env` file
2. Ensure you have the correct version of the browser and webdriver
3. Check the log file for detailed error messages

### If Automatic Login Fails

You can switch to manual login mode by changing:

```python
automation = RunwayMLAutomation(manual_login=True)
```

This will allow you to manually complete the login process while the script waits.

## Dependencies

- **selenium**: WebDriver for browser automation
- **webdriver-manager**: Automatic WebDriver binary management  
- **python-dotenv**: Environment variable management
- **Pillow**: Image file verification
- **opencv-python**: Video file verification

If the optional dependencies (Pillow, OpenCV) are not available, the script will fall back to basic file validation.

## Directory Structure

The script expects the following directory structure:

```
output/
  ├── video_id_1/
  │   ├── raw_json_video_id_1.json
  │   └── generated/  (created automatically)
  │       ├── video_id_1_scene0_image.png
  │       ├── video_id_1_scene0.mp4
  │       └── ...
  ├── video_id_2/
  │   └── ...
  └── ...
```

## RunwayML Interface Notes

The script now works with the latest RunwayML interface:

- **Updated URLs**: Uses the current team-specific URLs for Gen-4 tools
- **Video Generation Interface**: Handles the "Drop an image" interface by automating the "Select Asset" option
- **File Uploads**: Automatically manages file uploads using the browser's native dialog

## Performance Optimizations

This script is designed for maximum performance with RunwayML Gen-4:

- **Direct Gen-4 API Access**: Connects directly to Gen-4 endpoints without fallbacks
- **Streamlined URL Validation**: Quick verification of Gen-4 accessibility
- **Fast File Verification**: Efficient validation of generated media
- **Smart Resource Management**: Proper handling of browser sessions and downloads

## Key Features

### Gen-4 Exclusive

The script focuses exclusively on Gen-4 capabilities:
- State-of-the-art image generation quality
- Production-ready video outputs
- Higher consistency and fidelity than older generations

### Enhanced Verification

The script includes verification steps to ensure all Gen-4 outputs are valid:
- Image validation using PIL library
- Video validation using OpenCV
- Automatic regeneration of any invalid files

### Advanced Download Management

The script includes optimized download handling:
- Browser-specific download directory detection
- Real-time monitoring of download completion
- File integrity verification

## Configuration

You can adjust the following settings in the script:

- `MAX_WAIT_TIME`: Maximum wait time for generation (default: 240 seconds)
- `MAX_RETRIES`: Maximum number of retry attempts in case of failure (default: 3)
- `URLS`: Dictionary of RunwayML Gen-4 tool URLs (updated to match the current interface)

## Multiple Events Handling

The script supports scenes with multiple events. For each event in a scene, a separate video will be generated at full Gen-4 quality.

## Logs

Logs are saved in:

```
output/video_id/logs/video_id_automation.log
```

## Limitations

- Requires a RunwayML subscription with Gen-4 access
- Designed specifically for the current Gen-4 interface
- High-quality outputs require sufficient disk space and bandwidth

## Performance Expectations

- Gen-4 Image Generation: ~5-15 seconds per image
- Gen-4 Video Generation: ~20-60 seconds per 4-second clip
- File verification: ~1-3 seconds per file

## Contributions

Contributions are welcome! Feel free to open issues or send pull requests.
