// MediaTool Extension Background Service Worker
console.log('MediaTool Extension Background Script Loaded');

class ServiceManager {
  constructor() {
    this.serviceUrl = 'http://127.0.0.1:8765';
    this.token = null;
    this.isServiceRunning = false;
    this.init();
  }
  
  async init() {
    console.log('Initializing ServiceManager...');
    try {
      this.token = await this.getStoredToken();
      await this.checkServiceHealth();
      this.setupMessageHandlers();
      this.setupPeriodicHealthCheck();
    } catch (error) {
      console.error('ServiceManager initialization failed:', error);
    }
  }
  
  async getStoredToken() {
    try {
      const result = await chrome.storage.local.get(['authToken']);
      return result.authToken || null;
    } catch (error) {
      console.error('Failed to get stored token:', error);
      return null;
    }
  }
  
  async checkServiceHealth() {
    try {
      const response = await fetch(`${this.serviceUrl}/api/health`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      
      this.isServiceRunning = response.ok;
      if (!this.isServiceRunning && !this.token) {
        // Try to get a new token if service is running but we don't have auth
        await this.requestToken();
      }
      
      return this.isServiceRunning;
    } catch (error) {
      console.log('Service not available:', error.message);
      this.isServiceRunning = false;
      return false;
    }
  }
  
  async requestToken() {
    try {
      console.log('Requesting new auth token...');
      const response = await fetch(`${this.serviceUrl}/api/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          extension_id: chrome.runtime.id,
          timestamp: Date.now()
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        this.token = data.token;
        await chrome.storage.local.set({ authToken: this.token });
        return this.token;
      } else {
        console.error('Failed to get auth token:', response.status);
        return null;
      }
    } catch (error) {
      console.error('Token request failed:', error);
      return null;
    }
  }
  
  getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }
  
  setupMessageHandlers() {
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      console.log('Background received message:', message);
      
      switch (message.action) {
        case 'checkServiceStatus':
          this.checkServiceHealth()
            .then(status => sendResponse({ isRunning: status }))
            .catch(error => sendResponse({ isRunning: false, error: error.message }));
          return true;
          
        case 'downloadMedia':
          this.downloadMedia(message.data)
            .then(sendResponse)
            .catch(error => sendResponse({ error: error.message }));
          return true;
          
        case 'convertMedia':
          this.convertMedia(message.data)
            .then(sendResponse)
            .catch(error => sendResponse({ error: error.message }));
          return true;
          
        case 'getTasks':
          this.getTasks()
            .then(sendResponse)
            .catch(error => sendResponse({ error: error.message }));
          return true;
          
        case 'getFiles':
          this.getFiles(message.fileType)
            .then(sendResponse)
            .catch(error => sendResponse({ error: error.message }));
          return true;
          
        case 'openMediaFolder':
          this.openMediaFolder()
            .then(sendResponse)
            .catch(error => sendResponse({ error: error.message }));
          return true;
      }
    });
  }
  
  setupPeriodicHealthCheck() {
    // Check service health every 30 seconds
    setInterval(async () => {
      await this.checkServiceHealth();
    }, 30000);
  }
  
  async downloadMedia(data) {
    if (!this.isServiceRunning) {
      throw new Error('Service is not running');
    }
    
    try {
      const response = await fetch(`${this.serviceUrl}/api/download`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Download request failed:', error);
      throw error;
    }
  }
  
  async convertMedia(data) {
    if (!this.isServiceRunning) {
      throw new Error('Service is not running');
    }
    
    try {
      const response = await fetch(`${this.serviceUrl}/api/convert`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Convert request failed:', error);
      throw error;
    }
  }
  
  async getTasks() {
    if (!this.isServiceRunning) {
      throw new Error('Service is not running');
    }
    
    try {
      const response = await fetch(`${this.serviceUrl}/api/tasks`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Get tasks failed:', error);
      throw error;
    }
  }
  
  async getFiles(fileType) {
    if (!this.isServiceRunning) {
      throw new Error('Service is not running');
    }
    try {
      let url = `${this.serviceUrl}/api/files`;
      if (fileType) {
        url += `?type=${encodeURIComponent(fileType)}`;
      }
      const response = await fetch(url, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Get files failed:', error);
      throw error;
    }
  }

  async openMediaFolder() {
    if (!this.isServiceRunning) throw new Error('Service is not running');
    const response = await fetch(`${this.serviceUrl}/api/open_folder`, {
      method: 'POST',
      headers: this.getAuthHeaders()
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    return await response.json();
  }
}


// Initialize service manager
const serviceManager = new ServiceManager();

// Handle extension startup
chrome.runtime.onStartup.addListener(() => {
  console.log('MediaTool Extension started');
});

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
  console.log('MediaTool Extension installed/updated:', details.reason);
});