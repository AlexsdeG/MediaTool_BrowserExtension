class MediaToolClient {
  constructor() {
    this.serviceUrl = 'http://127.0.0.1:8765';
    this.socket = null;
    this.selectedFile = null;
    this.currentFileType = 'video';
    this.init();
  }

  async init() {
    // await this.checkServiceStatus();
    this.setupWebSocket();
    this.setupEventListeners();
    this.loadTasks();
  }

  async checkServiceStatus() {
    try {
      const response = await fetch(`${this.serviceUrl}/api/health`);
      this.updateServiceStatus(response.ok);
    } catch (error) {
      this.updateServiceStatus(false);
    }
  }

  updateServiceStatus(connected) {
    const statusEl = document.getElementById('service-status');
    statusEl.textContent = connected ? '🟢 Connected' : '🔴 Service Offline';
    statusEl.className = `status ${connected ? 'connected' : 'disconnected'}`;
  }

  setupWebSocket() {
    try {
      this.socket = io(this.serviceUrl);
      this.socket.on('connect', () => this.updateServiceStatus(true));
      this.socket.on('disconnect', () => this.updateServiceStatus(false));
      this.socket.on('task_update', (task) => this.updateTaskDisplay(task));
    } catch (error) {
      console.error('WebSocket setup failed:', error);
    }
  }

  setupEventListeners() {
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });

    document.getElementById('download-btn').addEventListener('click', () => this.downloadMedia());
    document.getElementById('convert-btn').addEventListener('click', () => this.convertMedia());
    document.getElementById('refresh-tasks').addEventListener('click', () => this.loadTasks());
    document.getElementById('video-btn').addEventListener('click', () => this.setFileType('video'));
    document.getElementById('audio-btn').addEventListener('click', () => this.setFileType('audio'));
    document.getElementById('open-folder-btn').addEventListener('click', () => this.openMediaFolder());

    this.detectPageMedia();
  }

  async switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-panel`).classList.add('active');

    if (tabName === 'convert') {
      this.loadFiles();
    }
  }

  async downloadMedia() {
    const url = document.getElementById('url-input').value;
    if (!url) {
      this.showNotification('Please enter a URL', 'error');
      return;
    }
    const quality = document.getElementById('quality-select').value;
    this.sendMessageToBackend('downloadMedia', { url, quality }, 'Download started', 'Download failed');
  }

  async convertMedia() {
    if (!this.selectedFile) {
      this.showNotification('Please select a file to convert.', 'error');
      return;
    }
    const format = document.getElementById('format-select').value;
    const outputType = this.currentFileType;
    this.sendMessageToBackend('convertMedia', { file_path: this.selectedFile.path, target_format: format, output_type: outputType }, 'Conversion started', 'Conversion failed');
  }

  async sendMessageToBackend(action, data, successMsg, errorMsg) {
    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ action, data }, response => {
          if (chrome.runtime.lastError) {
            reject(chrome.runtime.lastError.message);
          } else if (response && !response.error) {
            resolve(response);
          } else {
            reject(response ? response.error : 'Unknown error');
          }
        });
      });
      this.showNotification(`${successMsg}: ${response.task_id}`);
      this.loadTasks();
      this.switchTab('tasks');
    } catch (error) {
      this.showNotification(`${errorMsg}: ${error}`, 'error');
    }
  }

  setFileType(type) {
    this.currentFileType = type;
    document.getElementById('video-btn').classList.toggle('active', type === 'video');
    document.getElementById('audio-btn').classList.toggle('active', type === 'audio');
    this.loadFiles();
    this.updateFormatSelection();
  }

  async loadFiles() {
    try {
      const files = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ action: 'getFiles', fileType: this.currentFileType }, response => {
          if (chrome.runtime.lastError) {
            reject(chrome.runtime.lastError.message);
          } else if (response && !response.error) {
            resolve(response);
          } else {
            reject(response ? response.error : 'Unknown error');
          }
        });
      });
      this.renderFileTree(files);
    } catch (error) {
      this.showNotification('Failed to load files', 'error');
    }
  }

  renderFileTree(files) {
    const treeContainer = document.getElementById('file-tree');
    treeContainer.innerHTML = '';
    if (files.downloads) {
      treeContainer.appendChild(this.createTreeElement(files.downloads, 'Downloads'));
    }
    if (files.converted) {
      treeContainer.appendChild(this.createTreeElement(files.converted, 'Converted'));
    }
  }

  createTreeElement(nodes, name) {
    const folder = this.createFolderElement(name);
    if (Array.isArray(nodes)) {
      nodes.forEach(node => {
        let el;
        if (node.type === 'folder') {
          el = this.createTreeElement(node.children, node.name);
        } else {
          el = this.createFileElement(node);
        }
        folder.querySelector('.tree-children').appendChild(el);
      });
    }
    return folder;
  }

  createTreeElement(nodes, name, depth = 0) {
    const folder = this.createFolderElement(name, depth);
    if (Array.isArray(nodes)) {
      nodes.forEach(node => {
        let el;
        if (node.type === 'folder') {
          el = this.createTreeElement(node.children, node.name, depth + 1);
        } else {
          el = this.createFileElement(node, depth + 1);
        }
        folder.querySelector('.tree-children').appendChild(el);
      });
    }
    return folder;
  }

  createFileElement(file, depth = 0) {
    const element = document.createElement('div');
    element.className = 'tree-item tree-file';
    element.style.marginLeft = `${depth * 16}px`;
    element.textContent = file.name;
    element.addEventListener('click', (e) => {
      e.stopPropagation();
      if (this.selectedFile) {
        document.querySelector(`[data-path="${this.selectedFile.path}"]`)?.classList.remove('selected');
      }
      this.selectedFile = file;
      element.classList.add('selected');
      element.dataset.path = file.path;
      document.getElementById('convert-btn').disabled = false;
      this.updateFormatSelection();
    });
    return element;
  }

  createFolderElement(name, depth = 0) {
    const folder = document.createElement('div');
    folder.className = 'tree-item tree-folder collapsed';
    folder.style.marginLeft = `${depth * 16}px`;
    folder.innerHTML = `<span class="folder-toggle">▶</span> <span class="folder-name">${name}</span><div class="tree-children" style="display:none"></div>`;
    folder.querySelector('.folder-toggle').addEventListener('click', (e) => {
      e.stopPropagation();
      const children = folder.querySelector('.tree-children');
      const isCollapsed = children.style.display === 'none';
      children.style.display = isCollapsed ? 'block' : 'none';
      folder.classList.toggle('collapsed', !isCollapsed);
      folder.querySelector('.folder-toggle').textContent = isCollapsed ? '▼' : '▶';
    });
    folder.querySelector('.folder-name').addEventListener('click', (e) => {
      e.stopPropagation();
      const children = folder.querySelector('.tree-children');
      const isCollapsed = children.style.display === 'none';
      children.style.display = isCollapsed ? 'block' : 'none';
      folder.classList.toggle('collapsed', !isCollapsed);
      folder.querySelector('.folder-toggle').textContent = isCollapsed ? '▼' : '▶';
    });
    return folder;
  }

  updateFormatSelection() {
    const formatSelect = document.getElementById('format-select');
    const currentFormat = this.selectedFile?.name.split('.').pop();
    const isVideo = ['mp4', 'mkv', 'avi', 'mov', 'webm'].includes(currentFormat);
    const isAudio = ['mp3', 'wav', 'flac', 'aac', 'ogg'].includes(currentFormat);

    let options = '';
    if (this.currentFileType === 'video' && isVideo) {
      options = ['mp4', 'mkv', 'webm', 'avi'].filter(f => f !== currentFormat).map(f => `<option value="${f}">${f.toUpperCase()}</option>`).join('');
      options += '<option value="mp3">MP3 (from Video)</option>';
    } else if (this.currentFileType === 'audio' && (isAudio || isVideo)) {
      options = ['mp3', 'wav', 'flac'].filter(f => f !== currentFormat).map(f => `<option value="${f}">${f.toUpperCase()}</option>`).join('');
    }
    formatSelect.innerHTML = options;
  }

  openMediaFolder() {
    chrome.runtime.sendMessage({ action: 'openMediaFolder' }, response => {
      if (chrome.runtime.lastError || (response && response.error)) {
        this.showNotification('Failed to open folder', 'error');
      } else {
        this.showNotification('Opened MediaTool folder', 'info');
      }
    });
  }

  async detectPageMedia() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'detectMedia' });
      this.displayDetectedMedia(response);
    } catch (error) {
      // It's common for this to fail on pages where the content script isn't injected
    }
  }

  displayDetectedMedia(mediaData) {
    const mediaList = document.getElementById('media-list');
    mediaList.innerHTML = '';

    if (mediaData?.videos?.length > 0) {
      mediaData.videos.forEach(video => {
        const item = document.createElement('div');
        item.className = 'media-item';
        item.innerHTML = `
          <div class="media-info">
            <span class="media-type">📹 Video</span>
            <span class="media-title">${video.title || 'Unknown'}</span>
          </div>
          <button class="btn small" data-url="${video.src}">Download</button>
        `;
        item.querySelector('button').addEventListener('click', (e) => {
            document.getElementById('url-input').value = e.target.dataset.url;
            this.downloadMedia();
        });
        mediaList.appendChild(item);
      });
    }
  }

  async loadTasks() {
    try {
      const tasks = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ action: 'getTasks' }, response => {
          if (chrome.runtime.lastError) {
            reject(chrome.runtime.lastError.message);
          } else if (response && !response.error) {
            resolve(response);
          } else {
            reject(response ? response.error : 'Unknown error');
          }
        });
      });
      this.displayTasks(tasks);
    } catch (error) {
      this.showNotification('Failed to load tasks', 'error');
    }
  }

  displayTasks(tasks) {
    const taskList = document.getElementById('task-list');
    taskList.innerHTML = '';
    if (!Array.isArray(tasks)) return;

    tasks.slice().reverse().forEach(task => {
      const item = this.createTaskElement(task);
      taskList.appendChild(item);
    });
  }

  createTaskElement(task) {
    const item = document.createElement('div');
    item.className = `task-item ${task.status}`;
    item.dataset.taskId = task.id;
    item.innerHTML = `
      <div class="task-info">
        <span class="task-type">${task.type.toUpperCase()}</span>
        <span class="task-status">${task.status}</span>
      </div>
      <div class="task-progress">
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${task.progress}%"></div>
        </div>
        <span class="progress-text">${task.progress}%</span>
      </div>
      ${task.error ? `<div class="task-error">${task.error}</div>` : ''}
    `;
return item;
  }

  updateTaskDisplay(task) {
    const taskElement = document.querySelector(`[data-task-id="${task.id}"]`);
    if (taskElement) {
      taskElement.className = `task-item ${task.status}`;
      taskElement.querySelector('.task-status').textContent = task.status;
      taskElement.querySelector('.progress-fill').style.width = `${task.progress}%`;
      taskElement.querySelector('.progress-text').textContent = `${task.progress}%`;
      if (task.error) {
        let errorEl = taskElement.querySelector('.task-error');
        if (!errorEl) {
          errorEl = document.createElement('div');
          errorEl.className = 'task-error';
          taskElement.appendChild(errorEl);
        }
        errorEl.textContent = task.error;
      }
    } else {
        // if task is not in the list, add it
        const taskList = document.getElementById('task-list');
        const item = this.createTaskElement(task);
        taskList.prepend(item);
    }
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 3000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new MediaToolClient();
});
