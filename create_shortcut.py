"""
Creates desktop shortcut for WindowsAutochrome (Python script).
Uses multiple methods: win32com, VBScript, PowerShell (in order of preference).
"""

import os
import sys
import subprocess
import tempfile

def find_icon_path(BASE_DIR):
    """Find Chromium icon to use for the shortcut."""
    # Priority 1: Chromium in bin/
    chrome_icon = os.path.join(BASE_DIR, "bin", "chrome.exe")
    if os.path.exists(chrome_icon):
        return chrome_icon
    
    # Priority 2: Burp Suite Chromium
    localappdata = os.getenv("LOCALAPPDATA", "")
    if localappdata:
        import glob
        burp_patterns = [
            os.path.join(localappdata, "PortSwigger", "Burp Suite Professional", "**", "chrome.exe"),
            os.path.join(localappdata, "PortSwigger", "Burp Suite Community Edition", "**", "chrome.exe"),
        ]
        for pattern in burp_patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches and os.path.isfile(matches[0]):
                return matches[0]
    
    return None

def create_shortcut_vbscript(shortcut_path, target_path, working_dir, icon_path=None):
    """Create shortcut using VBScript (most reliable, no dependencies)."""
    vbscript = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_path}"
oLink.WorkingDirectory = "{working_dir}"
'''
    if icon_path:
        # Add ",0" to specify icon index (0 = first icon in file)
        vbscript += f'oLink.IconLocation = "{icon_path},0"\n'
    
    vbscript += '''oLink.Description = "WindowsAutochrome - Chromium Profile Launcher"
oLink.Save
'''
    
    # Write VBScript to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.vbs', delete=False, encoding='utf-8') as f:
        f.write(vbscript)
        vbscript_path = f.name
    
    try:
        # Run VBScript
        result = subprocess.run(
            ["cscript", "//Nologo", vbscript_path],
            capture_output=True,
            timeout=10,
            text=True,
            encoding='utf-8',
            errors='ignore'  # Ignore encoding errors
        )
        return result.returncode == 0
    finally:
        # Clean up temp file
        try:
            os.unlink(vbscript_path)
        except:
            pass

def create_shortcut():
    """Create desktop shortcut to Python script with Chromium icon."""
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Desktop path
    desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
    shortcut_path = os.path.join(desktop, "WindowsAutochrome.lnk")
    
    # Target: launch.vbs (runs without terminal window)
    # Fallback to launch.bat if VBS doesn't exist
    launch_vbs = os.path.join(BASE_DIR, "launch.vbs")
    launch_bat = os.path.join(BASE_DIR, "launch.bat")
    target_path = launch_vbs if os.path.exists(launch_vbs) else launch_bat
    
    # Find icon
    icon_path = find_icon_path(BASE_DIR)
    
    # Method 1: Try win32com (if available)
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.Arguments = ""
        shortcut.WorkingDirectory = BASE_DIR
        if icon_path:
            shortcut.IconLocation = f"{icon_path},0"  # ",0" = first icon in file
        shortcut.Description = "WindowsAutochrome - Chromium Profile Launcher"
        shortcut.save()
        print(f"Shortcut created: {shortcut_path} (using win32com)")
        return True
    except ImportError:
        pass  # Continue to next method
    except Exception as e:
        print(f"win32com error: {e}")
    
    # Method 2: Try VBScript (most reliable, no dependencies)
    try:
        # Escape paths for VBScript (double backslashes)
        shortcut_path_escaped = shortcut_path.replace("\\", "\\\\")
        target_path_escaped = target_path.replace("\\", "\\\\")
        working_dir_escaped = BASE_DIR.replace("\\", "\\\\")
        icon_path_escaped = icon_path.replace("\\", "\\\\") if icon_path else None
        
        if create_shortcut_vbscript(shortcut_path_escaped, target_path_escaped, working_dir_escaped, icon_path_escaped):
            if os.path.exists(shortcut_path):
                print(f"Shortcut created: {shortcut_path} (using VBScript)")
                return True
    except Exception as e:
        print(f"VBScript error: {e}")
    
    # Method 3: Try PowerShell (fallback)
    try:
        target_path_escaped = target_path.replace("\\", "\\\\")
        working_dir_escaped = BASE_DIR.replace("\\", "\\\\")
        icon_arg = ""
        if icon_path:
            icon_path_escaped = icon_path.replace("\\", "\\\\")
            icon_arg = f'$Shortcut.IconLocation = "{icon_path_escaped}"'
        
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_path_escaped}"
$Shortcut.WorkingDirectory = "{working_dir_escaped}"
{icon_arg}
$Shortcut.Description = "WindowsAutochrome - Chromium Profile Launcher"
$Shortcut.Save()
'''
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            timeout=10,
            text=True,
            encoding='utf-8',
            errors='ignore'  # Ignore encoding errors
        )
        if os.path.exists(shortcut_path):
            print(f"Shortcut created: {shortcut_path} (using PowerShell)")
            return True
        else:
            if result.stderr:
                print(f"PowerShell error: {result.stderr}")
    except Exception as e:
        print(f"PowerShell error: {e}")
    
    print(f"Error: Could not create shortcut using any method.")
    print(f"Manual: Create shortcut to: {target_path}")
    return False

if __name__ == "__main__":
    create_shortcut()
