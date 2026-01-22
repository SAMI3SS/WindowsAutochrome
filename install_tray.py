"""
Windows Tray Icon Installer
Starts as system tray icon on Windows boot.
"""

import os
import sys
import winreg
import ctypes

# Admin privileges check
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_startup():
    """Add shortcut to Windows startup folder."""
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PYTHON_EXE = sys.executable
    MAIN_PY = os.path.join(BASE_DIR, "main.py")
    
    # Startup folder
    startup_folder = os.path.join(
        os.getenv("APPDATA"),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )
    os.makedirs(startup_folder, exist_ok=True)
    
    # Create VBScript (to run in background)
    vbs_path = os.path.join(startup_folder, "AutochromeTray.vbs")
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "{PYTHON_EXE} ""{MAIN_PY}"" --tray", 0, False
Set WshShell = Nothing
'''
    
    try:
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_content)
        print(f"[OK] Startup shortcut added: {vbs_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def uninstall_startup():
    """Remove startup shortcut."""
    startup_folder = os.path.join(
        os.getenv("APPDATA"),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )
    vbs_path = os.path.join(startup_folder, "AutochromeTray.vbs")
    
    try:
        if os.path.exists(vbs_path):
            os.remove(vbs_path)
            print(f"[OK] Startup shortcut removed: {vbs_path}")
        else:
            print(f"  - Shortcut not found (already removed)")
        return True
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall_startup()
    else:
        install_startup()
    
    input("\nPress Enter to continue...")
