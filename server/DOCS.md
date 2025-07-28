



# Dev Workflow

``` bash
# 1. Install development dependencies
pip install flask flask-socketio flask-cors pyinstaller

# 2. Install Windows service dependencies (optional)
pip install pywin32

# 3. Install NSIS for installer creation

# 4. Build and test
python build.py
```



# Extra Stuff

Local Service Security
``` python
# Add authentication token
import secrets

class ServiceAuth:
    def __init__(self):
        self.token = self.load_or_create_token()
    
    def load_or_create_token(self):
        token_file = Path.home() / ".mediatool" / "token"
        if token_file.exists():
            return token_file.read_text().strip()
        else:
            token = secrets.token_urlsafe(32)
            token_file.parent.mkdir(exist_ok=True)
            token_file.write_text(token)
            return token
    
    def verify_request(self, request):
        auth_header = request.headers.get('Authorization')
        return auth_header == f"Bearer {self.token}"

# Use in Flask app
auth = ServiceAuth()

@app.before_request
def verify_auth():
    if request.endpoint != 'health_check':
        if not auth.verify_request(request):
            return jsonify({"error": "Unauthorized"}), 401
```

Port and Network Security
``` python
# Use random available port
import socket

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

# Bind only to localhost
app.run(host='127.0.0.1', port=find_free_port())
```

Auto-Update System
``` python
# Add to service
import requests
import json

def check_for_updates():
    try:
        response = requests.get('https://api.github.com/repos/AlexsdeG/MediaTool_CLI/releases/latest')
        latest = response.json()
        current_version = "1.0.0"  # Your current version
        
        if latest['tag_name'] > current_version:
            return latest['assets'][0]['download_url']
    except:
        pass
    return None
```



"""
function extractYouTubeData() {
  const videoId = new URLSearchParams(window.location.search).get('v');
  const videoTitle = document.querySelector('h1.title')?.textContent;
  
  return {
    videoId,
    title: videoTitle,
    url: window.location.href,
    thumbnail: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`
  };
}

"""
"""
function detectHLSStreams() {
  const scripts = document.querySelectorAll('script');
  const hlsUrls = [];
  
  scripts.forEach(script => {
    const content = script.textContent;
    const m3u8Matches = content.match(/https?:\/\/[^\s"']+\.m3u8[^\s"']*/g);
    if (m3u8Matches) {
      hlsUrls.push(...m3u8Matches);
    }
  });
  
  return hlsUrls;
}
"""