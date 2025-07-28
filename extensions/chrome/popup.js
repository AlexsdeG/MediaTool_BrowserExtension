class MediaToolClient {
  constructor() {
    this.serviceUrl = 'http://127.0.0.1:8765';
    this.socket = null;
    this.init();
  }

  async init() {
    await this.checkServiceStatus();
    this.setupWebSocket();
    this.setupEventListeners();
    this.loadTasks();
  }

  async checkServiceStatus() {
    try {
      const response = await fetch(`${this.serviceUrl}/api/health`);
      if (response.ok) {
        this.updateServiceStatus(true);
      } else {
        this.updateServiceStatus(false);
      }
    } catch (error) {
      this.updateServiceStatus(false);
    }
  }

  updateServiceStatus(connected) {
    const statusEl = document.getElementById('service-status');
    if (connected) {
      statusEl.textContent = '🟢 Connected';
      statusEl.className = 'status connected';
    } else {
      statusEl.textContent = '🔴 Service Offline';
      statusEl.className = 'status disconnected';
    }
  }

  setupWebSocket() {
    try {
      this.socket = io(this.serviceUrl);
      
      this.socket.on('connect', () => {
        console.log('Connected to service');
        this.updateServiceStatus(true);
      });

      this.socket.on('disconnect', () => {
        console.log('Disconnected from service');
        this.updateServiceStatus(false);
      });

      this.socket.on('task_update', (task) => {
        this.updateTaskDisplay(task);
      });
    } catch (error) {
      console.error('WebSocket setup failed:', error);
    }
  }

  setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });

    // Download button
    document.getElementById('download-btn').addEventListener('click', () => {
      this.downloadMedia();
    });

    // Convert button
    document.getElementById('convert-btn').addEventListener('click', () => {
      this.convertMedia();
    });

    // Refresh tasks
    document.getElementById('refresh-tasks').addEventListener('click', () => {
      this.loadTasks();
    });

    // Load current page media
    this.detectPageMedia();
  }

  switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-panel`).classList.add('active');

    if (tabName === 'convert') {
      this.loadFiles();
    } else if (tabName === 'tasks') {
      this.loadTasks();
    }
  }

  async downloadMedia() {
    const url = document.getElementById('url-input').value;
    const quality = document.getElementById('quality-select').value;

    if (!url) {
      alert('Please enter a URL');
      return;
    }

    try {
      const response = await fetch(`${this.serviceUrl}/api/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url, quality })
      });

      const result = await response.json();
      
      if (response.ok) {
        this.showNotification(`Download started: ${result.task_id}`);
        this.switchTab('tasks');
      } else {
        this.showNotification(`Error: ${result.error}`, 'error');
      }
    } catch (error) {
      this.showNotification('Service unavailable', 'error');
    }
  }

  async detectPageMedia() {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Send message to content script
    try {
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'detectMedia' });
      this.displayDetectedMedia(response);
    } catch (error) {
      console.log('Could not detect media on page');
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
          <button class="btn small" onclick="downloadDetected('${video.currentSrc}')">
            Download
          </button>
        `;
        mediaList.appendChild(item);
      });
    }

    // Similar for audio, YouTube, etc.
  }

  async loadTasks() {
    try {
      const response = await fetch(`${this.serviceUrl}/api/tasks`);
      const tasks = await response.json();
      this.displayTasks(tasks);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    }
  }

  displayTasks(tasks) {
    const taskList = document.getElementById('task-list');
    taskList.innerHTML = '';

    tasks.forEach(task => {
      const item = document.createElement('div');
      item.className = `task-item ${task.status}`;
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
      taskList.appendChild(item);
    });
  }

  updateTaskDisplay(task) {
    // Update specific task in the UI
    const taskElement = document.querySelector(`[data-task-id="${task.id}"]`);
    if (taskElement) {
      // Update progress bar, status, etc.
    }
  }

  showNotification(message, type = 'info') {
    // Simple notification system
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// Initialize when popup opens
document.addEventListener('DOMContentLoaded', () => {
  new MediaToolClient();
});

// Global function for detected media
window.downloadDetected = (url) => {
  document.getElementById('url-input').value = url;
  document.getElementById('download-btn').click();
};