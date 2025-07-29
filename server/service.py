from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import os
import queue
import json
import uuid
import subprocess
import sys

# Import your existing modules
from core import downloader
from core import converter
from core import utils

from security.auth import ServiceAuth

app = Flask(__name__)
CORS(app, origins=["chrome-extension://*"])
# CORS(app, origins=[
#     "chrome-extension://<your-extension-id>",
#     "http://localhost:8765"
# ], supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

# Task management
task_queue = queue.Queue()
active_tasks = {}

# Authentication
auth = ServiceAuth()

@app.before_request
def verify_auth():
    if request.endpoint == 'get_token':
        return

    auth_header = request.headers.get('Authorization')
    print("Auth header:", auth_header)
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    if not auth.verify_token(auth_header):
        return jsonify({"error": "Unauthorized"}), 401


class TaskManager:
    def __init__(self):
        self.tasks = {}
        
    def create_task(self, task_type, params):
        task_id = str(uuid.uuid4())
        task = {
            'id': task_id,
            'type': task_type,
            'status': 'pending',
            'progress': 0,
            'params': params,
            'result': None,
            'error': None
        }
        self.tasks[task_id] = task
        return task_id
    
    def update_task(self, task_id, **updates):
        if task_id in self.tasks:
            self.tasks[task_id].update(updates)
            # Emit to extension via WebSocket
            socketio.emit('task_update', self.tasks[task_id])

task_manager = TaskManager()

# API Endpoints
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "running", "version": "1.0.0"})

@app.route('/api/auth/token', methods=['POST'])
def get_token():
    # TODO: You can add more checks here (e.g., extension id, secret, etc.)
    return jsonify({"token": auth.token})

@app.route('/api/download', methods=['POST'])
def download_media():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best')
    
    if not url:
        return jsonify({"error": "URL required"}), 400
    
    # Create task
    task_id = task_manager.create_task('download', {
        'url': url,
        'quality': quality
    })
    
    # Queue for processing
    task_queue.put(task_id)
    
    return jsonify({"task_id": task_id})

@app.route('/api/convert', methods=['POST'])
def convert_media():
    data = request.json
    file_path = data.get('file_path')
    target_format = data.get('target_format')
    file_type = data.get('type')
    
    if not file_path or not target_format:
        return jsonify({"error": "file_path and format required"}), 400
    
    task_id = task_manager.create_task('convert', {
        'file_path': file_path,
        'format': target_format,
        'type': file_type
    })
    
    task_queue.put(task_id)
    return jsonify({"task_id": task_id})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(list(task_manager.tasks.values()))

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    task = task_manager.tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

def build_file_tree(base_path, file_type=None):
    """
    Recursively builds a file tree for the given base_path.
    Only includes files matching file_type ('audio' or 'video') if specified.
    """
    audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    tree = []
    if not base_path.exists():
        return tree
    for entry in sorted(base_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if entry.is_dir():
            children = build_file_tree(entry, file_type)
            if children:  # Only include folders with matching files
                tree.append({
                    'type': 'folder',
                    'name': entry.name,
                    'children': children
                })
        elif entry.is_file():
            ext = entry.suffix.lower()
            if file_type == 'audio' and ext not in audio_exts:
                continue
            if file_type == 'video' and ext not in video_exts:
                continue
            tree.append({
                'type': 'file',
                'name': entry.name,
                'path': str(entry),
                'size': entry.stat().st_size
            })
    return tree

@app.route('/api/files', methods=['GET'])
def list_files():
    """List downloaded and converted files as a directory tree, filtered by type if requested."""
    file_type = request.args.get('type', None)
    print("Requested file type:", file_type)
    if file_type not in (None, 'audio', 'video'):
        return jsonify({"error": "Invalid type parameter"}), 400
    try:
        downloads_tree = build_file_tree(utils.DOWNLOAD_DIR_BASE, file_type)
        converted_tree = build_file_tree(utils.CONVERT_DIR_BASE, file_type)
        return jsonify({
            'downloads': downloads_tree,
            'converted': converted_tree
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/open_folder', methods=['POST'])
def open_folder():
    """Open the MediaTool base folder in the system file explorer."""
    try:
        base_path = str(utils.DOWNLOAD_DIR_BASE.parent)
        if sys.platform.startswith('win'):
            os.startfile(base_path)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', base_path])
        else:
            subprocess.Popen(['xdg-open', base_path])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# WebSocket for real-time updates
@socketio.on('connect')
def handle_connect():
    print('Extension connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Extension disconnected')

# Background worker
def worker():
    """Background worker to process tasks"""
    while True:
        try:
            task_id = task_queue.get(timeout=1)
            task = task_manager.tasks.get(task_id)
            
            if not task:
                continue
                
            task_manager.update_task(task_id, status='running')
            
            try:
                if task['type'] == 'download':
                    process_download(task_id, task['params'])
                elif task['type'] == 'convert':
                    process_convert(task_id, task['params'])
                    
            except Exception as e:
                task_manager.update_task(task_id, 
                    status='failed', 
                    error=str(e)
                )
                
        except queue.Empty:
            continue

def process_download(task_id, params):
    """Process download task with progress updates"""
    try:
        daily_download_path, _ = utils.get_daily_paths()
        
        # Update progress during download
        def progress_callback(progress):
            task_manager.update_task(task_id, progress=progress)
        
        # Your existing download logic with progress callback
        downloader.handle_download(params['url'], daily_download_path, progress_callback)
        
        task_manager.update_task(task_id, 
            status='completed', 
            progress=100
        )
        
    except Exception as e:
        task_manager.update_task(task_id, 
            status='failed', 
            error=str(e)
        )

def process_convert(task_id, params):
    """Process conversion task with progress updates"""
    try:
        def progress_callback(progress):
            task_manager.update_task(task_id, progress=progress)
        # input, output, format, filetype
        converter.handle_conversion(params['file_path'], params['format'], params['file_type'], progress_callback=progress_callback)

        task_manager.update_task(task_id,
            status='completed',
            progress=100
        )
        
    except Exception as e:
        task_manager.update_task(task_id, 
            status='failed', 
            error=str(e)
        )

if __name__ == '__main__':
    # Setup directories # TODO: has to be run daily at midnight
    utils.initialize_directories()
    
    # Start background worker
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    
    # Start Flask app
    socketio.run(app, host='127.0.0.1', port=8765, debug=True)