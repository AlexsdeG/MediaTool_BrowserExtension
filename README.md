# MediaTool Browser Extension & Service

A cross-platform tool to download and convert media from your browser using a local Python backend service.

## Features
- Download videos, audio, and iframes from any page
- Convert media to MP3, MP4, WAV, FLAC
- Chrome extension UI
- Real-time task updates
- Windows service support (Linux/macOS coming soon)

## Quick Start

### 1. Start Backend Service (Dev)
```
cd server
python service.py
```

### 2. Load Chrome Extension
- Go to chrome://extensions
- Enable Developer Mode
- Load `extensions/chrome`

### 3. Download/Convert Media
- Use the popup to send tasks to the backend

## Production
- Build with `python scripts/build.py`
- Create installer with NSIS (see `server/installer.nsi`)

## Security
- Localhost only, token-based auth between extension and service

## Roadmap
- Linux/macOS service support
- Firefox extension
- Auto-update system

See `docs/DEVELOPMENT.md` for more.

# MediaTool_BrowserExtension
Browser extension for my MediaTool_CLI




# Extension Structure (demo)
extension/
├── manifest.json
├── popup.html           # Main UI popup
├── popup.js            # Popup logic
├── popup.css           # Popup styling
├── content.js          # Content script for page analysis
├── background.js       # Service worker for downloads
├── inject.js           # Injected script for deep analysis
├── utils.js            # Utility functions
├── icons/              # Extension icons
└── assets/             # CSS, images, etc.