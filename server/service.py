# service.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import queue
import json
from pathlib import Path
import uuid

# Import your existing modules
from core import downloader
from core import converter
from core import utils

from security.auth import ServiceAuth

app = Flask(__name__)
CORS(app, origins=["chrome-extension://*"])
socketio = SocketIO(app, cors_allowed_origins="*")

# Task management
task_queue = queue.Queue()
active_tasks = {}

# Authentication
auth = ServiceAuth()

@app.before_request
def verify_auth():
    # Allow health check without auth
    if request.endpoint == 'health_check':
        return
    auth_header = request.headers.get('Authorization')
    # if not auth.verify_token(auth_header):
    #     return jsonify({"error": "Unauthorized"}), 401


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
    target_format = data.get('format')
    
    if not file_path or not target_format:
        return jsonify({"error": "file_path and format required"}), 400
    
    task_id = task_manager.create_task('convert', {
        'file_path': file_path,
        'format': target_format
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

@app.route('/api/files', methods=['GET'])
def list_files():
    """List downloaded and converted files"""
    try:
        download_files = list(utils.DOWNLOAD_DIR_BASE.glob('**/*'))
        convert_files = list(utils.CONVERT_DIR_BASE.glob('**/*'))
        
        files = []
        for file_path in download_files + convert_files:
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'type': 'download' if utils.DOWNLOAD_DIR_BASE in file_path.parents else 'convert'
                })
        
        return jsonify(files)
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
        converter.convert_media(params['file_path'], params['output_path'], params['format'], params['file_type'], progress_callback=progress_callback)

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
    utils.setup_directories()
    
    # Start background worker
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    
    # Start Flask app
    socketio.run(app, host='127.0.0.1', port=8765, debug=True)