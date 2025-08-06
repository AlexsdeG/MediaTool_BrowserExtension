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
    document.getElementById('refresh-media').addEventListener('click', () => this.detectPageMedia());
    document.getElementById('video-btn').addEventListener('click', () => this.setFileType('video'));
    document.getElementById('audio-btn').addEventListener('click', () => this.setFileType('audio'));
    document.getElementById('open-folder-btn').addEventListener('click', () => this.openMediaFolder());

    // Detect media on initial load
    this.detectPageMedia();
  }

  async switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-panel`).classList.add('active');

    if (tabName === 'convert') {
      this.loadFiles();
    } else if (tabName === 'download') {
      // Auto-detect media when switching to download tab
      this.detectPageMedia();
    } else if (tabName === 'tasks') {
      this.loadTasks();
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
    const target_format = document.getElementById('format-select').value;
    const file_type = this.currentFileType;
    this.sendMessageToBackend('convertMedia', { file_path: this.selectedFile.path, target_format, file_type }, 'Conversion started', 'Conversion failed');
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
      console.log('Detecting media on page...');
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      // Check if we can inject content script on this page
      if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://') || tab.url.startsWith('edge://') || tab.url.startsWith('about:')) {
        console.log('Cannot inject into this page type:', tab.url);
        this.displayDetectedMedia(null);
        return;
      }
      
      // Try to send message to content script first
      try {
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'detectMedia' });
        console.log('Media detection response:', response);
        
        if (response && !response.error) {
          this.displayDetectedMedia(response);
          return;
        } else {
          console.log('No media detected or error:', response?.error);
        }
      } catch (communicationError) {
        console.log('Content script communication failed:', communicationError.message);
      }
      
      // If content script communication failed, try to inject/re-inject
      try {
        console.log('Attempting to inject content script...');
        
        // Check if chrome.scripting is available (Manifest V3)
        if (chrome.scripting && chrome.scripting.executeScript) {
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js']
          });
          
          console.log('Content script injected, waiting for initialization...');
          
          // Wait longer for script to initialize and page to be ready
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          // Try communication again
          const response = await chrome.tabs.sendMessage(tab.id, { action: 'detectMedia' });
          console.log('Media detection response after injection:', response);
          this.displayDetectedMedia(response);
          
        } else {
          // Fallback for older Chrome versions or different manifest versions
          console.log('chrome.scripting not available, using executeScript...');
          
          await new Promise((resolve, reject) => {
            chrome.tabs.executeScript(tab.id, { file: 'content.js' }, (result) => {
              if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
              } else {
                resolve(result);
              }
            });
          });
          
          // Wait for script initialization
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          const response = await chrome.tabs.sendMessage(tab.id, { action: 'detectMedia' });
          this.displayDetectedMedia(response);
        }
        
      } catch (injectionError) {
        console.error('Failed to inject content script:', injectionError);
        
        // For YouTube specifically, try a different approach
        if (tab.url && tab.url.includes('youtube.com')) {
          console.log('YouTube detected, using alternative detection...');
          this.detectYouTubeDirectly(tab);
        } else {
          this.showNotification('Cannot detect media on this page', 'error');
          this.displayDetectedMedia(null);
        }
      }
      
    } catch (error) {
      console.error('Media detection failed:', error);
      this.showNotification('Media detection failed', 'error');
      this.displayDetectedMedia(null);
    }
  }

  async detectYouTubeDirectly(tab) {
    try {
      // Extract video ID from URL
      const url = new URL(tab.url);
      const videoId = url.searchParams.get('v');
      
      if (videoId) {
        console.log('Detected YouTube video ID:', videoId);
        
        // Create YouTube media data manually
        const youtubeData = {
          videos: [],
          audios: [],
          iframes: [],
          links: [],
          youtube: {
            videoId: videoId,
            title: tab.title || 'YouTube Video',
            channel: 'YouTube',
            url: tab.url,
            thumbnail: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
            type: 'youtube'
          },
          streaming: [{
            service: 'youtube',
            url: tab.url,
            title: tab.title || 'YouTube Video',
            type: 'streaming_service'
          }]
        };
        
        this.displayDetectedMedia(youtubeData);
      } else {
        this.displayDetectedMedia(null);
      }
      
    } catch (error) {
      console.error('Direct YouTube detection failed:', error);
      this.displayDetectedMedia(null);
    }
  }

  displayDetectedMedia(mediaData) {
    const mediaList = document.getElementById('media-list');
    mediaList.innerHTML = '';

    if (!mediaData) {
      mediaList.innerHTML = '<div class="empty-state"><p>No media detected on this page</p></div>';
      return;
    }

    let mediaCount = 0;

    // Display YouTube videos
    if (mediaData.youtube) {
      const youtube = mediaData.youtube;
      const item = document.createElement('div');
      item.className = 'media-item';
      item.innerHTML = `
        <div class="media-info">
          <span class="media-type">🎬 YouTube</span>
          <span class="media-title">${this.truncateText(youtube.title, 30)}</span>
          <span class="media-channel">${this.truncateText(youtube.channel, 25)}</span>
        </div>
        <button class="btn small" data-url="${youtube.url}">Download</button>
      `;
      item.querySelector('button').addEventListener('click', (e) => {
        e.stopPropagation();
        document.getElementById('url-input').value = e.target.dataset.url;
      });
      mediaList.appendChild(item);
      mediaCount++;
    }

    // Display video elements
    if (mediaData.videos && mediaData.videos.length > 0) {
      mediaData.videos.forEach((video, index) => {
        // Get the best URL from sources or currentSrc
        let videoUrl = video.currentSrc || 
                      (video.sources && video.sources.length > 0 ? video.sources[0] : null);
        
        if (videoUrl && this.isValidMediaUrl(videoUrl)) {
          const item = document.createElement('div');
          item.className = 'media-item';
          item.innerHTML = `
            <div class="media-info">
              <span class="media-type">📹 Video</span>
              <span class="media-title">${this.truncateText(video.title, 30)}</span>
              ${video.duration ? `<span class="media-duration">${this.formatDuration(video.duration)}</span>` : ''}
            </div>
            <button class="btn small" data-url="${videoUrl}">Download</button>
          `;
          item.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('url-input').value = e.target.dataset.url;
          });
          mediaList.appendChild(item);
          mediaCount++;
        }
      });
    }

    // Display audio elements
    if (mediaData.audios && mediaData.audios.length > 0) {
      mediaData.audios.forEach((audio, index) => {
        let audioUrl = audio.currentSrc || 
                      (audio.sources && audio.sources.length > 0 ? audio.sources[0] : null);
        
        if (audioUrl && this.isValidMediaUrl(audioUrl)) {
          const item = document.createElement('div');
          item.className = 'media-item';
          item.innerHTML = `
            <div class="media-info">
              <span class="media-type">🎵 Audio</span>
              <span class="media-title">${this.truncateText(audio.title, 30)}</span>
              ${audio.duration ? `<span class="media-duration">${this.formatDuration(audio.duration)}</span>` : ''}
            </div>
            <button class="btn small" data-url="${audioUrl}">Download</button>
          `;
          item.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('url-input').value = e.target.dataset.url;
          });
          mediaList.appendChild(item);
          mediaCount++;
        }
      });
    }

    // Display iframe embedded media
    if (mediaData.iframes && mediaData.iframes.length > 0) {
      mediaData.iframes.forEach((iframe, index) => {
        if (iframe.src) {
          const item = document.createElement('div');
          item.className = 'media-item';
          item.innerHTML = `
            <div class="media-info">
              <span class="media-type">🖼️ Embedded</span>
              <span class="media-title">${this.truncateText(iframe.title, 30)}</span>
            </div>
            <button class="btn small" data-url="${iframe.src}">Download</button>
          `;
          item.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('url-input').value = e.target.dataset.url;
          });
          mediaList.appendChild(item);
          mediaCount++;
        }
      });
    }

    // Display media links
    if (mediaData.links && mediaData.links.length > 0) {
      mediaData.links.forEach((link, index) => {
        if (link.url) {
          const item = document.createElement('div');
          item.className = 'media-item';
          item.innerHTML = `
            <div class="media-info">
              <span class="media-type">🔗 Link</span>
              <span class="media-title">${this.truncateText(link.title, 30)}</span>
            </div>
            <button class="btn small" data-url="${link.url}">Download</button>
          `;
          item.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('url-input').value = e.target.dataset.url;
          });
          mediaList.appendChild(item);
          mediaCount++;
        }
      });
    }

    // Display streaming services
    if (mediaData.streaming && mediaData.streaming.length > 0) {
      mediaData.streaming.forEach((stream, index) => {
        if (stream.url) {
          const item = document.createElement('div');
          item.className = 'media-item';
          item.innerHTML = `
            <div class="media-info">
              <span class="media-type">📺 ${stream.service || 'Stream'}</span>
              <span class="media-title">${this.truncateText(stream.title, 30)}</span>
            </div>
            <button class="btn small" data-url="${stream.url}">Download</button>
          `;
          item.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('url-input').value = e.target.dataset.url;
          });
          mediaList.appendChild(item);
          mediaCount++;
        }
      });
    }

    // Show message if no media found
    if (mediaCount === 0) {
      mediaList.innerHTML = '<div class="empty-state"><p>No downloadable media found on this page</p></div>';
    }
  }

  truncateText(text, maxLength) {
    if (!text) return 'Unknown';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  }

  formatDuration(seconds) {
    if (!seconds || isNaN(seconds)) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  isValidMediaUrl(url) {
    if (!url) return false;
    
    // Skip data URLs, blob URLs that are too short, and invalid URLs
    if (url.startsWith('data:') || 
        (url.startsWith('blob:') && url.length < 20) ||
        url === '' || 
        url === 'about:blank') {
      return false;
    }
    
    try {
      new URL(url);
      return true;
    } catch {
      return false;
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
