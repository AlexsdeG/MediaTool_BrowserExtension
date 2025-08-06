// MediaTool Extension Content Script
console.log('MediaTool Content Script Loaded');

class MediaDetector {
  constructor() {
    this.mediaData = {
      videos: [],
      audios: [],
      iframes: [],
      links: [],
      youtube: null,
      streaming: []
    };
    this.setupMessageListener();
  }
  
  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === 'detectMedia') {
        try {
          const mediaData = this.detectAllMedia();
          sendResponse(mediaData);
        } catch (error) {
          console.error('Media detection failed:', error);
          sendResponse({ error: error.message });
        }
      }
      return true;
    });
  }
  
  detectAllMedia() {
    this.mediaData = {
      videos: [],
      audios: [],
      iframes: [],
      links: [],
      youtube: null,
      streaming: []
    };
    
    this.detectVideoElements();
    this.detectAudioElements();
    this.detectIframes();
    this.detectMediaLinks();
    this.detectYouTube();
    this.detectStreamingServices();
    this.detectHLSStreams();
    
    console.log('Detected media:', this.mediaData);
    return this.mediaData;
  }
  
  detectVideoElements() {
    document.querySelectorAll('video').forEach((video, index) => {
      const sources = [];
      
      // Direct src
      if (video.src) sources.push(video.src);
      
      // Source elements
      video.querySelectorAll('source').forEach(source => {
        if (source.src) sources.push(source.src);
      });
      
      this.mediaData.videos.push({
        id: `video_${index}`,
        sources,
        title: video.title || video.getAttribute('data-title') || document.title,
        duration: video.duration || 0,
        currentSrc: video.currentSrc,
        poster: video.poster,
        width: video.videoWidth,
        height: video.videoHeight,
        type: 'video_element'
      });
    });
  }
  
  detectAudioElements() {
    document.querySelectorAll('audio').forEach((audio, index) => {
      const sources = [];
      
      if (audio.src) sources.push(audio.src);
      
      audio.querySelectorAll('source').forEach(source => {
        if (source.src) sources.push(source.src);
      });
      
      this.mediaData.audios.push({
        id: `audio_${index}`,
        sources,
        title: audio.title || document.title,
        duration: audio.duration || 0,
        currentSrc: audio.currentSrc,
        type: 'audio_element'
      });
    });
  }
  
  detectIframes() {
    document.querySelectorAll('iframe').forEach((iframe, index) => {
      const src = iframe.src;
      if (src && this.isMediaIframe(src)) {
        this.mediaData.iframes.push({
          id: `iframe_${index}`,
          src,
          title: iframe.title || 'Embedded Media',
          type: 'iframe'
        });
      }
    });
  }
  
  detectMediaLinks() {
    document.querySelectorAll('a').forEach((link, index) => {
      const href = link.href;
      if (href && this.isMediaLink(href)) {
        this.mediaData.links.push({
          id: `link_${index}`,
          url: href,
          title: link.textContent.trim() || link.title || 'Media Link',
          type: 'media_link'
        });
      }
    });
  }
  
  detectYouTube() {
    if (window.location.hostname.includes('youtube.com')) {
      this.mediaData.youtube = this.extractYouTubeData();
    }
  }
  
  extractYouTubeData() {
    try {
      // Try multiple methods to get video ID
      let videoId = new URLSearchParams(window.location.search).get('v');
      
      // If no 'v' parameter, try extracting from URL path (for youtu.be links)
      if (!videoId && window.location.hostname.includes('youtu.be')) {
        videoId = window.location.pathname.substring(1);
      }
      
      // If still no videoId, try extracting from current URL
      if (!videoId) {
        const match = window.location.href.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
        videoId = match ? match[1] : null;
      }
      
      if (!videoId) {
        console.log('No YouTube video ID found');
        return null;
      }
      
      // Try multiple selectors for title with fallbacks
      const titleSelectors = [
        'h1.ytd-video-primary-info-renderer',
        '#title h1',
        'h1.title',
        '.ytd-video-primary-info-renderer h1',
        'h1[class*="title"]',
        'meta[property="og:title"]'
      ];
      
      let videoTitle = 'YouTube Video';
      for (const selector of titleSelectors) {
        const element = document.querySelector(selector);
        if (element) {
          if (selector.includes('meta')) {
            videoTitle = element.getAttribute('content') || videoTitle;
          } else {
            videoTitle = element.textContent?.trim() || videoTitle;
          }
          if (videoTitle && videoTitle !== 'YouTube Video') break;
        }
      }
      
      // Try multiple selectors for channel name
      const channelSelectors = [
        '#owner-name a',
        '.ytd-channel-name a',
        '#channel-name a',
        'a[href*="/channel/"]',
        'a[href*="/@"]'
      ];
      
      let channelName = 'Unknown Channel';
      for (const selector of channelSelectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent?.trim()) {
          channelName = element.textContent.trim();
          break;
        }
      }
      
      console.log('YouTube data extracted:', { videoId, title: videoTitle, channel: channelName });
      
      return {
        videoId,
        title: videoTitle,
        channel: channelName,
        url: window.location.href,
        thumbnail: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
        type: 'youtube'
      };
      
    } catch (error) {
      console.error('YouTube data extraction failed:', error);
      return null;
    }
  }
  
  detectStreamingServices() {
    const hostname = window.location.hostname.toLowerCase();
    
    // Common streaming services
    const streamingServices = [
      'twitch.tv', 'vimeo.com', 'dailymotion.com', 'facebook.com',
      'instagram.com', 'tiktok.com', 'twitter.com', 'x.com'
    ];
    
    streamingServices.forEach(service => {
      if (hostname.includes(service)) {
        this.mediaData.streaming.push({
          service: service.split('.')[0],
          url: window.location.href,
          title: document.title,
          type: 'streaming_service'
        });
      }
    });
  }
  
  detectHLSStreams() {
    try {
      // Look for .m3u8 URLs in scripts and network requests
      const scripts = document.querySelectorAll('script');
      const hlsUrls = new Set();
      
      scripts.forEach(script => {
        const content = script.textContent || script.innerHTML;
        if (content) {
          const m3u8Matches = content.match(/https?:\/\/[^\s"']+\.m3u8[^\s"']*/g);
          if (m3u8Matches) {
            m3u8Matches.forEach(url => hlsUrls.add(url));
          }
        }
      });
      
      // Add detected HLS streams
      hlsUrls.forEach((url, index) => {
        this.mediaData.streaming.push({
          id: `hls_${index}`,
          url: url,
          title: 'HLS Stream',
          type: 'hls_stream'
        });
      });
    } catch (error) {
      console.error('HLS detection failed:', error);
    }
  }
  
  isMediaIframe(src) {
    const mediaPatterns = [
      /youtube\.com\/embed/i,
      /vimeo\.com\/video/i,
      /dailymotion\.com\/embed/i,
      /twitch\.tv\/embed/i,
      /facebook\.com\/plugins\/video/i
    ];
    
    return mediaPatterns.some(pattern => pattern.test(src));
  }
  
  isMediaLink(href) {
    const mediaExtensions = [
      '.mp4', '.webm', '.avi', '.mkv', '.mov', '.wmv', '.flv',
      '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a',
      '.m3u8', '.mpd'
    ];
    
    const lowerHref = href.toLowerCase();
    return mediaExtensions.some(ext => lowerHref.includes(ext)) ||
           lowerHref.includes('youtube.com/watch') ||
           lowerHref.includes('youtu.be/');
  }
}

// Initialize media detector
const mediaDetector = new MediaDetector();

// Auto-detect media when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => mediaDetector.detectAllMedia(), 1000);
  });
} else {
  setTimeout(() => mediaDetector.detectAllMedia(), 1000);
}

// Re-detect media when page changes (for SPAs)
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    setTimeout(() => mediaDetector.detectAllMedia(), 2000);
  }
}).observe(document, { subtree: true, childList: true });