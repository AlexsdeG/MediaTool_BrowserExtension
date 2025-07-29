from pathlib import Path
import re
import os
from datetime import datetime

# --- Base Directories ---
# Use a more robust way to get the user's home directory
HOME_DIR = Path.home()
# Base directory for all app-related data
APP_DIR_BASE = HOME_DIR / 'MediaTool'
# Subdirectories for downloads and conversions
DOWNLOAD_DIR_BASE = APP_DIR_BASE / 'downloads'
CONVERT_DIR_BASE = APP_DIR_BASE / 'converted'

# --- Daily Subdirectories ---
def get_daily_paths():
    """Ensures and returns the daily download and convert directories."""
    today = datetime.now().strftime('%Y-%m-%d')
    daily_download_path = DOWNLOAD_DIR_BASE / today
    daily_convert_path = CONVERT_DIR_BASE / today
    
    # Create directories if they don't exist
    daily_download_path.mkdir(parents=True, exist_ok=True)
    daily_convert_path.mkdir(parents=True, exist_ok=True)
    
    return daily_download_path, daily_convert_path

# --- File System Utilities ---
def sanitize_filename(filename: str) -> str:
    """Removes illegal characters from a filename to make it safe for all filesystems."""
    # Remove characters that are illegal in Windows, Linux, and macOS
    # Also replace multiple spaces/underscores with a single one
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    sanitized = re.sub(r'[\s_]+', '_', sanitized)
    return sanitized

def get_file_structure(base_path: Path):
    """
    Recursively builds a JSON-like structure for a directory.
    """
    tree = []
    if not base_path.exists():
        return tree

    for item in sorted(base_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        node = {
            "name": item.name,
            "path": str(item.resolve()),
            "type": "file" if item.is_file() else "folder"
        }
        if item.is_dir():
            node["children"] = get_file_structure(item)
        else:
            node["size"] = item.stat().st_size
        tree.append(node)
    return tree

# --- Initialization ---
def initialize_directories():
    """Creates all necessary base directories on startup."""
    print("Initializing directories...")
    get_daily_paths()
    print(f"  - Download path: {DOWNLOAD_DIR_BASE}")
    print(f"  - Convert path: {CONVERT_DIR_BASE}")
    print("Initialization complete.")

# Ensure directories are created when the module is loaded
# initialize_directories()