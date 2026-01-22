"""
WindowsAutochrome Launcher
Chromium "Who is using Chromium?"-style profile picker and launcher.
"""

import os
import sys
import subprocess
import glob
import zipfile
import shutil
import urllib.request
import urllib.error
import urllib.parse
import threading
import json
import time
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

# Windows-specific creation flags
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
BIN_DIR = os.path.join(BASE_DIR, "bin")
CACHE_DIR = os.path.join(BASE_DIR, ".cache")

# Debug log file
DEBUG_LOG = os.path.join(BASE_DIR, "debug.log")

# Crash log (useful when running --noconsole exe)
CRASH_LOG = os.path.join(BASE_DIR, "crash.log")


def _install_excepthook():
    def _hook(exc_type, exc, tb):
        import traceback
        msg = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(CRASH_LOG, "a", encoding="utf-8") as f:
                f.write("\n" + ("-" * 80) + "\n")
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write(msg)
        except Exception:
            pass
        try:
            messagebox.showerror(
                "WindowsAutochrome Error",
                f"The application crashed:\n\n{exc}\n\nDetails were written to: {CRASH_LOG}",
            )
        except Exception:
            pass
    sys.excepthook = _hook


_install_excepthook()

# Global theme unpack list (filled in setup_all_profiles)
THEMES_UNPACK_DIRS = []  # legacy (unused); keep empty to avoid unexpected behavior

def debug_log(message: str):
    """Write debug message to both stdout and the debug log file."""
    # Print to stdout if available (may be None when running with pythonw.exe)
    try:
        if sys.stdout is not None:
            print(message)
            sys.stdout.flush()
    except Exception:
        pass
    
    # Always write to log file
    try:
        with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception:
        pass

# Chromium download URLs (Autochrome logic)
CHROMIUM_BASE_URL = "https://commondatastorage.googleapis.com/chromium-browser-snapshots/"
CHROMIUM_API_URL = "https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/"
CHROMIUM_TYPE = "Win_x64"
CHROMIUM_ZIP_NAME = "chrome-win32.zip"

# Profile definitions - Chromium profile colors and directory names
COLOR_ORDER = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange", "Cyan", "White"]
CHROME_DIRS = [
    "Default",
    "Profile 1",
    "Profile 2",
    "Profile 3",
    "Profile 4",
    "Profile 5",
    "Profile 6",
    "Profile 7",
]

# Chromium avatar icon mapping (from Autochrome)
AVATAR_ICONS = {
    "White": "chrome://theme/IDR_PROFILE_AVATAR_0",
    "Cyan": "chrome://theme/IDR_PROFILE_AVATAR_1",
    "Blue": "chrome://theme/IDR_PROFILE_AVATAR_2",
    "Green": "chrome://theme/IDR_PROFILE_AVATAR_3",
    "Orange": "chrome://theme/IDR_PROFILE_AVATAR_4",
    "Purple": "chrome://theme/IDR_PROFILE_AVATAR_5",
    "Red": "chrome://theme/IDR_PROFILE_AVATAR_6",
    "Yellow": "chrome://theme/IDR_PROFILE_AVATAR_7",
}

# Map profile names to hex colors
PROFILE_COLOR_MAP = {
    "Red": "#EA4335",
    "Blue": "#4285F4",
    "Green": "#34A853",
    "Yellow": "#FBBC04",
    "Purple": "#9C27B0",
    "Orange": "#FF9800",
    "Cyan": "#00BCD4",
    "White": "#FFFFFF",
}

# PROFILES list (color + hex)
PROFILES = [(name, PROFILE_COLOR_MAP[name]) for name in COLOR_ORDER]


def get_latest_chromium_version():
    """
    Fetch the latest Chromium revision number from the LAST_CHANGE file.
    """
    try:
        last_change_url = f"{CHROMIUM_BASE_URL}{CHROMIUM_TYPE}/LAST_CHANGE"
        with urllib.request.urlopen(last_change_url, timeout=10) as response:
            version = int(response.read().decode().strip())
            return version
    except Exception as e:
        print(f"Failed to get Chromium version: {e}")
        return None


def try_download_version(version, zip_path, progress_callback=None):
    """
    Try to download a specific Chromium version.
    Uses the working URL formats you provided.
    """
    # Possible filenames and URL formats.
    # Windows Chromium builds can have different archive names.
    # Prioritize chrome-win.zip, then chrome-win32.zip.
    possible_filenames = ["chrome-win.zip", "chrome-win32.zip"]
    
    download_attempts = []
    
    # For each filename, try multiple URL formats
    for filename in possible_filenames:
        # Format 1: commondatastorage (primary)
        download_attempts.append({
            "url": f"https://commondatastorage.googleapis.com/chromium-browser-snapshots/Win_x64/{version}/{filename}",
            "name": f"{filename} (commondatastorage)"
        })
        
        # Format 2: Direct Google Cloud Storage API path
        download_attempts.append({
            "url": f"https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Win_x64/{version}/{filename}?alt=media",
            "name": f"{filename} (direkt)"
        })
        
        # Format 3: storage.googleapis.com (fallback)
        download_attempts.append({
            "url": f"https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/{version}/{filename}",
            "name": f"{filename} (storage.googleapis)"
        })
    
    for attempt in download_attempts:
        zip_url = attempt["url"]
        attempt_name = attempt["name"]
        
        try:
            req = urllib.request.Request(zip_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status != 200:
                    continue
                
                total_size = int(response.headers.get('Content-Length', 0))
                
                if progress_callback:
                    progress_callback(5, 0, total_size, f"Downloading Chromium revision {version}...")
                
                print(f"[OK] Found archive: {attempt_name}, downloading...")
                
                # Streaming download
                downloaded = 0
                with open(zip_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            percent = min(100, (downloaded * 100) // total_size)
                            progress_callback(percent, downloaded, total_size, "")
                
                # Check that file is non-empty
                if os.path.getsize(zip_path) > 0:
                    print(f"[OK] Revision {version} downloaded successfully! ({attempt_name})")
                    return True
                else:
                    os.remove(zip_path)
                    continue
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # This URL format does not exist for this build, try next
                continue
            print(f"HTTP Error ({e.code}) version {version}, format: {attempt_name}")
            continue
        except Exception:
            # Ignore and try next format
            continue

    # All formats failed
    return False


def download_chromium(version, progress_callback=None):
    """
    Download the Chromium ZIP archive for a given version.
    Falls back to older revisions and alternative sources if needed.
    """
    # Ensure cache directory exists
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    zip_path = os.path.join(CACHE_DIR, f"chrome-{CHROMIUM_TYPE}-{version}.zip")
    
    # Reuse cached zip if it already exists
    if os.path.isfile(zip_path):
        print(f"Using cached archive: {zip_path}")
        if progress_callback:
            progress_callback(100, 0, 0, "Using cached archive...")
        return zip_path
    
    # Try primary URL formats for this version (DIRECT download, no version iteration)
    if progress_callback:
        progress_callback(0, 0, 0, f"Downloading Chromium revision {version}...")
    
    if try_download_version(version, zip_path, progress_callback):
        print(f"Download successful: {zip_path}")
        return zip_path
    
    # If primary source failed, try alternative source (download-chromium.appspot.com)
    print("Primary source failed, trying alternative source (download-chromium.appspot.com)...")
    debug_log("Trying alternative Chromium source (download-chromium.appspot.com)...")
    alt_result = try_alternative_chromium_source(progress_callback)
    if alt_result:
        debug_log(f"Alternative source successful: {alt_result}")
        return alt_result
    
    # If both failed, return None (no version iteration)
    error_msg = "Chromium could not be downloaded from primary or alternative sources!"
    print(error_msg)
    debug_log(error_msg)
    return None


def try_alternative_chromium_source(progress_callback=None):
    """
    Try alternative Chromium sources (e.g. download-chromium.appspot.com).
    """
    # Alternative sources list
    alternative_sources = [
        {
            "name": "Chromium Download (download-chromium.appspot.com)",
            "url": "https://download-chromium.appspot.com/dl/Win_x64?type=snapshots",
            "method": "download_chromium_appspot"
        },
        # Other alternative sources can be added here
    ]
    
    for source in alternative_sources:
        if progress_callback:
            progress_callback(0, 0, 0, f"Trying alternative source: {source['name']}...")
        
        print(f"Trying alternative source: {source['name']}...")
        
        # Special handling for download-chromium.appspot.com
        if source["method"] == "download_chromium_appspot":
            zip_path = try_download_chromium_appspot(progress_callback)
            if zip_path:
                return zip_path
    
    return None


def try_download_chromium_appspot(progress_callback=None):
    """
    Try to download Chromium from download-chromium.appspot.com.
    This endpoint automatically serves the latest Windows build.
    """
    try:
        # Use download-chromium.appspot.com API
        download_url = "https://download-chromium.appspot.com/dl/Win_x64?type=snapshots"
        
        zip_path = os.path.join(CACHE_DIR, "chrome-win32-appspot.zip")
        
        if progress_callback:
            progress_callback(0, 0, 0, "Downloading Chromium (alternative source)...")
        
        req = urllib.request.Request(download_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            if response.status != 200:
                print(f"Alternative source failed: HTTP {response.status}")
                return None
            
            total_size = int(response.headers.get('Content-Length', 0))
            
            if progress_callback:
                progress_callback(5, 0, total_size, "Downloading Chromium (alternative source)...")
            
            print("[OK] Downloading from alternative source...")
            
            # Streaming download
            downloaded = 0
            with open(zip_path, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback and total_size > 0:
                        percent = min(100, (downloaded * 100) // total_size)
                        progress_callback(percent, downloaded, total_size, "")
            
            if os.path.getsize(zip_path) > 0:
                print(f"[OK] Alternative source download successful: {zip_path}")
                return zip_path
            else:
                os.remove(zip_path)
                return None
                
    except Exception as e:
        print(f"Alternative source download error: {e}")
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except:
                pass
        return None


def extract_chromium(zip_path, progress_callback=None):
    """
    Extract the Chromium ZIP and copy chrome.exe (and its DLLs) into bin/.
    """
    extract_dir = os.path.join(CACHE_DIR, "extract")
    chrome_exe_source = os.path.join(extract_dir, "chrome-win32", "chrome.exe")
    chrome_exe_target = os.path.join(BIN_DIR, "chrome.exe")
    
    try:
        # If Chromium is already installed, skip
        if os.path.isfile(chrome_exe_target):
            print(f"Chromium already installed: {chrome_exe_target}")
            return chrome_exe_target
        
        # Clean old extract dir
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
        os.makedirs(extract_dir, exist_ok=True)
        os.makedirs(BIN_DIR, exist_ok=True)
        
        print(f"Extracting ZIP: {zip_path}")
        
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            total_files = len(zip_ref.namelist())
            extracted = 0
            
            for member in zip_ref.namelist():
                zip_ref.extract(member, extract_dir)
                extracted += 1
                if progress_callback:
                    percent = (extracted * 100) // total_files
                    progress_callback(percent, extracted, total_files, "")
        
        # Copy chrome.exe into bin/
        # Support different ZIP layouts (chrome-win, chrome-win32, chromium, etc.)
        possible_chrome_paths = [
            os.path.join(extract_dir, "chrome-win", "chrome.exe"),      # chrome-win.zip için
            os.path.join(extract_dir, "chrome-win32", "chrome.exe"),    # chrome-win32.zip için
            os.path.join(extract_dir, "chromium", "chrome.exe"),
            os.path.join(extract_dir, "chrome.exe"),  # Doğrudan kök dizinde
        ]
        
        chrome_exe_source = None
        chrome_base_dir = None
        
        for path in possible_chrome_paths:
            if os.path.isfile(path):
                chrome_exe_source = path
                chrome_base_dir = os.path.dirname(path)
                print(f"Found chrome.exe: {chrome_exe_source}")
                break
        
        if chrome_exe_source and chrome_base_dir:
            print(f"Copying chrome.exe: {chrome_exe_source} -> {chrome_exe_target}")
            shutil.copy2(chrome_exe_source, chrome_exe_target)
            
            # Copy sibling files and folders (DLLs, resources, etc.)
            for item in os.listdir(chrome_base_dir):
                src = os.path.join(chrome_base_dir, item)
                dst = os.path.join(BIN_DIR, item)
                
                # chrome.exe already copied
                if item == "chrome.exe":
                    continue
                    
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                elif os.path.isfile(src):
                    shutil.copy2(src, dst)
            
            print(f"Chromium installation complete: {chrome_exe_target}")
            return chrome_exe_target
        else:
            # List ZIP contents (debug)
            print("ZIP contents:")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for name in zip_ref.namelist()[:20]:  # İlk 20 dosyayı göster
                    print(f"  - {name}")
            raise FileNotFoundError("chrome.exe not found inside the archive. See ZIP contents above.")
            
    except Exception as e:
        print(f"Extraction error: {e}")
        return None


def ensure_chrome_executable(progress_callback=None):
    """
    Locate Chrome/Chromium or automatically download and install it.
    Autochrome logic: first reuse existing Burp Chromium if available, otherwise install local copy.
    """
    # 1. Look inside Burp Suite directories under LOCALAPPDATA
    localappdata = os.getenv("LOCALAPPDATA", "")
    if localappdata:
        burp_patterns = [
            os.path.join(localappdata, "PortSwigger", "Burp Suite Professional", "**", "chrome.exe"),
            os.path.join(localappdata, "PortSwigger", "Burp Suite Community Edition", "**", "chrome.exe"),
            os.path.join(localappdata, "PortSwigger", "*", "**", "chrome.exe"),
        ]
        
        for pattern in burp_patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                chrome_path = matches[0]
                if os.path.isfile(chrome_path):
                    print(f"Burp Suite'ten bulundu: {chrome_path}")
                    return chrome_path
    
    # 2. Check ./bin/chrome.exe
    bin_chrome = os.path.join(BIN_DIR, "chrome.exe")
    if os.path.isfile(bin_chrome):
        print(f"Local installation found: {bin_chrome}")
        return bin_chrome
    
    # 3. Look for Burp Suite under Program Files
    program_files = os.getenv("ProgramFiles", "")
    if program_files:
        burp_patterns = [
            os.path.join(program_files, "PortSwigger", "Burp Suite Professional", "**", "chrome.exe"),
            os.path.join(program_files, "PortSwigger", "Burp Suite Community Edition", "**", "chrome.exe"),
        ]
        
        for pattern in burp_patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                chrome_path = matches[0]
                if os.path.isfile(chrome_path):
                    print(f"Program Files'tan bulundu: {chrome_path}")
                    return chrome_path
    
    # 4. If still not found, download and install Chromium
    print("Chromium not found, starting automatic download...")
    debug_log("Starting Chromium download...")
    
    if progress_callback:
        progress_callback(0, 0, 0, "Checking latest Chromium revision...")
    
    debug_log("Fetching latest Chromium version...")
    version = get_latest_chromium_version()
    if not version:
        error_msg = "Could not fetch Chromium revision!"
        print(error_msg)
        debug_log(error_msg)
        return None
    
    debug_log(f"Latest Chromium version: {version}")
    if progress_callback:
        progress_callback(5, 0, 0, f"Revision {version} found, downloading...")
    
    def download_progress(p, d, t, s=""):
        if progress_callback:
            overall_p = 5 + int(p * 0.6)
            status = s or f"Downloading: {p}%"
            progress_callback(overall_p, d, t, status)
        # Also log to debug
        if p % 10 == 0:
            debug_log(f"Download progress: {p}% - {s}")
    
    debug_log(f"Starting download for version {version}...")
    zip_path = download_chromium(version, download_progress if progress_callback else None)
    
    if not zip_path:
        error_msg = "Chromium download failed!"
        print(error_msg)
        debug_log(error_msg)
        return None
    
    debug_log(f"Download completed: {zip_path}")
    if progress_callback:
        progress_callback(65, 0, 0, "Installing Chromium...")
    
    def extract_progress(p, d, t, s=""):
        if progress_callback:
            overall_p = 65 + int(p * 0.35)
            status = s or f"Installing: {p}%"
            progress_callback(overall_p, d, t, status)
        # Also log to debug
        if p % 10 == 0:
            debug_log(f"Extraction progress: {p}% - {s}")
    
    debug_log("Extracting Chromium...")
    chrome_exe = extract_chromium(zip_path, extract_progress if progress_callback else None)
    
    if chrome_exe and os.path.isfile(chrome_exe):
        debug_log(f"Chromium installation completed: {chrome_exe}")
        if progress_callback:
            progress_callback(100, 0, 0, "Installation complete!")
            # Print newline after progress updates
            print()  # New line after progress updates
        return chrome_exe
    
    error_msg = "Chromium extraction failed!"
    debug_log(error_msg)
    return None


def hex_to_hsv(hex_color: str) -> float:
    """
    Convert hex color string to HSV hue in range [0.0, 1.0].
    Used by the Autochrome theme system.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return 0.0
    
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    delta = max_val - min_val
    
    if delta == 0:
        return 0.0
    
    if max_val == r:
        hue = ((g - b) / delta) % 6
    elif max_val == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4
    
    hue = hue / 6.0
    return hue


def get_extension_id_from_pub(pub_path: str) -> str:
    """
    Compute Chromium extension ID from a .pub file (Autochrome logic).
    Take first 32 chars of SHA256(pubkey) and map 0-9a-f -> a-p.
    """
    import hashlib
    try:
        with open(pub_path, "rb") as f:
            key_data = f.read()
        hash_hex = hashlib.sha256(key_data).hexdigest()[:32]
        # 0-9a-f -> a-p mapping (from Autochrome)
        extension_id = hash_hex.translate(str.maketrans("0123456789abcdef", "abcdefghijklmnop"))
        return extension_id
    except Exception as e:
        print(f"Extension ID calculation error: {e}")
        return None


def get_extension_version_from_crx(crx_path: str) -> str:
    """
    Read extension version from CRX manifest (Autochrome logic).
    """
    try:
        import zipfile
        with zipfile.ZipFile(crx_path, 'r') as zip_ref:
            manifest_data = zip_ref.read('manifest.json')
            manifest = json.loads(manifest_data.decode('utf-8'))
            version = manifest.get('version', '1.0')
            return version
    except Exception as e:
        debug_log(f"[ERROR] Failed to read extension version from CRX: {e}")
        return "1.0"  # Default version


def create_theme_extension(profile_path: str, profile_name: str, hex_color: str):
    """
    Create the theme extension for a profile (Autochrome logic - External Extensions).
    Uses prebuilt .crx files and writes External Extensions JSON alongside them.
    """
    debug_log(f"\n[DEBUG] create_theme_extension called:")
    debug_log(f"  - profile_path: {profile_path}")
    debug_log(f"  - profile_name: {profile_name}")
    debug_log(f"  - hex_color: {hex_color}")
    
    # Path to Autochrome theme CRX/PUB files
    autochrome_themes_dir = os.path.join(os.path.dirname(BASE_DIR), "autochrome-master", "data", "themes")
    debug_log(f"  - autochrome_themes_dir: {autochrome_themes_dir}")
    
    # Locate theme files
    crx_path = os.path.join(autochrome_themes_dir, f"{profile_name}.crx")
    pub_path = os.path.join(autochrome_themes_dir, f"{profile_name}.pub")
    
    debug_log(f"  - crx_path: {crx_path}")
    debug_log(f"  - pub_path: {pub_path}")
    debug_log(f"  - crx_path exists: {os.path.exists(crx_path)}")
    debug_log(f"  - pub_path exists: {os.path.exists(pub_path)}")
    
    if not os.path.exists(crx_path) or not os.path.exists(pub_path):
        debug_log("[ERROR] Theme CRX/PUB files not found!")
        return None
    
    # Compute extension ID from .pub
    extension_id = get_extension_id_from_pub(pub_path)
    if not extension_id:
        debug_log("[ERROR] Failed to compute extension ID!")
        return None
    
    debug_log(f"  - Extension ID: {extension_id}")
    
    # Create External Extensions folder under PROFILES_DIR (Autochrome layout)
    # In Autochrome, "External Extensions" lives at @install_dir/External Extensions
    external_extensions_dir = os.path.join(PROFILES_DIR, "External Extensions")
    os.makedirs(external_extensions_dir, exist_ok=True)
    
    # Copy .crx into that folder
    final_crx_path = os.path.join(external_extensions_dir, f"{extension_id}.crx")
    final_crx_path_abs = os.path.abspath(final_crx_path)
    
    try:
        shutil.copy2(crx_path, final_crx_path)
        debug_log(f"[OK] Copied theme CRX: {final_crx_path_abs}")
    except Exception as e:
        debug_log(f"[ERROR] Failed to copy theme CRX: {e}")
        import traceback
        debug_log(traceback.format_exc())
        return None
    
    # Read extension version from CRX (Autochrome logic)
    extension_version = get_extension_version_from_crx(crx_path)
    debug_log(f"  - Extension Version: {extension_version}")
    
    # NOTE: native Chromium profile picker runs in "System Profile" on Windows.
    # Forcing themes/extensions into that window is not reliable, so we do NOT
    # unpack themes globally for picker.
    
    # Create External Extensions JSON (Autochrome format, absolute path with forward slashes)
    json_path = os.path.join(external_extensions_dir, f"{extension_id}.json")
    try:
        # Normalize path for Windows (backslashes -> forward slashes)
        final_crx_path_for_json = final_crx_path_abs.replace('\\', '/')
        
        json_data = {
            "external_crx": final_crx_path_for_json,  # Absolute path with forward slashes
            "external_version": extension_version,    # Version from CRX manifest
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        debug_log(f"[OK] External Extensions JSON created: {json_path}")
        debug_log(f"  - Extension ID: {extension_id}")
        debug_log(f"  - Extension Version: {extension_version}")
        debug_log(f"  - CRX Path (JSON): {final_crx_path_for_json}")
        return extension_id
    except Exception as e:
        debug_log(f"[ERROR] Failed to write External Extensions JSON: {e}")
        import traceback
        debug_log(traceback.format_exc())
        return None


def create_profile_preferences(profile_path: str, profile_name: str):
    """
    Create Chromium profile Preferences and Secure Preferences (Autochrome logic).
    Sets avatar icon, theme, and baseline privacy / security options.
    """
    preferences_path = os.path.join(profile_path, "Preferences")
    
    # Load existing Preferences if present
    prefs = {}
    if os.path.exists(preferences_path):
        try:
            with open(preferences_path, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
        except Exception as e:
            print(f"Preferences file could not be read, creating new one: {e}")
            prefs = {}
    
    # Ensure "profile" dictionary
    if "profile" not in prefs:
        prefs["profile"] = {}
    
    # Set avatar icon if mapping exists
    if profile_name in AVATAR_ICONS:
        prefs["profile"]["name"] = profile_name
        prefs["profile"]["avatar_icon"] = AVATAR_ICONS[profile_name]
        print(f"Profile avatar icon set: {AVATAR_ICONS[profile_name]}")
    
    # Create and wire up theme extension
    debug_log(f"\n[DEBUG] Creating theme extension for profile: {profile_name}")
    extension_id = None
    if profile_name in PROFILE_COLOR_MAP:
        hex_color = PROFILE_COLOR_MAP[profile_name]
        debug_log(f"[DEBUG] Profile color: {hex_color}")
        extension_id = create_theme_extension(profile_path, profile_name, hex_color)
        debug_log(f"[DEBUG] Extension ID returned: {extension_id}")
    else:
        debug_log(f"[DEBUG] Profile name not in PROFILE_COLOR_MAP: {profile_name}")
    
    if extension_id:
        # Attach theme extension into Preferences (Autochrome format)
        if "extensions" not in prefs:
            prefs["extensions"] = {}
        
        # Theme entry (Autochrome format - just id)
        prefs["extensions"]["theme"] = {
            "id": extension_id
        }
        
        # Add extension into install_time list
        if "install_time" not in prefs["extensions"]:
            prefs["extensions"]["install_time"] = {}
        prefs["extensions"]["install_time"][extension_id] = str(int(time.time() * 1000000))
        
        # Add extension into settings (so Chromium recognizes it)
        if "settings" not in prefs["extensions"]:
            prefs["extensions"]["settings"] = {}
        prefs["extensions"]["settings"][extension_id] = {
            "creation_flags": 1,
            "initialized": True,
            "location": 4,  # EXTERNAL_PREF
            "state": 1,  # ENABLED
        }
        
        debug_log(f"[OK] Theme extension added to Preferences: {extension_id}")
        debug_log(f"  - Preferences['extensions']['theme']['id'] = {extension_id}")
        debug_log(f"  - Preferences['extensions']['settings'][{extension_id}] added")
    
    # Baseline Autochrome privacy / security settings
    if "autofill" not in prefs:
        prefs["autofill"] = {"enabled": False}
    
    if "safebrowsing" not in prefs:
        prefs["safebrowsing"] = {
            "enabled": False,
            "extended_reporting_enabled": False,
            "scout_reporting_enabled": False
        }
    
    if "translate" not in prefs:
        prefs["translate"] = {"enabled": False}
    
    if "search" not in prefs:
        prefs["search"] = {"suggest_enabled": False}
    
    # Write Preferences back to disk
    try:
        with open(preferences_path, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
        debug_log(f"[OK] Preferences written: {preferences_path}")
        if extension_id and "extensions" in prefs and "theme" in prefs["extensions"]:
            debug_log(f"  - Theme ID: {prefs['extensions']['theme'].get('id', 'MISSING!')}")
    except Exception as e:
        debug_log(f"[ERROR] Failed to write Preferences: {e}")
        import traceback
        debug_log(traceback.format_exc())
    
    # Create / update Secure Preferences (for extensions)
    secure_prefs_path = os.path.join(profile_path, "Secure Preferences")
    secure_prefs = {}
    if os.path.exists(secure_prefs_path):
        try:
            with open(secure_prefs_path, 'r', encoding='utf-8') as f:
                secure_prefs = json.load(f)
        except:
            secure_prefs = {}
    
    # Add extension state into Secure Preferences (External Extensions - Autochrome format)
    if extension_id:
        if "extensions" not in secure_prefs:
            secure_prefs["extensions"] = {}
        if "settings" not in secure_prefs["extensions"]:
            secure_prefs["extensions"]["settings"] = {}
        
        # Add extension settings (External Extensions - Autochrome format)
        # Autochrome uses ack_external: true; on Windows, state:1 and location:4 also help.
        # We additionally embed the manifest and path so Chromium can recognize the unpacked theme.
        try:
            import zipfile
            crx_path = os.path.join(os.path.dirname(BASE_DIR), "autochrome-master", "data", "themes", f"{profile_name}.crx")
            with zipfile.ZipFile(crx_path, 'r') as zip_ref:
                manifest_data = zip_ref.read('manifest.json')
                manifest = json.loads(manifest_data.decode('utf-8'))
            
            # Unpack CRX so Chromium can treat it as an unpacked extension
            extension_version = manifest.get('version', '1.0')
            extension_dir = os.path.join(profile_path, "Extensions", extension_id, extension_version)
            os.makedirs(extension_dir, exist_ok=True)
            
            # CRX'i extract et
            with zipfile.ZipFile(crx_path, 'r') as zip_ref:
                zip_ref.extractall(extension_dir)
            
            debug_log(f"[OK] Theme extension unpacked: {extension_dir}")
            
            # Extension path in forward-slash form
            extension_path = os.path.abspath(extension_dir).replace('\\', '/')
            
            secure_prefs["extensions"]["settings"][extension_id] = {
                "ack_external": True,  # External extension acknowledgement
                "state": 1,            # ENABLED
                "location": 4,         # EXTERNAL_PREF
                "manifest": manifest,  # Manifest so Chromium can validate the extension
                "path": extension_path # Unpacked extension path
            }
        except Exception as e:
            debug_log(f"[ERROR] Manifest read / extract error: {e}")
            import traceback
            debug_log(traceback.format_exc())
            # If manifest cannot be read, fall back to minimal settings
            secure_prefs["extensions"]["settings"][extension_id] = {
                "ack_external": True,
                "state": 1,
                "location": 4
            }
        
        try:
            # On Windows, HMAC signatures might not be strictly required in our case,
            # but Chromium may still validate consistency. We just write JSON here.
            with open(secure_prefs_path, 'w', encoding='utf-8') as f:
                json.dump(secure_prefs, f, indent=2, ensure_ascii=False, sort_keys=True)
            debug_log(f"[OK] Secure Preferences written: {secure_prefs_path}")
            debug_log(f"  - Extension ID: {extension_id}")
            debug_log(f"  - ack_external: {secure_prefs['extensions']['settings'][extension_id].get('ack_external', False)}")
            debug_log(f"  - state: {secure_prefs['extensions']['settings'][extension_id].get('state', 0)}")
            debug_log(f"  - location: {secure_prefs['extensions']['settings'][extension_id].get('location', 0)}")
            if 'manifest' in secure_prefs['extensions']['settings'][extension_id]:
                debug_log("  - manifest: PRESENT")
        except Exception as e:
            debug_log(f"[ERROR] Failed to write Secure Preferences: {e}")
            import traceback
            debug_log(traceback.format_exc())


def setup_all_profiles():
    """
    Creates all profiles and prepares the Local State file.
    For use with Chromium's profile picker screen.
    """
    # Create all profiles
    profile_entries = {}
    
    for idx, (profile_name, _) in enumerate(PROFILES):
        dir_name = CHROME_DIRS[idx] if idx < len(CHROME_DIRS) else profile_name
        # Profile directory in Chromium format: Default, Profile 1, Profile 2...
        profile_path = os.path.join(PROFILES_DIR, dir_name)
        os.makedirs(profile_path, exist_ok=True)
        
        # Create Preferences for each profile
        create_profile_preferences(profile_path, profile_name)
        
        # Create profile entry (for Local State)
        entry = {"name": profile_name}
        if profile_name in AVATAR_ICONS:
            entry["avatar_icon"] = AVATAR_ICONS[profile_name]
        profile_entries[dir_name] = entry
        
        debug_log(f"Profile created: {dir_name} ({profile_name})")
    
    # Create Local State file (with all profiles)
    local_state_path = os.path.join(PROFILES_DIR, "Local State")
    local_state = {
        "browser": {
            "confirm_to_quit": True,
            "enabled_labs_experiments": [
                "enable-brotli@2",
                "show-cert-link"
            ]
        },
        "network_time": {
            "network_time_queries_enabled": False
        },
        "profile": {
            "info_cache": profile_entries,
            "last_used": list(profile_entries.keys())[0] if profile_entries else None
        }
    }
    
    try:
        with open(local_state_path, 'w', encoding='utf-8') as f:
            json.dump(local_state, f, indent=2, ensure_ascii=False)
        debug_log(f"Local State file created: {local_state_path}")
        debug_log(f"  - Profile count: {len(profile_entries)}")
    except Exception as e:
        debug_log(f"Failed to create Local State file: {e}")
        import traceback
        debug_log(traceback.format_exc())


def build_chrome_command(chrome_path: str):
    """
    Creates Chromium launch command (with all profiles).
    Uses Chromium's native profile picker screen.
    """
    # Create all profiles
    setup_all_profiles()
    
    # Use profile directory as absolute path (for Windows)
    profile_path_abs = os.path.abspath(PROFILES_DIR)
    
    # Autochrome environment spoofing
    env = os.environ.copy()
    env["GOOGLE_API_KEY"] = "invalid"
    env["GOOGLE_DEFAULT_CLIENT_ID"] = "invalid"
    env["GOOGLE_DEFAULT_CLIENT_SECRET"] = "invalid"
    
    # Autochrome flag'leri (analiz raporundan)
    flags = [
        "--ignore-certificate-errors",
        "--disable-xss-auditor",
        "--no-default-browser-check",
        "--no-first-run",
        "--disable-background-networking",
        "--disable-client-side-phishing-detection",
        "--disable-component-update",
        "--disable-sync",
        "--disable-translate",
        "--safebrowsing-disable-auto-update",
        "--safebrowsing-disable-download-protection",
        "--proxy-server=127.0.0.1:8080",
        f'--user-data-dir={profile_path_abs}',  # All profiles under this directory
    ]

    # NOTE: do not force-load extensions for native picker on Windows.

    # Chromium debug logging (helps diagnose why themes/extensions aren't applied)
    # Writes inside PROFILES_DIR so it's always writable.
    log_file = os.path.join(profile_path_abs, "chromium.log")
    flags += [
        "--enable-logging",
        "--v=1",
        f'--log-file={log_file}',
    ]
    
    cmd = [chrome_path] + flags
    return cmd, env


def build_chrome_command_for_profile(chrome_path: str, profile_name: str):
    """
    Launch a *specific* profile and force-load its theme via --load-extension.
    This is the most reliable way on Windows to guarantee the colored top frame.
    """
    setup_all_profiles()

    # profile_name arg can be: color name ("Red") or chromium dir name ("Profile 1")
    def map_profile_arg(pname: str):
        # Is it a color name?
        if pname in COLOR_ORDER:
            idx = COLOR_ORDER.index(pname)
            dir_name = CHROME_DIRS[idx] if idx < len(CHROME_DIRS) else pname
            display_name = pname
            return dir_name, display_name
        # Is it a chromium dir name?
        if pname in CHROME_DIRS:
            idx = CHROME_DIRS.index(pname)
            display_name = COLOR_ORDER[idx] if idx < len(COLOR_ORDER) else pname
            return pname, display_name
        # fallback
        return pname, pname

    dir_name, display_name = map_profile_arg(profile_name)
    profile_name = display_name

    # Materialize a Chrome-friendly profile layout:
    # user-data-dir = profiles/<ProfileName>/
    # actual profile dir = profiles/<ProfileName>/Default/
    profile_root = os.path.abspath(os.path.join(PROFILES_DIR, dir_name))
    profile_dir_abs = os.path.join(profile_root, "Default")
    os.makedirs(profile_dir_abs, exist_ok=True)

    # Ensure Preferences / Secure Preferences / Extensions live under Default/
    def _copy_if_exists(src, dst):
        if os.path.exists(src) and os.path.isfile(src):
            shutil.copy2(src, dst)
    _copy_if_exists(os.path.join(PROFILES_DIR, profile_name, "Preferences"),
                    os.path.join(profile_dir_abs, "Preferences"))
    _copy_if_exists(os.path.join(PROFILES_DIR, profile_name, "Secure Preferences"),
                    os.path.join(profile_dir_abs, "Secure Preferences"))
    # copy Extensions tree if present
    src_ext = os.path.join(PROFILES_DIR, profile_name, "Extensions")
    dst_ext = os.path.join(profile_dir_abs, "Extensions")
    if os.path.isdir(src_ext):
        if os.path.isdir(dst_ext):
            shutil.rmtree(dst_ext, ignore_errors=True)
        shutil.copytree(src_ext, dst_ext)

    env = os.environ.copy()
    env["GOOGLE_API_KEY"] = "invalid"
    env["GOOGLE_DEFAULT_CLIENT_ID"] = "invalid"
    env["GOOGLE_DEFAULT_CLIENT_SECRET"] = "invalid"

    # Determine extension dir from that profile's Preferences
    prefs_path = os.path.join(profile_dir_abs, "Preferences")
    prefs = _safe_read_json(prefs_path) or {}
    theme_id = (prefs.get("extensions", {}).get("theme", {}) or {}).get("id")
    if not theme_id:
        raise RuntimeError(f"Theme ID not found: {profile_name}")

    # We always unpack to: profiles/<Profile>/Extensions/<id>/1.1/
    # (version is in CRX manifest; default is 1.1 for autochrome themes)
    ext_dir = os.path.join(profile_dir_abs, "Extensions", theme_id, "1.1")
    if not os.path.isdir(ext_dir):
        # try to find any version directory
        base = os.path.join(profile_dir_abs, "Extensions", theme_id)
        if os.path.isdir(base):
            versions = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
            versions.sort(reverse=True)
            if versions:
                ext_dir = os.path.join(base, versions[0])
    if not os.path.isdir(ext_dir):
        raise RuntimeError(f"Theme extension directory not found: {ext_dir}")

    ext_dir_abs = os.path.abspath(ext_dir)
    ext_dir_abs = ext_dir_abs.replace("\\", "/")  # safer for Chrome flags on Windows

    flags = [
        "--ignore-certificate-errors",
        "--disable-xss-auditor",
        "--no-default-browser-check",
        "--no-first-run",
        "--disable-background-networking",
        "--disable-client-side-phishing-detection",
        "--disable-component-update",
        "--disable-sync",
        "--disable-translate",
        "--safebrowsing-disable-auto-update",
        "--safebrowsing-disable-download-protection",
        "--proxy-server=127.0.0.1:8080",
        f'--user-data-dir={profile_root}',
        # Force-load theme extension for this profile (Default)
        f'--load-extension={ext_dir_abs}',
        "--profile-directory=Default",
    ]

    log_file = os.path.join(profile_root, f"chromium-{profile_name}.log")
    flags += [
        "--enable-logging",
        "--v=1",
        f'--log-file={log_file}',
    ]

    cmd = [chrome_path] + flags
    return cmd, env


def _safe_read_json(path: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        debug_log(f"[POSTCHECK] JSON okunamadı: {path} -> {e}")
        return None


def postcheck_profiles_state():
    """
    After launching Chromium, check whether it created/modified profile dirs and whether
    our theme prefs survived. This is crucial on Windows where Chromium may reset prefs.
    """
    try:
        base = os.path.abspath(PROFILES_DIR)
        debug_log(f"[POSTCHECK] base={base}")
        if not os.path.exists(base):
            debug_log("[POSTCHECK] profiles dir not found")
            return

        # list top-level dirs (helps detect if Chromium created 'Default' / 'Profile 1' etc)
        top = []
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if os.path.isdir(p):
                top.append(name)
        debug_log(f"[POSTCHECK] top-level dirs: {top}")

        # inspect each Autochrome profile dir
        for profile_name, _ in PROFILES:
            pdir = os.path.join(base, profile_name)
            prefs = _safe_read_json(os.path.join(pdir, "Preferences")) or {}
            sprefs = _safe_read_json(os.path.join(pdir, "Secure Preferences")) or {}

            theme_id = (
                prefs.get("extensions", {})
                .get("theme", {})
                .get("id")
            )
            has_secure_setting = False
            try:
                has_secure_setting = (
                    sprefs.get("extensions", {})
                    .get("settings", {})
                    .get(theme_id or "", {})
                    .get("ack_external") is True
                )
            except Exception:
                has_secure_setting = False

            debug_log(
                f"[POSTCHECK] {profile_name}: theme_id={theme_id} secure_ack={has_secure_setting} "
                f"prefs_keys={list(prefs.keys())[:10]} sprefs_keys={list(sprefs.keys())[:10]}"
            )
    except Exception as e:
        import traceback
        debug_log(f"[POSTCHECK] Error: {e}\n{traceback.format_exc()}")


def launch_chrome(chrome_path: str, root: ctk.CTk):
    """
    Launches Chromium (with all profiles).
    Shows Chromium's native profile picker screen.
    """
    cmd, env = build_chrome_command(chrome_path)
    
    try:
        # Launch Chromium as detached process (no console window)
        process = subprocess.Popen(
            cmd,
            env=env,
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        print(f"Chromium started (PID: {process.pid})")
        print(f"Command: {' '.join(cmd)}")
        
        # Close launcher immediately (100ms wait removed)
        try:
            root.quit()
        except:
            pass
        try:
            root.destroy()
        except:
            pass
        
        # Exit after process is started
        sys.exit(0)
        
    except Exception as e:
        import traceback
        error_msg = f"Failed to launch Chromium:\n{str(e)}\n\n"
        error_msg += f"Command: {' '.join(cmd)}\n\n"
        error_msg += f"Traceback:\n{traceback.format_exc()}"
        print(error_msg)
        messagebox.showerror("Launch Error", error_msg)
        raise


class ProfileCard(ctk.CTkFrame):
    """
    Tek bir profil kartı widget'ı.
    Similar to Chromium's profile picker cards.
    """
    
    def __init__(self, parent, profile_name: str, color: str, callback):
        super().__init__(parent, fg_color="transparent")
        
        self.profile_name = profile_name
        self.color = color
        self.callback = callback
        self.is_hovered = False
        
        # Avatar (renkli daire)
        self.avatar_frame = ctk.CTkFrame(
            self,
            width=80,
            height=80,
            corner_radius=40,
            fg_color=color,
            border_width=0,
        )
        self.avatar_frame.pack(pady=(0, 8))
        
        # Profil ismi
        self.name_label = ctk.CTkLabel(
            self,
            text=profile_name,
            font=ctk.CTkFont(size=13, weight="normal"),
            text_color=("gray80", "gray70"),
        )
        self.name_label.pack()
        
        # Event bindings
        self.avatar_frame.bind("<Button-1>", self._on_click)
        self.avatar_frame.bind("<Enter>", self._on_enter)
        self.avatar_frame.bind("<Leave>", self._on_leave)
        self.name_label.bind("<Button-1>", self._on_click)
        self.name_label.bind("<Enter>", self._on_enter)
        self.name_label.bind("<Leave>", self._on_leave)
        
        # Widget'ları da tıklanabilir yap
        for widget in [self.avatar_frame, self.name_label]:
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
    
    def _on_click(self, event):
        """Kart tıklandığında callback'i çağır."""
        self.callback(self.profile_name)
    
    def _on_enter(self, event):
        """Mouse kartın üzerine geldiğinde hover efekti."""
        if not self.is_hovered:
            self.is_hovered = True
            # Avatar'ı biraz büyüt ve parlaklaştır
            hover_color = self._brighten_color(self.color, 0.15)
            self.avatar_frame.configure(fg_color=hover_color)
            self.avatar_frame.configure(width=85, height=85)
            self.name_label.configure(text_color=("white", "white"))
    
    def _on_leave(self, event):
        """Mouse karttan ayrıldığında normal haline dön."""
        if self.is_hovered:
            self.is_hovered = False
            self.avatar_frame.configure(fg_color=self.color)
            self.avatar_frame.configure(width=80, height=80)
            self.name_label.configure(text_color=("gray80", "gray70"))
    
    def _brighten_color(self, hex_color: str, factor: float) -> str:
        """Rengi parlaklaştırır."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return "#" + hex_color
        
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        return "#{:02x}{:02x}{:02x}".format(r, g, b)


class ProgressDialog(ctk.CTk):
    """Progress dialog for Chromium download / installation."""
    
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.progress_value = 0
        self.status_text = ""
        
        # For throttling
        self._last_update_time = 0
        self._update_interval = 0.1  # update at most every 100ms
        self._pending_update = None
        
        self.title("Chromium Setup")
        self.geometry("500x200")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("dark")
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(pady=30, padx=40, fill="x")
        self.progress_bar.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Hazırlanıyor...",
            font=ctk.CTkFont(size=14),
        )
        self.status_label.pack(pady=10)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (200 // 2)
        self.geometry(f"500x200+{x}+{y}")
        
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
    
    def _schedule_update(self, percent, downloaded, total, status):
        """Thread-safe update scheduling with throttling."""
        import time
        current_time = time.time()
        
        # If enough time has passed or it's the first update
        if current_time - self._last_update_time >= self._update_interval or self._last_update_time == 0:
            self._last_update_time = current_time
            # Use after_idle (safer)
            try:
                self.after_idle(lambda: self.update_progress(percent, downloaded, total, status))
            except Exception as e:
                print(f"Schedule update error: {e}")
        else:
            # Store latest values and schedule a later update
            self._pending_update = (percent, downloaded, total, status)
            # Schedule next update
            remaining = self._update_interval - (current_time - self._last_update_time)
            try:
                self.after(int(remaining * 1000), lambda: self._process_pending_update())
            except Exception as e:
                print(f"Pending update schedule error: {e}")
    
    def _process_pending_update(self):
        """Process any pending throttled update."""
        if self._pending_update:
            percent, downloaded, total, status = self._pending_update
            self._pending_update = None
            self.update_progress(percent, downloaded, total, status)
    
    def update_progress(self, percent, downloaded=0, total=0, status=""):
        """Update progress bar and status label. Thread-safe and recursion-safe."""
        try:
            # Clamp percent into [0, 100]
            percent = max(0, min(100, percent))
            self.progress_value = percent / 100.0
            
            # Update progress bar (wrapped in try/except for safety)
            try:
                self.progress_bar.set(self.progress_value)
            except Exception as e:
                print(f"Progress bar update error: {e}")
            
            # Build status text
            if status:
                self.status_text = status
            elif total > 0:
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                self.status_text = f"Downloading... ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)"
            else:
                self.status_text = status or f"Processing... {percent}%"
            
            # Update status label
            try:
                self.status_label.configure(text=self.status_text)
            except Exception as e:
                print(f"Status label update error: {e}")
            
            # Use update_idletasks() instead of update() (safer)
            try:
                self.update_idletasks()
            except Exception as e:
                print(f"Update error: {e}")
        except Exception as e:
            print(f"update_progress error: {e}")


class AutochromeLauncher(ctk.CTk):
    """
    Main launcher window.
    Visually mimics Chromium's "Who is using Chromium?" profile picker.
    """
    
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("WindowsAutochrome")
        self.geometry("600x500")
        self.resizable(False, False)
        
        # Dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Locate or install Chromium
        self.chrome_path = None
        self._ensure_chrome()
        
        # Build UI
        self._create_ui()
        
        # Frameless window (Chromium-like) - after UI
        self.overrideredirect(True)
        
        # Center window on screen (after UI)
        self._center_window()
        
        # Bring window to front
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))
    
    def _ensure_chrome(self):
        """Find Chromium or automatically download / install it."""
        # First, try to reuse an existing installation quickly
        def simple_find():
            # Check Burp Suite bundles
            localappdata = os.getenv("LOCALAPPDATA", "")
            if localappdata:
                burp_patterns = [
                    os.path.join(localappdata, "PortSwigger", "Burp Suite Professional", "**", "chrome.exe"),
                    os.path.join(localappdata, "PortSwigger", "Burp Suite Community Edition", "**", "chrome.exe"),
                ]
                for pattern in burp_patterns:
                    matches = glob.glob(pattern, recursive=True)
                    if matches and os.path.isfile(matches[0]):
                        return matches[0]
            
            # Check bin/chrome.exe
            bin_chrome = os.path.join(BIN_DIR, "chrome.exe")
            if os.path.isfile(bin_chrome):
                return bin_chrome
            return None
        
        self.chrome_path = simple_find()
        
        # Not found -> run full ensure_chrome_executable with UI progress
        if not self.chrome_path:
            progress_dialog = ProgressDialog(self)
            progress_dialog.update()
            
            def download_thread():
                try:
                    def progress_callback(percent, downloaded, total, status=""):
                        # Thread-safe ve throttled update
                        progress_dialog._schedule_update(percent, downloaded, total, status)
                    
                    chrome_path = ensure_chrome_executable(progress_callback)
                    
                    # Başarılı olduğunda UI thread'inde çağır
                    try:
                        progress_dialog.after_idle(lambda: self._on_chrome_ready(chrome_path, progress_dialog))
                    except Exception as e:
                        print(f"on_chrome_ready schedule error: {e}")
                        # Alternatif: direkt çağır (eğer mainloop çalışmıyorsa)
                        self._on_chrome_ready(chrome_path, progress_dialog)
                except Exception as e:
                    # In case of error, call in UI thread
                    try:
                        progress_dialog.after_idle(lambda: self._on_chrome_error(str(e), progress_dialog))
                    except Exception as e2:
                        print(f"on_chrome_error schedule error: {e2}")
                        # Alternatif: direkt çağır
                        self._on_chrome_error(str(e), progress_dialog)
            
            threading.Thread(target=download_thread, daemon=True).start()
            progress_dialog.mainloop()
    
    def _on_chrome_ready(self, chrome_path, progress_dialog):
        """Called when Chromium is ready."""
        try:
            self.chrome_path = chrome_path
            
            if not chrome_path:
                # Detailed error and alternative instructions
                error_msg = (
                    "Chromium could not be downloaded automatically.\n\n"
                    "Alternative options:\n"
                    "1. Manual download:\n"
                    "   - Download Chromium from: https://download-chromium.appspot.com/\n"
                    "   - Extract the ZIP and copy chrome.exe into:\n"
                    f"   {BIN_DIR}\\chrome.exe\n\n"
                    "2. Use Burp Suite Chromium:\n"
                    "   - If Burp Suite Professional/Community Edition is installed,\n"
                    "   - this launcher can reuse Burp's bundled Chromium.\n\n"
                    "3. Retry:\n"
                    "   - Check your internet connection\n"
                    "   - Then restart WindowsAutochrome"
                )
                messagebox.showerror("Setup Error", error_msg)
            
            # Progress dialog'u kapat (quit daha güvenli)
            try:
                progress_dialog.quit()
            except:
                pass
            try:
                progress_dialog.destroy()
            except:
                pass
        except Exception as e:
            print(f"_on_chrome_ready error: {e}")
    
    def _on_chrome_error(self, error_msg, progress_dialog):
        """Handle Chromium download / installation error."""
        try:
            messagebox.showerror(
                "Setup Error",
                f"An error occurred during Chromium setup:\n\n{error_msg}"
            )
            
            # Progress dialog'u kapat (quit daha güvenli)
            try:
                progress_dialog.quit()
            except:
                pass
            try:
                progress_dialog.destroy()
            except:
                pass
        except Exception as e:
            print(f"_on_chrome_error error: {e}")
    
    def _center_window(self):
        """Center the window on the current screen."""
        self.update_idletasks()
        # Ensure we have a non-zero window size
        width = self.winfo_width() or 600
        height = self.winfo_height() or 500
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_ui(self):
        """Create all UI widgets."""
        # Main frame (dark background)
        main_frame = ctk.CTkFrame(
            self,
            fg_color=("#2B2B2B", "#1E1E1E"),  # Chromium'un koyu teması
            corner_radius=0,
        )
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Title label
        title_label = ctk.CTkLabel(
            main_frame,
            text="Who is using Autochrome?",
            font=ctk.CTkFont(size=24, weight="normal"),
            text_color=("white", "white"),
        )
        title_label.pack(pady=(40, 30))
        
        # Profile cards container (2 rows, 4 columns)
        cards_frame = ctk.CTkFrame(
            main_frame,
            fg_color="transparent",
        )
        cards_frame.pack(expand=True, fill="both", padx=40, pady=20)
        
        # Configure grid
        for col in range(4):
            cards_frame.grid_columnconfigure(col, weight=1)
        for row in range(2):
            cards_frame.grid_rowconfigure(row, weight=1)

        # Create 8 profile cards
        for idx, (pname, color) in enumerate(PROFILES):
            row = idx // 4
            col = idx % 4
            card = ProfileCard(
                cards_frame,
                profile_name=pname,
                color=color,
                callback=self._on_profile_selected,
            )
            card.grid(row=row, column=col, padx=16, pady=12)
        
        # Close button (top-right)
        close_button = ctk.CTkButton(
            main_frame,
            text="✕",
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color="#E81123",
            text_color=("gray70", "gray70"),
            font=ctk.CTkFont(size=16),
            command=self._on_close,
        )
        close_button.place(x=570, y=10)
        
        # Drag support
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._on_drag)
        self._drag_start_x = 0
        self._drag_start_y = 0
    
    def _start_drag(self, event):
        """Start dragging the borderless window."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y
    
    def _on_drag(self, event):
        """Update position while dragging."""
        x = self.winfo_x() + event.x - self._drag_start_x
        y = self.winfo_y() + event.y - self._drag_start_y
        self.geometry(f"+{x}+{y}")
    
    def _on_profile_selected(self, profile_name: str):
        """Called when a profile card is clicked; launches Chromium with that profile."""
        if hasattr(self, "_launching") and self._launching:
            return
        self._launching = True

        if not self.chrome_path:
            self._launching = False
            messagebox.showinfo(
                "Chromium Setup",
                "Chromium is not ready yet.\n\n"
                "Please wait until the installation finishes..."
            )
            return

        try:
            cmd, env = build_chrome_command_for_profile(self.chrome_path, profile_name)
            process = subprocess.Popen(
                cmd,
                env=env,
                creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"Chromium started (PID: {process.pid}) [Profile={profile_name}]")
            print(f"Command: {' '.join(cmd)}")
        
            # Close launcher window
            try:
                self.destroy()
            except Exception:
                pass
            sys.exit(0)

        except Exception as e:
            self._launching = False
            messagebox.showerror(
                "Chromium Launch Error",
                f"Could not launch profile '{profile_name}':\n{str(e)}"
            )
    
    def _launch_chromium(self):
        """Launch Chromium with all profiles (native picker)."""
        # Prevent double-launch
        if hasattr(self, '_launching') and self._launching:
            return
        self._launching = True
        
        if not self.chrome_path:
            self._launching = False
            messagebox.showinfo(
                "Chromium Setup",
                "Chromium is not ready yet.\n\n"
                "Please wait until the installation finishes..."
            )
            return
        
        # Launch Chromium with all profiles
        try:
            launch_chrome(self.chrome_path, self)
        except Exception as e:
            self._launching = False
            messagebox.showerror(
                "Chromium Launch Error",
                f"Could not launch Chromium:\n{str(e)}"
            )
    
    def _on_close(self):
        """Close launcher."""
        self.destroy()
        sys.exit(0)


def create_tray_icon():
    """Create system tray icon."""
    if not HAS_PYSTRAY:
        return None
    
    # Simple tray icon
    image = Image.new('RGB', (64, 64), color=(66, 133, 244))  # Chromium mavisi
    draw = ImageDraw.Draw(image)
    draw.ellipse([16, 16, 48, 48], fill=(255, 255, 255))
    
    # Profile selection / launcher entry
    def show_launcher(icon=None, item=None):
        """Show launcher window (as a new process)."""
        try:
            BASE_DIR = os.path.abspath(os.path.dirname(__file__))
            MAIN_PY = os.path.join(BASE_DIR, "main.py")
            PYTHON_EXE = sys.executable
            
            # On Windows, use shell=True
            if sys.platform == "win32":
                # Shell komutu ile başlat
                cmd = f'"{PYTHON_EXE}" "{MAIN_PY}"'
                subprocess.Popen(
                    cmd,
                    cwd=BASE_DIR,
                    shell=True,
                    # creationflags kaldırıldı - normal process olarak başlat
                )
            else:
                # For Linux/macOS
                subprocess.Popen(
                    [PYTHON_EXE, MAIN_PY],
                    cwd=BASE_DIR,
                )
                    
        except Exception as e:
            error_msg = f"Launcher error: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            
            # Persist error to a file for debugging
            try:
                error_log = os.path.join(os.path.abspath(os.path.dirname(__file__)), "tray_error.log")
                with open(error_log, 'a', encoding='utf-8') as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
                    f.write(traceback.format_exc())
            except:
                pass
    
    def quit_app(icon=None, item=None):
        """Exit the tray application."""
        if icon:
            icon.stop()
        os._exit(0)
    
    def launch_profile(profile_name: str):
        def _inner(icon=None, item=None):
            try:
                BASE_DIR = os.path.abspath(os.path.dirname(__file__))
                MAIN_PY = os.path.join(BASE_DIR, "main.py")
                PYTHON_EXE = sys.executable
                cmd = f'"{PYTHON_EXE}" "{MAIN_PY}" --profile "{profile_name}"'
                subprocess.Popen(cmd, cwd=BASE_DIR, shell=True)
            except Exception as e:
                debug_log(f"[TRAY] profile launch error {profile_name}: {e}")
        return _inner

    profile_items = [pystray.MenuItem(name, launch_profile(name)) for (name, _) in PROFILES]

    menu = pystray.Menu(
        pystray.MenuItem("Open (Profile Picker)", show_launcher),
        pystray.MenuItem("Profiles", pystray.Menu(*profile_items)),
        pystray.MenuItem("Quit", quit_app),
    )
    
    icon = pystray.Icon("Autochrome", image, "Autochrome Launcher", menu)
    return icon

def check_and_setup():
    """
    Check if this is the first run and perform initial setup if needed.
    Returns True if setup was completed (or already done), False on error.
    """
    INSTALLED_MARKER = os.path.join(BASE_DIR, ".installed")
    
    # If already installed, skip setup
    if os.path.exists(INSTALLED_MARKER):
        return True
    
    # First run: perform setup
    print("First run detected. Performing initial setup...")
    
    try:
        # 1. Ensure directory structure
        os.makedirs(PROFILES_DIR, exist_ok=True)
        os.makedirs(BIN_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        # 2. Check/install Chromium (with progress dialog if possible)
        chrome_path = None
        
        # Try to find existing Chromium first
        localappdata = os.getenv("LOCALAPPDATA", "")
        if localappdata:
            burp_patterns = [
                os.path.join(localappdata, "PortSwigger", "Burp Suite Professional", "**", "chrome.exe"),
                os.path.join(localappdata, "PortSwigger", "Burp Suite Community Edition", "**", "chrome.exe"),
            ]
            for pattern in burp_patterns:
                matches = glob.glob(pattern, recursive=True)
                if matches and os.path.isfile(matches[0]):
                    chrome_path = matches[0]
                    break
        
        if not chrome_path:
            bin_chrome = os.path.join(BIN_DIR, "chrome.exe")
            if os.path.isfile(bin_chrome):
                chrome_path = bin_chrome
        
        # If not found, download Chromium (direct download, no blocking dialogs)
        if not chrome_path:
            print("Chromium not found. Starting download...")
            debug_log("Chromium download started")
            
            # Download directly (no blocking UI)
            def progress_callback(percent, downloaded=0, total=0, status=""):
                # Log to file and console
                msg = f"Chromium download: {percent}% - {status}"
                # Use \r to update same line, flush to ensure immediate display
                print(f"\r{msg}", end='', flush=True)
                if percent % 10 == 0 or status:
                    debug_log(msg)
            
            chrome_path = ensure_chrome_executable(progress_callback)
            
            # Fallback: check bin directory
            if not chrome_path:
                bin_chrome = os.path.join(BIN_DIR, "chrome.exe")
                if os.path.isfile(bin_chrome):
                    chrome_path = bin_chrome
                    debug_log("Chromium found in bin/ after download attempt")
            
            if chrome_path:
                # Print newline after progress updates
                print()  # New line after progress updates
                debug_log(f"Chromium download completed: {chrome_path}")
            else:
                print()  # New line after progress updates
                debug_log("Chromium download failed")
        
        # 3. Seed profiles (create all profiles with themes)
        print("Setting up profiles...")
        debug_log("Setting up profiles...")
        try:
            setup_all_profiles()
            debug_log("Profiles setup completed")
        except Exception as e:
            debug_log(f"Profile setup error: {e}")
            import traceback
            debug_log(traceback.format_exc())
        
        # 4. Create desktop shortcut with Chromium icon
        print("Creating desktop shortcut...")
        try:
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            shortcut_path = os.path.join(desktop, "WindowsAutochrome.lnk")
            
            # Check if shortcut already exists
            if not os.path.exists(shortcut_path):
                # Create new shortcut
                try:
                    sys.path.insert(0, BASE_DIR)
                    from create_shortcut import create_shortcut
                    if create_shortcut():
                        print("Desktop shortcut created successfully!")
                        debug_log("Desktop shortcut created")
                    else:
                        print("Note: Desktop shortcut could not be created automatically.")
                        print(f"You can manually create a shortcut to: {os.path.join(BASE_DIR, 'launch.vbs')}")
                except Exception as e:
                    print(f"Warning: Could not create shortcut: {e}")
                    debug_log(f"Shortcut creation error: {e}")
                    print(f"You can manually create a shortcut to: {os.path.join(BASE_DIR, 'launch.vbs')}")
            else:
                print("Desktop shortcut already exists.")
        except Exception as e:
            print(f"Warning: Shortcut creation failed: {e}")
            debug_log(f"Shortcut creation failed: {e}")
        
        # 6. Create marker file (ALWAYS, even if Chromium download failed)
        try:
            with open(INSTALLED_MARKER, 'w') as f:
                f.write(f"Installed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                if chrome_path:
                    f.write(f"Chromium: {chrome_path}\n")
                else:
                    f.write("Chromium: NOT FOUND\n")
            print("Setup completed!")
            debug_log("Setup marker file created")
            return True
        except Exception as e:
            print(f"Warning: Could not create marker file: {e}")
            debug_log(f"Marker file creation error: {e}")
            # Still return True, setup is mostly complete
            return True
    
    except Exception as e:
        import traceback
        print(f"Setup error: {e}\n{traceback.format_exc()}")
        return False


def main():
    """Entry point.

    - python main.py                -> Native Chromium profile picker (no custom UI)
    - python main.py --profile Red  -> Launch specific profile (Red) without UI
    - python main.py --repair       -> Re-seed all profiles (force theme loading)
    """
    # Ensure clean exit on Windows
    import signal
    def signal_handler(sig, frame):
        print("\nExiting...")
        sys.exit(0)
    
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except:
        pass  # Windows may not support all signals
    
    try:
        # Check for --repair argument first
        if "--repair" in sys.argv:
            print("Repair mode: Re-seeding all profiles...")
            chrome_path = ensure_chrome_executable()
            if not chrome_path:
                print("ERROR: Chromium not found!")
                return
            
            setup_all_profiles()
            
            # Seed each profile
            for profile_name, _ in PROFILES:
                try:
                    cmd, env = build_chrome_command_for_profile(chrome_path, profile_name)
                    cmd.extend(["--minimized", "--no-first-run"])
                    process = subprocess.Popen(
                        cmd,
                        env=env,
                        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(3)
                    process.terminate()
                    time.sleep(1)
                    try:
                        process.kill()
                    except:
                        pass
                    print(f"[OK] Seeded profile: {profile_name}")
                except Exception as e:
                    print(f"[ERROR] Failed to seed {profile_name}: {e}")
            
            print("Repair completed!")
            return
        
        # Check and perform first-run setup if needed
        setup_success = check_and_setup()
        if not setup_success:
            print("WARNING: Initial setup had issues, but continuing anyway...")
            # Continue - user can manually fix if needed
        
        # Initialize chrome_path
        chrome_path = None
        
        # Basic arg parsing (no extra deps)
        profile_arg = None
        if "--profile" in sys.argv:
            try:
                idx = sys.argv.index("--profile")
                profile_arg = sys.argv[idx + 1].strip()
            except Exception:
                profile_arg = None

        # Ensure profiles directory exists
        os.makedirs(PROFILES_DIR, exist_ok=True)
        
        # If a specific profile was requested, launch it directly (no UI)
        if profile_arg:
            # Locate Chromium
            chrome_path = None
            localappdata = os.getenv("LOCALAPPDATA", "")
            if localappdata:
                burp_patterns = [
                    os.path.join(localappdata, "PortSwigger", "Burp Suite Professional", "**", "chrome.exe"),
                    os.path.join(localappdata, "PortSwigger", "Burp Suite Community Edition", "**", "chrome.exe"),
                ]
                for pattern in burp_patterns:
                    matches = glob.glob(pattern, recursive=True)
                    if matches and os.path.isfile(matches[0]):
                        chrome_path = matches[0]
                        break

            if not chrome_path:
                bin_chrome = os.path.join(BIN_DIR, "chrome.exe")
                if os.path.isfile(bin_chrome):
                    chrome_path = bin_chrome

            if not chrome_path:
                print("Chromium not found, downloading...")
                from threading import Event
                progress_event = Event()

                def progress_callback(percent, downloaded=0, total=0, status=""):
                    # Use \r to update same line, flush to ensure immediate display
                    msg = f"Progress: {percent}% - {status}"
                    print(f"\r{msg}", end='', flush=True)

                chrome_path = ensure_chrome_executable(progress_callback)
                # Print newline after progress updates
                print()  # New line after progress updates
                if not chrome_path:
                    print("Chromium could not be downloaded/installed!")
                    return

            print(f"Starting Chromium... (Profile: {profile_arg})")
            cmd, env = build_chrome_command_for_profile(chrome_path, profile_arg)
            process = subprocess.Popen(
                cmd,
                env=env,
                creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"Chromium started (PID: {process.pid})")
            print("Proxy: 127.0.0.1:8080 (Burp Suite)")
            return

        # Default: Chromium native profile picker (no CTk UI)
        # Find Chromium if not already found
        if not chrome_path:
            # Final fallback: try to find Chromium one more time
            localappdata = os.getenv("LOCALAPPDATA", "")
            if localappdata:
                burp_patterns = [
                    os.path.join(localappdata, "PortSwigger", "Burp Suite Professional", "**", "chrome.exe"),
                    os.path.join(localappdata, "PortSwigger", "Burp Suite Community Edition", "**", "chrome.exe"),
                ]
                for pattern in burp_patterns:
                    matches = glob.glob(pattern, recursive=True)
                    if matches and os.path.isfile(matches[0]):
                        chrome_path = matches[0]
                        break
            
            if not chrome_path:
                bin_chrome = os.path.join(BIN_DIR, "chrome.exe")
                if os.path.isfile(bin_chrome):
                    chrome_path = bin_chrome
        
        if not chrome_path:
            error_msg = (
                "Chromium not found!\n\n"
                "The setup process could not download Chromium automatically.\n\n"
                "Please:\n"
                "1. Check your internet connection\n"
                "2. Try running the EXE again\n"
                "3. Or manually download Chromium and place it in:\n"
                f"   {BIN_DIR}\\chrome.exe\n\n"
                "Check debug.log for details."
            )
            print(error_msg)
            debug_log("ERROR: Chromium not found after setup")
            try:
                messagebox.showerror("WindowsAutochrome - Chromium Not Found", error_msg)
            except:
                pass
            # Don't exit - wait a bit so user can read the message
            time.sleep(2)
            return

        print("Starting Chromium... (Native profile picker)")
        cmd, env = build_chrome_command(chrome_path)
        process = subprocess.Popen(
            cmd,
            env=env,
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Chromium started (PID: {process.pid})")
        return
        
    except Exception as e:
        # On error, print full traceback so it appears in crash.log / console
        import traceback
        error_msg = f"An error occurred:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        debug_log(error_msg)
        # Show error message to user
        try:
            messagebox.showerror("WindowsAutochrome Error", f"An error occurred:\n\n{str(e)}\n\nCheck debug.log for details.")
        except:
            pass
        # Wait a bit so user can read the error
        time.sleep(3)


if __name__ == "__main__":
    main()
