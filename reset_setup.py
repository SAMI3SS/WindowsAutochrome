"""
Reset WindowsAutochrome setup - removes .installed marker and optionally clears cache.
Run this to force setup to run again on next launch.
"""

import os
import shutil

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTALLED_MARKER = os.path.join(BASE_DIR, ".installed")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
DEBUG_LOG = os.path.join(BASE_DIR, "debug.log")

def reset_setup(clear_cache=False, clear_logs=False):
    """Reset setup by removing marker files."""
    print("Resetting WindowsAutochrome setup...")
    
    # Remove .installed marker
    if os.path.exists(INSTALLED_MARKER):
        os.remove(INSTALLED_MARKER)
        print(f"[OK] Removed: {INSTALLED_MARKER}")
    else:
        print(f"  (Not found: {INSTALLED_MARKER})")
    
    # Clear cache if requested
    if clear_cache and os.path.exists(CACHE_DIR):
        try:
            shutil.rmtree(CACHE_DIR)
            print(f"[OK] Cleared cache: {CACHE_DIR}")
        except Exception as e:
            print(f"[ERROR] Error clearing cache: {e}")
    
    # Clear debug log if requested
    if clear_logs and os.path.exists(DEBUG_LOG):
        try:
            os.remove(DEBUG_LOG)
            print(f"[OK] Cleared debug log: {DEBUG_LOG}")
        except Exception as e:
            print(f"[ERROR] Error clearing log: {e}")
    
    print("\nSetup reset complete!")
    print("Next time you run 'python main.py', setup will run again.")
    print("\nNote: This does NOT delete:")
    print("  - Chromium installation (bin/chrome.exe)")
    print("  - Profiles (profiles/)")
    print("  - Desktop shortcut")

if __name__ == "__main__":
    import sys
    
    clear_cache = "--clear-cache" in sys.argv or "-c" in sys.argv
    clear_logs = "--clear-logs" in sys.argv or "-l" in sys.argv
    
    print("WindowsAutochrome Setup Reset")
    print("=" * 40)
    print()
    
    if clear_cache:
        print("Will clear cache directory")
    if clear_logs:
        print("Will clear debug log")
    
    print()
    reset_setup(clear_cache=clear_cache, clear_logs=clear_logs)
