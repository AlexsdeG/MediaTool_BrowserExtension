import os
import re
from pathlib import Path
from datetime import datetime

# Define base paths
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / 'data'
# DOWNLOAD_DIR_BASE = DATA_DIR / 'download'
# CONVERT_DIR_BASE = DATA_DIR / 'convert'
DOWNLOAD_DIR_BASE = Path.home() / "MediaTool" / "downloads"
CONVERT_DIR_BASE = Path.home() / "MediaTool" / "converted"
TEMP_DIR_BASE = Path.home() / "MediaTool" / "temp"

def setup_directories():
    """Creates the necessary data directories if they don't exist."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Create dated subdirectories
    daily_download_path = DOWNLOAD_DIR_BASE / today_str
    daily_convert_path = CONVERT_DIR_BASE / today_str
    
    daily_download_path.mkdir(parents=True, exist_ok=True)
    daily_convert_path.mkdir(parents=True, exist_ok=True)
    TEMP_DIR_BASE.mkdir(parents=True, exist_ok=True)
    
    # print("Directories initialized.")
    return daily_download_path, daily_convert_path

def sanitize_filename(filename):
    """Removes invalid characters from a string to make it a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def get_daily_paths():
    """Returns the Path objects for today's download and convert directories."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    return DOWNLOAD_DIR_BASE / today_str, CONVERT_DIR_BASE / today_str