# MediaTool Development Guide

## Development

### 1. Start Backend Service (Dev)

```bash
cd server
python service.py
```

- Service runs at http://127.0.0.1:8765
- Logs output to console

### 2. Load Chrome Extension (Dev)
- Go to chrome://extensions
- Enable Developer Mode
- Click "Load unpacked" and select `extensions/chrome`

### 3. Test
- Use the popup to download/convert media
- Check backend logs for errors


## Production

### 1. Build Standalone Executable

```bash
cd scripts
python build.py
```

- Creates a standalone executable for Windows

### 2. Create Installer (Windows)

```bash
cd server
makensis installer.nsi
```

### 3. Install Service
- Run the installer or use the executable


## Notes
- For Linux/macOS, see future docs for service/installer support
- For Firefox, copy `chrome` extension and adjust manifest to v2
