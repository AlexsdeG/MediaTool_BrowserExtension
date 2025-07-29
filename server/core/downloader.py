import requests
from pytube import YouTube
from tqdm import tqdm
from pathlib import Path
from bs4 import BeautifulSoup
import subprocess
import re
import tempfile
import os
import shutil
from . import utils

def download_direct_url(url: str, output_path: Path, headers=None):
    """Downloads a file from a direct URL with a progress bar."""
    try:
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        total_size = int(response.headers.get('content-length', 0))
        filename = url.split('/')[-1]
        
        # Sanitize filename
        safe_filename = utils.sanitize_filename(filename)
        if not safe_filename: # Handle cases where URL ends with /
            safe_filename = "downloaded_file"

        file_path = output_path / safe_filename
        
        print(f"Downloading: {safe_filename}")
        with tqdm(
            total=total_size, 
            unit='B', 
            unit_scale=True, 
            unit_divisor=1024,
            desc=safe_filename
        ) as pbar:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        print(f"✅ Download complete: {file_path}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading direct URL: {e}")


### HLS Stream Downloading
def download_hls_stream(m3u8_url: str, output_path: Path, title: str = None, referer: str = None):
    """Downloads HLS stream using ffmpeg with proper headers."""
    try:
        # Create a safe filename
        if title:
            safe_filename = utils.sanitize_filename(title)
            if not safe_filename.endswith('.mp4'):
                safe_filename += '.mp4'
        else:
            safe_filename = "video_stream.mp4"
        
        file_path = output_path / safe_filename
        
        print(f"Downloading HLS stream: {safe_filename}")
        print("This may take a while depending on the video length...")
        
        # Build ffmpeg command with headers
        ffmpeg_cmd = ['ffmpeg']
        
        # Add headers if we have a referer
        if referer:
            ffmpeg_cmd.extend([
                '-headers', f'Referer: {referer}',
                '-headers', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ])
        else:
            ffmpeg_cmd.extend([
                '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ])
        
        ffmpeg_cmd.extend([
            '-i', m3u8_url,
            '-c', 'copy',  # Copy streams without re-encoding for speed
            '-y',  # Overwrite output file without asking
            str(file_path)
        ])
        
        print(f"Running ffmpeg command...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ HLS download complete: {file_path}")
        else:
            print(f"❌ FFmpeg error: {result.stderr}")
            # Try alternative method
            print("Trying alternative download method...")
            download_hls_alternative(m3u8_url, output_path, title, referer)
            
    except FileNotFoundError:
        print("❌ FFmpeg not found. Please install FFmpeg to download HLS streams.")
        print("You can download it from: https://ffmpeg.org/download.html")
    except Exception as e:
        print(f"❌ Error downloading HLS stream: {e}")

def download_hls_alternative(m3u8_url: str, output_path: Path, title: str = None, referer: str = None):
    """Alternative method to download HLS stream by downloading segments manually."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if referer:
            headers['Referer'] = referer
        
        # Download the m3u8 playlist
        print("Downloading playlist...")
        playlist_response = requests.get(m3u8_url, headers=headers)
        playlist_response.raise_for_status()
        
        playlist_content = playlist_response.text
        print(f"Playlist content preview: {playlist_content[:500]}...")
        
        # Check if this is a master playlist (contains #EXT-X-STREAM-INF)
        if '#EXT-X-STREAM-INF' in playlist_content:
            print("Master playlist detected, finding best quality stream...")
            
            # Parse master playlist to find the best quality stream
            lines = playlist_content.split('\n')
            best_bandwidth = 0
            best_playlist_url = None
            
            for i, line in enumerate(lines):
                if line.startswith('#EXT-X-STREAM-INF'):
                    # Extract bandwidth
                    bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
                    if bandwidth_match:
                        bandwidth = int(bandwidth_match.group(1))
                        # Get the next line which should be the playlist URL
                        if i + 1 < len(lines):
                            playlist_url = lines[i + 1].strip()
                            if playlist_url and bandwidth > best_bandwidth:
                                best_bandwidth = bandwidth
                                best_playlist_url = playlist_url
            
            if best_playlist_url:
                # Make URL absolute if relative
                if not best_playlist_url.startswith('http'):
                    base_url = '/'.join(m3u8_url.split('/')[:-1]) + '/'
                    best_playlist_url = base_url + best_playlist_url
                
                print(f"Found best quality stream: {best_playlist_url} (bandwidth: {best_bandwidth})")
                
                # Recursively download the actual playlist
                return download_hls_alternative(best_playlist_url, output_path, title, referer)
            else:
                print("❌ No valid stream found in master playlist")
                return
        
        # Parse the playlist to get segment URLs
        segments = []
        base_url = '/'.join(m3u8_url.split('/')[:-1]) + '/'
        
        lines = playlist_content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('http'):
                    segments.append(line)
                else:
                    segments.append(base_url + line)
        
        if not segments:
            print("❌ No video segments found in playlist")
            print(f"Playlist content:\n{playlist_content}")
            return
        
        print(f"Found {len(segments)} video segments")
        
        # Validate that we have a reasonable number of segments for a 1h 15min video
        # (should be hundreds of segments, not just 5)
        if len(segments) < 10:
            print(f"⚠️  Warning: Only {len(segments)} segments found. This seems too few for a long video.")
            print("This might be a master playlist or incomplete playlist.")
        
        # Create a safe filename
        if title:
            safe_filename = utils.sanitize_filename(title)
            if not safe_filename.endswith('.mp4'):
                safe_filename += '.mp4'
        else:
            safe_filename = "video_stream.mp4"
        
        file_path = output_path / safe_filename
        
        # Create a local temporary directory in the data folder
        temp_dir = utils.TEMP_DIR_BASE
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a unique subdirectory for this download
        import time
        temp_download_dir = temp_dir / f"hls_download_{int(time.time())}"
        temp_download_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            segment_files = []
            failed_segments = 0
            
            # Download all segments
            print("Downloading video segments...")
            with tqdm(total=len(segments), desc="Segments") as pbar:
                for i, segment_url in enumerate(segments):
                    try:
                        segment_response = requests.get(segment_url, headers=headers, timeout=30)
                        segment_response.raise_for_status()
                        
                        # Check if we actually got video data
                        if len(segment_response.content) < 1000:  # Segments should be much larger
                            print(f"⚠️  Warning: Segment {i} is suspiciously small ({len(segment_response.content)} bytes)")
                        
                        segment_file = temp_download_dir / f"segment_{i:04d}.ts"
                        with open(segment_file, 'wb') as f:
                            f.write(segment_response.content)
                        
                        segment_files.append(segment_file)
                        pbar.update(1)
                        
                    except Exception as e:
                        print(f"Error downloading segment {i}: {e}")
                        failed_segments += 1
                        continue
            
            if not segment_files:
                print("❌ Failed to download any segments")
                return
            
            if failed_segments > 0:
                print(f"⚠️  Warning: {failed_segments} segments failed to download")
            
            print(f"Successfully downloaded {len(segment_files)} segments")
            
            # Calculate total size to verify we have substantial content
            total_size = sum(segment_file.stat().st_size for segment_file in segment_files)
            print(f"Total downloaded size: {total_size / (1024*1024):.2f} MB")
            
            if total_size < 10 * 1024 * 1024:  # Less than 10MB for a 1h+ video is suspicious
                print("⚠️  Warning: Total download size seems too small for the expected video length")
            
            # Method 1: Try direct concatenation using binary mode
            print("Concatenating segments using binary merge...")
            try:
                with open(file_path, 'wb') as output_file:
                    for segment_file in segment_files:
                        with open(segment_file, 'rb') as input_file:
                            shutil.copyfileobj(input_file, output_file)
                
                # Verify the final file size
                final_size = file_path.stat().st_size
                print(f"Final file size: {final_size / (1024*1024):.2f} MB")
                
                print(f"✅ HLS download complete (binary merge): {file_path}")
                return
                
            except Exception as e:
                print(f"Binary merge failed: {e}")
                print("Trying ffmpeg concatenation...")
            
            # Method 2: Use ffmpeg with proper file list format
            try:
                # Create a file list for ffmpeg with proper escaping
                filelist_path = temp_download_dir / "filelist.txt"
                with open(filelist_path, 'w', encoding='utf-8') as f:
                    for segment_file in segment_files:
                        # Use forward slashes and escape the path properly
                        escaped_path = str(segment_file).replace('\\', '/')
                        f.write(f"file '{escaped_path}'\n")
                
                # Concatenate segments using ffmpeg
                print("Concatenating segments with ffmpeg...")
                concat_cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(filelist_path),
                    '-c', 'copy',
                    '-y',
                    str(file_path)
                ]
                
                result = subprocess.run(concat_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    final_size = file_path.stat().st_size
                    print(f"Final file size: {final_size / (1024*1024):.2f} MB")
                    print(f"✅ HLS download complete (ffmpeg): {file_path}")
                else:
                    print(f"❌ Error concatenating segments with ffmpeg: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ Error in ffmpeg concatenation: {e}")
                
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_download_dir)
                print("Temporary files cleaned up")
            except Exception as e:
                print(f"Warning: Could not clean up temporary files: {e}")
                
    except Exception as e:
        print(f"❌ Error in alternative HLS download: {e}")

def extract_video_sources(html_content: str):
    """Extracts video sources from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    sources = []
    
    # Look for video tags
    videos = soup.find_all('video')
    for video in videos:
        # Check for src attribute on video tag
        if video.get('src'):
            sources.append(video.get('src'))
        
        # Check for source tags within video
        source_tags = video.find_all('source')
        for source in source_tags:
            if source.get('src'):
                sources.append(source.get('src'))
    
    # Also look for standalone source tags
    standalone_sources = soup.find_all('source')
    for source in standalone_sources:
        if source.get('src'):
            sources.append(source.get('src'))
    
    return sources

def extract_video_title(html_content: str):
    """Attempts to extract video title from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find title in data-plyr-config
    video = soup.find('video')
    if video and video.get('data-plyr-config'):
        config = video.get('data-plyr-config')
        title_match = re.search(r'"title":\s*"([^"]+)"', config)
        if title_match:
            return title_match.group(1)
    
    # Try to find title in page title
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text().strip()
    
    return None

def download_from_iframe(url: str, output_path: Path, referer: str = None):
    """Attempts to find and download media from an iframe source."""
    try:
        print(f"Fetching iframe page: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if referer:
            headers['Referer'] = referer
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        page_content = response.text
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # First, try to find video sources directly in this page
        video_sources = extract_video_sources(page_content)
        
        if video_sources:
            print(f"Found {len(video_sources)} video source(s)")
            
            # Extract title if available
            title = extract_video_title(page_content)
            
            for i, source in enumerate(video_sources):
                print(f"Source {i+1}: {source}")
                
                # Handle different types of sources
                if source.startswith('blob:'):
                    print(f"⚠️  Skipping blob URL (not downloadable): {source}")
                    continue
                elif source.endswith('.m3u8'):
                    print("Detected HLS stream (.m3u8)")
                    download_hls_stream(source, output_path, title, url)
                    return
                elif any(source.endswith(ext) for ext in ['.mp4', '.mp3', '.wav', '.mov', '.mkv']):
                    print("Detected direct media file")
                    download_direct_url(source, output_path, headers)
                    return
                else:
                    print(f"Unknown source type, attempting direct download: {source}")
                    download_direct_url(source, output_path, headers)
                    return
        
        # If no video sources found, try to find iframe
        iframe = soup.find('iframe')
        if iframe:
            iframe_src = iframe.get('src')
            if iframe_src:
                # If the src is protocol-relative (starts with //), add https:
                if iframe_src.startswith('//'):
                    iframe_src = 'https:' + iframe_src
                    
                print(f"Found iframe src: {iframe_src}")
                
                # Recursively process the iframe content
                download_from_iframe(iframe_src, output_path, url)
                return
        
        print("❌ No video sources or iframes found on the page.")

    except Exception as e:
        print(f"❌ Error processing iframe URL: {e}")

def handle_download(url: str, download_path: Path, progress_callback=None):
    """
    Determines the type of URL and calls the correct download function.
    Optionally accepts a progress_callback(progress: int) for reporting progress (0-100).
    """
    url = url.strip()
    if not url:
        print("URL cannot be empty.")
        return

    # Progress: 20% - Starting
    if progress_callback:
        progress_callback(5)

    # Only one URL is handled per call
    if 'youtube.com' in url or 'youtu.be' in url:
        download_youtube(url, download_path)
    elif url.endswith(('.mp3', '.mp4', '.wav', '.mov', '.mkv')):
        download_direct_url(url, download_path)
    elif url.endswith('.m3u8'):
        download_hls_stream(url, download_path)
    else:
        # Assume it might be a page with an iframe or video content
        print("URL is not a direct media link or YouTube. Attempting to find video content...")
        download_from_iframe(url, download_path)

    # Progress: 100% - Done
    if progress_callback:
        progress_callback(100)
        
        
### Youtube

def download_youtube(url: str, output_path: Path):
    """Downloads a YouTube video with a progress bar."""
    try:
        print("Attempting to download YouTube video...")
        
        # Try different approaches for YouTube download
        try:
            # First attempt with default settings
            yt = YouTube(url)
            print(f"Video Title: {yt.title}")
            print(f"Video Length: {yt.length} seconds")
            
        except Exception as e:
            print(f"First attempt failed: {e}")
            print("Trying with different user agent...")
            
            # Try with custom user agent and other options
            try:
                yt = YouTube(
                    url,
                    use_oauth=False,
                    allow_oauth_cache=False
                )
                print(f"Video Title: {yt.title}")
                print(f"Video Length: {yt.length} seconds")
                
            except Exception as e2:
                print(f"Second attempt failed: {e2}")
                print("YouTube download failed. This might be due to:")
                print("1. Age-restricted content")
                print("2. Private/unavailable video")
                print("3. Regional restrictions")
                print("4. YouTube API changes")
                print("\nTrying alternative method with yt-dlp...")
                
                # Fallback to yt-dlp if available
                return download_youtube_ytdlp(url, output_path)

        # Get available streams
        print("Getting available streams...")
        streams = yt.streams.filter(progressive=True, file_extension='mp4')
        
        if not streams:
            print("No progressive MP4 streams found. Trying adaptive streams...")
            # Try adaptive streams (video + audio separate)
            video_streams = yt.streams.filter(adaptive=True, file_extension='mp4', type='video')
            audio_streams = yt.streams.filter(adaptive=True, file_extension='mp4', type='audio')
            
            if video_streams and audio_streams:
                print("Found adaptive streams. Will download video and audio separately then merge.")
                return download_youtube_adaptive(yt, output_path, video_streams, audio_streams)
            else:
                # Try any available stream
                streams = yt.streams.filter(file_extension='mp4')
                if not streams:
                    streams = yt.streams
        
        if not streams:
            print("❌ No downloadable streams found.")
            return

        # Select the best quality stream
        stream = streams.get_highest_resolution()
        if not stream:
            stream = streams.first()
            
        print(f"Selected stream: {stream.resolution or 'audio'} - {stream.mime_type}")

        safe_filename = utils.sanitize_filename(f"{yt.title}.{stream.subtype}")
        print(f"Downloading: {safe_filename}")
        
        # Download with progress bar
        if hasattr(stream, 'filesize') and stream.filesize:
            # Using TQDM for progress if filesize is known
            with tqdm(
                total=stream.filesize, 
                unit='B', 
                unit_scale=True, 
                unit_divisor=1024,
                desc=safe_filename[:50]
            ) as pbar:
                def on_progress(chunk, file_handler, bytes_remaining):
                    pbar.update(stream.filesize - bytes_remaining - pbar.n)

                yt.register_on_progress_callback(on_progress)
                stream.download(output_path=str(output_path), filename=safe_filename)
        else:
            # Simple download without progress bar
            print("Downloading... (progress not available)")
            stream.download(output_path=str(output_path), filename=safe_filename)

        print(f"✅ YouTube download complete: {output_path / safe_filename}")

    except Exception as e:
        print(f"❌ Error downloading YouTube video: {e}")
        print("Trying alternative method with yt-dlp...")
        download_youtube_ytdlp(url, output_path)

def download_youtube_adaptive(yt, output_path: Path, video_streams, audio_streams):
    """Downloads YouTube video using adaptive streams (separate video and audio)."""
    try:
        # Select best video and audio streams
        video_stream = video_streams.get_highest_resolution()
        audio_stream = audio_streams.get_audio_only()
        
        if not video_stream or not audio_stream:
            print("❌ Could not find suitable video or audio streams")
            return
            
        print(f"Video stream: {video_stream.resolution} - {video_stream.mime_type}")
        print(f"Audio stream: {audio_stream.abr} - {audio_stream.mime_type}")
        
        # Create temporary directory for separate files
        temp_dir = utils.TEMP_DIR_BASE
        temp_dir.mkdir(exist_ok=True)
        
        import time
        temp_download_dir = temp_dir / f"youtube_download_{int(time.time())}"
        temp_download_dir.mkdir(exist_ok=True)
        
        try:
            # Download video and audio separately
            print("Downloading video stream...")
            video_file = temp_download_dir / f"video.{video_stream.subtype}"
            video_stream.download(output_path=str(temp_download_dir), filename=f"video.{video_stream.subtype}")
            
            print("Downloading audio stream...")
            audio_file = temp_download_dir / f"audio.{audio_stream.subtype}"
            audio_stream.download(output_path=str(temp_download_dir), filename=f"audio.{audio_stream.subtype}")
            
            # Merge using ffmpeg
            safe_filename = utils.sanitize_filename(f"{yt.title}.mp4")
            output_file = output_path / safe_filename
            
            print("Merging video and audio...")
            merge_cmd = [
                'ffmpeg',
                '-i', str(video_file),
                '-i', str(audio_file),
                '-c', 'copy',
                '-y',
                str(output_file)
            ]
            
            result = subprocess.run(merge_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ YouTube download complete (adaptive): {output_file}")
            else:
                print(f"❌ Error merging streams: {result.stderr}")
                
        finally:
            # Clean up temporary files
            try:
                shutil.rmtree(temp_download_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temporary files: {e}")
                
    except Exception as e:
        print(f"❌ Error in adaptive YouTube download: {e}")

def download_youtube_ytdlp(url: str, output_path: Path):
    """Fallback method using yt-dlp if available."""
    try:
        print("Attempting download with yt-dlp...")
        
        # Check if yt-dlp is available
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ yt-dlp not found. Please install it with: pip install yt-dlp")
            print("Or download from: https://github.com/yt-dlp/yt-dlp")
            return
            
        # Use yt-dlp to download
        ytdlp_cmd = [
            'yt-dlp',
            '--format', 'best[height<=720]',  # Limit to 720p for reliability
            '--output', str(output_path / '%(title)s.%(ext)s'),
            '--no-playlist',
            url
        ]
        
        print("Running yt-dlp...")
        result = subprocess.run(ytdlp_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ YouTube download complete (yt-dlp)")
            print(result.stdout)
        else:
            print(f"❌ yt-dlp error: {result.stderr}")
            
    except FileNotFoundError:
        print("❌ yt-dlp not found. Please install it with: pip install yt-dlp")
    except Exception as e:
        print(f"❌ Error with yt-dlp download: {e}")