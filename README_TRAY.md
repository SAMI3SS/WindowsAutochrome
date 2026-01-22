# System Tray Icon Installation

## Installation

1. **Install required libraries:**
   ```powershell
   pip install pystray pillow
   ```

2. **Run in system tray mode:**
   ```powershell
   python main.py --tray
   ```

3. **For auto-start (optional):**
   ```powershell
   python install_tray.py
   ```

## Usage

- Autochrome icon will appear in the system tray (bottom-right corner)
- Click the icon to open "Select Profile" menu
- Click "Select Profile" to open the profile selection window

## Uninstall

```powershell
python install_tray.py uninstall
```
