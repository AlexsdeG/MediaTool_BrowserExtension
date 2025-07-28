import ffmpeg
from pathlib import Path
from . import utils

def list_downloaded_files(download_base_path: Path) -> list:
    """Finds all files in the download directory and its subdirectories."""
    if not download_base_path.exists():
        return []
    
    # Use glob to find all files in all subdirectories of download
    files = [f for f in download_base_path.glob('**/*') if f.is_file()]
    return files

def list_files_by_type(download_base_path: Path, convert_base_path: Path, file_type: str) -> list:
    """Finds files in both download and convert directories filtered by type (audio or video)."""
    # Define file extensions for different types
    audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    if file_type == 'audio':
        target_extensions = audio_extensions
    elif file_type == 'video':
        target_extensions = video_extensions
    else:
        return []
    
    all_files = []
    
    # Check download directory
    if download_base_path.exists():
        download_files = [f for f in download_base_path.glob('**/*') if f.is_file()]
        all_files.extend(download_files)
    
    # Check convert directory
    if convert_base_path.exists():
        convert_files = [f for f in convert_base_path.glob('**/*') if f.is_file()]
        all_files.extend(convert_files)
    
    # Filter by extension and remove duplicates
    filtered_files = []
    seen_names = set()
    
    for file_path in all_files:
        if file_path.suffix.lower() in target_extensions:
            # Use a combination of name and size to identify unique files
            file_key = f"{file_path.name}_{file_path.stat().st_size}"
            if file_key not in seen_names:
                filtered_files.append(file_path)
                seen_names.add(file_key)
    
    return sorted(filtered_files, key=lambda x: x.name.lower())

def convert_media(input_path: Path, output_path: Path, format: str, file_type: str, progress_callback=None):
    """Converts a media file to the specified format using ffmpeg with progress indication."""
    print(f"\nConverting {input_path.name} to {format.upper()}...")
    print(f"Output will be saved to: {output_path}")
    print("⏳ Starting conversion process...")
    
    # Progress: 20% - Starting
    if progress_callback:
        progress_callback(20)
        
    try:
        # Get input file info for progress estimation
        try:
            probe = ffmpeg.probe(str(input_path))
            duration = float(probe['streams'][0]['duration'])
            print(f"📊 Input file duration: {duration:.1f} seconds")
        except:
            duration = None
            print("📊 Unable to determine file duration")
        
        print("🔄 Processing... Please wait, this may take a while depending on file size and format.")
        
        # Build the ffmpeg command with appropriate settings
        if file_type == 'audio':
            print("🎵 Converting audio file...")
            # Audio conversion with quality settings
            if format in ['mp3']:
                print("🎯 Target: High quality MP3 (320k bitrate)")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), acodec='libmp3lame', audio_bitrate='320k', y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif format in ['wav']:
                print("🎯 Target: Uncompressed WAV")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), acodec='pcm_s16le', y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif format in ['flac']:
                print("🎯 Target: Lossless FLAC")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), acodec='flac', y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif format in ['aac']:
                print("🎯 Target: High quality AAC")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), acodec='aac', audio_bitrate='256k', y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                print(f"🎯 Target: {format.upper()} format")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
        else:
            print("🎬 Converting video file...")
            # Video conversion
            if format in ['mp4']:
                print("🎯 Target: High quality MP4 with H.264 codec")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), vcodec='libx264', acodec='aac', crf=23, y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif format in ['mkv']:
                print("🎯 Target: MKV (copying streams for speed)")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), vcodec='copy', acodec='copy', y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif format in ['webm']:
                print("🎯 Target: WebM with VP9 codec")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), vcodec='libvpx-vp9', acodec='libopus', crf=30, y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif format in ['avi']:
                print("🎯 Target: AVI format")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), vcodec='libx264', acodec='mp3', y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                print(f"🎯 Target: {format.upper()} format")
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), y=None)
                    .run(capture_stdout=True, capture_stderr=True)
                )
        
        print("✅ Conversion successful!")
        
        # Progress: 100% - Done
        if progress_callback:
            progress_callback(100)
        
        # Show output file info
        try:
            output_size = output_path.stat().st_size / (1024 * 1024)
            print(f"📁 Output file size: {output_size:.1f} MB")
        except:
            pass

    except ffmpeg.Error as e:
        print("❌ Conversion failed.")
        print("FFmpeg Error:", e.stderr.decode())
    except Exception as e:
        print(f"❌ Unexpected error during conversion: {e}")

def select_file_type():
    """Shows menu to select between audio and video files."""
    print("\n--- Select Media Type ---")
    print("1: Audio Files (MP3, WAV, FLAC, etc.)")
    print("2: Video Files (MP4, MKV, AVI, etc.)")
    
    while True:
        choice = input("> Select media type (1-2): ").strip()
        if choice == '1':
            return 'audio'
        elif choice == '2':
            return 'video'
        else:
            print("Invalid selection. Please enter 1 or 2.")

def select_target_format(file_type: str, source_format: str):
    """Shows format selection based on file type."""
    print(f"\n--- Select Target Format ---")
    
    if file_type == 'audio':
        formats = {
            '1': 'mp3',
            '2': 'wav', 
            '3': 'flac',
            '4': 'aac',
            '5': 'ogg'
        }
        print("1: MP3 (Compressed, widely supported)")
        print("2: WAV (Uncompressed, high quality)")
        print("3: FLAC (Lossless compression)")
        print("4: AAC (High quality, Apple devices)")
        print("5: OGG (Open source format)")
        
    else:  # video
        formats = {
            '1': 'mp4',
            '2': 'mkv',
            '3': 'avi',
            '4': 'mov',
            '5': 'webm'
        }
        print("1: MP4 (Most compatible)")
        print("2: MKV (High quality, supports subtitles)")
        print("3: AVI (Older format, widely supported)")
        print("4: MOV (Apple format)")
        print("5: WebM (Web optimized)")
    
    # Also show option to extract audio from video
    if file_type == 'video':
        print("\n--- Extract Audio ---")
        print("6: Extract to MP3")
        print("7: Extract to WAV")
        formats.update({'6': 'mp3', '7': 'wav'})
    
    while True:
        format_choice = input("> Select a format number: ").strip()
        if format_choice in formats:
            selected_format = formats[format_choice]
            
            # Check if we're extracting audio from video
            if file_type == 'video' and format_choice in ['6', '7']:
                return selected_format, 'audio'  # Return format and new type
            else:
                return selected_format, file_type  # Return format and same type
        else:
            print("Invalid format selection.")

def run_conversion_menu():
    """Shows an enhanced menu to select media type, file, and format for conversion."""
    # Step 1: Select media type
    file_type = select_file_type()
    
    # Step 2: List files of selected type from both download and convert directories
    daily_download_path, daily_convert_path = utils.get_daily_paths()
    print(f"\n🔍 Searching for {file_type} files in download and convert directories...")
    
    files_to_convert = list_files_by_type(utils.DOWNLOAD_DIR_BASE, utils.CONVERT_DIR_BASE, file_type)
    
    if not files_to_convert:
        print(f"\n❌ No {file_type} files found in download or convert directories.")
        print("💡 Try downloading some media files first, or check if files have the correct extensions.")
        input("Press Enter to return to the main menu.")
        return

    print(f"\n--- Select a {file_type.title()} File to Convert ---")
    print(f"📂 Found {len(files_to_convert)} {file_type} file(s):")
    
    for i, file_path in enumerate(files_to_convert):
        # Show relative path and file size for better overview
        try:
            file_size = file_path.stat().st_size / (1024 * 1024)  # Size in MB
            
            # Determine if file is from download or convert directory
            if utils.DOWNLOAD_DIR_BASE in file_path.parents:
                relative_path = file_path.relative_to(utils.DOWNLOAD_DIR_BASE)
                source_dir = "📥 download"
            else:
                relative_path = file_path.relative_to(utils.CONVERT_DIR_BASE)
                source_dir = "🔄 convert"
            
            print(f"{i + 1}: {relative_path} ({file_size:.1f} MB) [{source_dir}]")
        except Exception as e:
            print(f"{i + 1}: {file_path.name} [error reading file info]")

    # Step 3: Select file
    try:
        choice = int(input(f"\n> Select a {file_type} file number: ")) - 1
        if not 0 <= choice < len(files_to_convert):
            print("❌ Invalid selection.")
            return
        selected_file = files_to_convert[choice]
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
        return

    # Step 4: Select target format
    source_format = selected_file.suffix.lower()[1:]  # Remove the dot
    print(f"\n📋 Selected file: {selected_file.name}")
    print(f"📋 Current format: {source_format.upper()}")
    print(f"📋 File location: {selected_file.parent}")
    
    target_format, output_type = select_target_format(file_type, source_format)
    
    # Step 5: Prepare for conversion
    output_filename = f"{selected_file.stem}.{target_format}"
    safe_output_filename = utils.sanitize_filename(output_filename)
    output_path = daily_convert_path / safe_output_filename
    
    # Check if output file already exists
    if output_path.exists():
        print(f"\n⚠️  Output file already exists: {output_path}")
        overwrite = input("Do you want to overwrite it? (y/N): ").lower().strip()
        if overwrite not in ['y', 'yes']:
            print("❌ Conversion cancelled.")
            input("Press Enter to return to the main menu.")
            return
    
    print(f"\n🚀 Starting conversion process...")
    print(f"📤 Input:  {selected_file}")
    print(f"📥 Output: {output_path}")
    
    # Step 6: Convert
    convert_media(selected_file, output_path, target_format, output_type)
    
    print(f"\n🎉 Conversion completed!")
    print(f"📂 You can find your converted file at: {output_path}")
    
    input("\nPress Enter to return to the main menu.")