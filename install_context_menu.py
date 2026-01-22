"""
Windows Context Menu Installer
Adds right-click menu to Chromium icon.
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

# Run with admin privileges
def run_as_admin():
    if is_admin():
        return True
    else:
        # Restart with admin privileges
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False

def install_context_menu():
    """Add context menu for Chromium."""
    if not run_as_admin():
        print("Admin privileges required. Please run again.")
        return False
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    LAUNCHER_BAT = os.path.join(BASE_DIR, "launcher.bat")
    PYTHON_EXE = sys.executable
    
    # Chromium executable paths
    chromium_paths = [
        os.path.join(BASE_DIR, "bin", "chrome.exe"),
        r"%LOCALAPPDATA%\PortSwigger\Burp Suite Professional\*\chrome.exe",
        r"%LOCALAPPDATA%\PortSwigger\Burp Suite Community Edition\*\chrome.exe",
    ]
    
    # Registry keys
    # HKEY_CLASSES_ROOT\Applications\chrome.exe\shell\Autochrome\command
    # HKEY_CLASSES_ROOT\Applications\chromium.exe\shell\Autochrome\command
    
    registry_keys = [
        (winreg.HKEY_CLASSES_ROOT, r"Applications\chrome.exe\shell\Autochrome"),
        (winreg.HKEY_CLASSES_ROOT, r"Applications\chromium.exe\shell\Autochrome"),
        (winreg.HKEY_CLASSES_ROOT, r"*\shell\Autochrome"),  # For all files
    ]
    
    # Command string
    command = f'"{PYTHON_EXE}" "{os.path.join(BASE_DIR, "main.py")}"'
    
    try:
        for hkey, key_path in registry_keys:
            try:
                # Create shell key
                key = winreg.CreateKey(hkey, key_path)
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Autochrome Select Profile")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{os.path.join(BASE_DIR, "bin", "chrome.exe")}"')
                winreg.CloseKey(key)
                
                # Create command key
                command_key = winreg.CreateKey(hkey, f"{key_path}\\command")
                winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)
                winreg.CloseKey(command_key)
                
                print(f"[OK] Context menu added: {key_path}")
            except Exception as e:
                print(f"[ERROR] Error ({key_path}): {e}")
        
        print("\n[OK] Context menu successfully added!")
        print("Right-click Chromium icon and see 'Autochrome Select Profile' option.")
        return True
        
    except Exception as e:
        print(f"[ERROR] Registry error: {e}")
        return False

def uninstall_context_menu():
    """Remove context menu."""
    if not run_as_admin():
        print("Admin privileges required. Please run again.")
        return False
    
    registry_keys = [
        (winreg.HKEY_CLASSES_ROOT, r"Applications\chrome.exe\shell\Autochrome"),
        (winreg.HKEY_CLASSES_ROOT, r"Applications\chromium.exe\shell\Autochrome"),
        (winreg.HKEY_CLASSES_ROOT, r"*\shell\Autochrome"),
    ]
    
    try:
        for hkey, key_path in registry_keys:
            try:
                winreg.DeleteKey(hkey, f"{key_path}\\command")
                winreg.DeleteKey(hkey, key_path)
                print(f"[OK] Context menu removed: {key_path}")
            except FileNotFoundError:
                print(f"  - Key not found (already removed): {key_path}")
            except Exception as e:
                print(f"[ERROR] Error ({key_path}): {e}")
        
        print("\n[OK] Context menu successfully removed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Registry error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall_context_menu()
    else:
        install_context_menu()
    
    input("\nPress Enter to continue...")
