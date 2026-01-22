# WindowsAutochrome
<<<<<<< HEAD

A Chromium profile launcher for Windows with colored themes, designed for penetration testing and security research. Works seamlessly with Burp Suite.

## Features

- **8 Colored Profiles** - Red, Blue, Green, Yellow, Purple, Orange, Cyan, White
- **Burp Suite Integration** - Automatically configured to work with Burp Suite proxy (127.0.0.1:8080)
- **Security-Focused** - Pre-configured with penetration testing flags
- **Auto-Setup** - Automatically downloads Chromium on first run
- **Native Profile Picker** - Uses Chromium's built-in profile selection
- **System Tray Support** - Run in background with tray icon

## Quick Start

### Installation

```bash
pip install customtkinter pystray pillow pywin32
```

### Running

**Option 1: Double-click `launch.bat`** 
- Just double-click the file - it works like a regular app

**Option 2: Command line** (Recommended)
```bash
python main.py
```

On first run, the script will automatically:
- Download Chromium (~100-150 MB)
- Create 8 colored profiles
- Create a desktop shortcut
- Launch Chromium with profile picker

## Usage

### Normal Mode (Profile Picker)
```bash
python main.py
```
Launches Chromium showing all 8 colored profiles. Click any profile to start browsing.

### Launch Specific Profile
```bash
python main.py --profile Red
```
Launches Chromium directly with the specified profile.

### System Tray Mode
```bash
python main.py --tray
```
Runs in system tray. Right-click the icon to select a profile.

### Repair Profiles
```bash
python main.py --repair
```
Re-seeds all profiles to ensure themes are properly loaded.

## Profiles

Each profile has:
- **Isolated browser data** - Separate cookies, history, and settings
- **Colored top frame** - Visual identification by color
- **Auto proxy** - Configured for Burp Suite (127.0.0.1:8080)
- **Security flags** - Optimized for penetration testing

Available profiles:
- **Red** - #EA4335
- **Blue** - #4285F4
- **Green** - #34A853
- **Yellow** - #FBBC04
- **Purple** - #9C27B0
- **Orange** - #FF9800
- **Cyan** - #00BCD4
- **White** - #FFFFFF

## Project Structure

```
WindowsAutochrome/
├── main.py                 # Main launcher
├── launch.bat              # Quick launcher
├── launch.vbs              # Silent launcher (no terminal)
├── create_shortcut.py      # Desktop shortcut creator
├── install_tray.py         # System tray installer
└── README.md              # This file
```

## Requirements

- Python 3.7+
- Windows 10/11
- Internet connection (for first-time Chromium download)

## Burp Suite Integration

WindowsAutochrome is designed to work seamlessly with Burp Suite:

- **Automatic Proxy Configuration** - All profiles are pre-configured to use Burp Suite's default proxy (127.0.0.1:8080)
- **No Manual Setup Required** - Just start Burp Suite, then launch WindowsAutochrome
- **Isolated Profiles** - Each colored profile has separate browser data, making it easy to test different scenarios
- **Security Flags** - Pre-configured with security-focused Chromium flags optimized for penetration testing

To use with Burp Suite:
1. Start Burp Suite and ensure the proxy is running on 127.0.0.1:8080
2. Launch WindowsAutochrome: `python main.py` or double-click `launch.bat`
3. Select any profile - traffic will automatically route through Burp Suite

## Notes

- Chromium is automatically downloaded on first run
- All browser data is isolated per profile
- Proxy is pre-configured for Burp Suite (127.0.0.1:8080)
- Profiles are created automatically with colored themes

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
=======
(autochrome for Windows) Chromium profile launcher for Windows with colored themes and automatic Burp Suite proxy configuration. Perfect for penetration testing and security research.
>>>>>>> 50dd32dece1b63683f4ae446c71610941d428901
