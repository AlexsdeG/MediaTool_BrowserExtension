import subprocess
import shutil
import os
from pathlib import Path

def build_service():
    """Build service executable with PyInstaller"""
    print("Building service executable...")
    
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--hidden-import=engineio.async_drivers.threading",
        "--hidden-import=socketio",
        "--add-data", "templates;templates",
        "--add-data", "static;static",
        "service.py"
    ], check=True)
    
    print("Service built successfully")

def build_installer():
    """Build NSIS installer"""
    print("Building installer...")
    
    # Ensure NSIS is in PATH or specify full path
    subprocess.run([
        "makensis",
        "installer.nsi"
    ], check=True)
    
    print("Installer built successfully")

def build_extension():
    """Package extension"""
    print("Packaging extension...")
    
    # Create extension package
    shutil.make_archive('extension', 'zip', 'extension')
    
    print("Extension packaged")

if __name__ == "__main__":
    build_service()
    build_extension()
    build_installer()