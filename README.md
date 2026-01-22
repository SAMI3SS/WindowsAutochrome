# WindowsAutochrome

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

1. **Clone the repository:**
```bash
git clone https://github.com/SAMI3SS/WindowsAutochrome.git
cd /WindowsAutochrome
```

2. **Run the launcher:**
```bash
python main.py
```

**First run:** The script will automatically:
- Install required Python packages (customtkinter, pystray, pillow, pywin32)
- Download Chromium (~100-150 MB)
- Create 8 colored profiles
- Create a desktop shortcut with Chromium icon
- Launch Chromium with profile picker

**After first run:** Simply double-click the desktop shortcut to launch Chromium. No need to run Python commands again - the shortcut works like a regular application.

## Usage

### Normal Mode (Profile Picker)
```bash
python main.py (Recommended)
```
Launches Chromium showing all 8 colored profiles. Click any profile to start browsing.

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
2. Launch WindowsAutochrome: `python main.py` or double-click the desktop shortcut
3. Select any profile - traffic will automatically route through Burp Suite

## Notes

- Chromium is automatically downloaded on first run
- All browser data is isolated per profile
- Proxy is pre-configured for Burp Suite (127.0.0.1:8080)
- Profiles are created automatically with colored themes
- **Desktop shortcut is created automatically** - After first run, you can use the desktop shortcut instead of running Python commands

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
