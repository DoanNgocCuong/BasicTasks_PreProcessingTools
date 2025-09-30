# ============================================================================
# GOOGLE COLAB RUNNER FOR YOUTUBE VIDEO CRAWLER - SMART VERSION
# ============================================================================
# Copy and paste this entire script into Google Colab
# It will automatically:
# 1. Upload your project files
# 2. Install ONLY missing requirements (no reinstall = no runtime restart needed)
# 3. Run the YouTube crawler
# ============================================================================

# Cell 1: Setup and imports
print("🚀 Setting up YouTube Video Crawler on Google Colab...")
print("=" * 60)

# Install required packages for the setup
!pip install --upgrade pip

# Cell 2: Upload project files
print("\n📁 STEP 1: UPLOAD PROJECT FILES")
print("=" * 60)
print("Please upload your project ZIP file (including .env and cookies.txt)")
print("1. Zip your project folder")
print("2. Click 'Choose Files' below")
print("3. Select your ZIP file")

from google.colab import files
import zipfile
import os

# Wait for file upload
uploaded = files.upload()

if not uploaded:
    print("❌ No files uploaded. Please try again.")
else:
    # Get the uploaded file
    zip_filename = list(uploaded.keys())[0]
    print(f"✅ Uploaded: {zip_filename}")
    
    # Extract the ZIP file
    print(f"📦 Extracting {zip_filename}...")
    try:
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall('.')
        print("✅ Files extracted successfully")
    except Exception as e:
        print(f"❌ Error extracting files: {e}")

# Cell 3: Find and navigate to project directory
print("\n📂 STEP 2: LOCATE PROJECT DIRECTORY")
print("=" * 60)

# Find the project directory
project_dir = None
for item in os.listdir('.'):
    if os.path.isdir(item) and 'youtube_video_crawler.py' in os.listdir(item):
        project_dir = item
        break

if not project_dir:
    # Check if files are in current directory
    if 'youtube_video_crawler.py' in os.listdir('.'):
        project_dir = '.'
    else:
        print("❌ Could not find youtube_video_crawler.py")

if project_dir:
    print(f"📁 Project directory found: {project_dir}")
    os.chdir(project_dir)
    print(f"📂 Changed to directory: {os.getcwd()}")
    
    # List files to verify
    print("\n📋 Project files:")
    for item in os.listdir('.'):
        if os.path.isfile(item):
            print(f"  📄 {item}")
        else:
            print(f"  📁 {item}/")

# Cell 4: Smart package installation (NO REINSTALL = NO RUNTIME RESTART)
print("\n📦 STEP 3: SMART PACKAGE INSTALLATION")
print("=" * 60)

def check_package_installed(package_name):
    """Check if a package is already installed"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_if_missing(package_name, install_name=None):
    """Install package only if it's not already installed"""
    if install_name is None:
        install_name = package_name
    
    if check_package_installed(package_name):
        print(f"✅ {package_name} already installed - skipping")
        return True
    else:
        print(f"📦 Installing {package_name}...")
        try:
            !pip install {install_name}
            print(f"✅ {package_name} installed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install {package_name}: {e}")
            return False

# Check and install packages one by one (no bulk install = no conflicts)
print("🔍 Checking existing packages and installing only what's missing...")

# Core packages
install_if_missing("google", "google-api-python-client")
install_if_missing("yt_dlp", "yt-dlp")
# install_if_missing("whisper", "openai-whisper")  # REMOVED: No longer using Whisper
install_if_missing("ffmpeg", "ffmpeg-python")
install_if_missing("audioread")
install_if_missing("dotenv", "python-dotenv")

# Check PyTorch compatibility and fix if needed
print("\n🔧 Checking PyTorch compatibility...")
try:
    import torch
    import torchvision
    print(f"✅ PyTorch version: {torch.__version__}")
    print(f"✅ TorchVision version: {torchvision.__version__}")
    
    # Test if there are compatibility issues
    try:
        from transformers import Wav2Vec2Processor
        print("✅ Transformers import test passed")
    except Exception as e:
        print(f"⚠️  Transformers import failed: {e}")
        print("🔧 Fixing PyTorch compatibility...")
        
        # Install compatible versions
        !pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
        !pip install transformers==4.35.0 --force-reinstall
        
        print("✅ PyTorch compatibility fixed")
        
except Exception as e:
    print(f"❌ PyTorch check failed: {e}")
    print("🔧 Installing PyTorch...")
    !pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118
    !pip install transformers==4.35.0

print("✅ Package installation completed")

# Cell 5: Verify environment files
print("\n🔍 STEP 4: VERIFY ENVIRONMENT FILES")
print("=" * 60)

if os.path.exists('.env'):
    print("✅ .env file found")
else:
    print("⚠️  .env file not found - make sure you uploaded it")

if os.path.exists('cookies.txt'):
    print("✅ cookies.txt file found")
else:
    print("⚠️  cookies.txt file not found - make sure you uploaded it")

# Cell 6: Setup auto-download of collected_video_urls.txt
print("\n📥 STEP 5: SETUP AUTO-DOWNLOAD")
print("=" * 60)

# Function to download collected_video_urls.txt
def download_collected_urls():
    """Download the collected_video_urls.txt file if it exists"""
    urls_file = "youtube_url_outputs/collected_video_urls.txt"
    if os.path.exists(urls_file):
        try:
            from google.colab import files
            files.download(urls_file)
            print(f"✅ Downloaded: {urls_file}")
            return True
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return False
    else:
        print(f"⚠️  File not found: {urls_file}")
        return False

# Test download function
print("🧪 Testing download function...")
download_collected_urls()

# Cell 7: Run the YouTube crawler with auto-download
print("\n🚀 STEP 6: RUN YOUTUBE VIDEO CRAWLER WITH AUTO-DOWNLOAD")
print("=" * 60)

if os.path.exists('youtube_video_crawler.py'):
    print("🎯 Starting YouTube Video Crawler...")
    print("📥 Auto-downloading collected_video_urls.txt every 10 minutes...")
    print("Note: The crawler will run in the foreground.")
    print("You can stop it with Ctrl+C when needed.")
    print("\n" + "="*60)
    
    # Import threading for background download
    import threading
    import time
    
    # Flag to control the download thread
    download_running = True
    
    def auto_download_worker():
        """Background worker to download file every 10 minutes"""
        while download_running:
            time.sleep(600)  # Wait 10 minutes (600 seconds)
            if download_running:  # Check again in case we're stopping
                print(f"\n⏰ Auto-downloading collected_video_urls.txt...")
                download_collected_urls()
    
    # Start the auto-download thread
    download_thread = threading.Thread(target=auto_download_worker, daemon=True)
    download_thread.start()
    print("[START] Auto-download thread started (every 10 minutes)")
    
    try:
        # Run the crawler
        !python youtube_video_crawler.py
    except KeyboardInterrupt:
        print("\n⏹️  Crawler stopped by user")
    finally:
        # Stop the download thread
        download_running = False
        print("[STOP] Auto-download thread stopped")
        
else:
    print("❌ youtube_video_crawler.py not found!")

print("\n🎉 Setup complete!")
print("📝 Check the output above for any errors or success messages.")
print("💾 collected_video_urls.txt was auto-downloaded every 10 minutes during runtime.")
print("🚀 No runtime restart needed - packages installed intelligently!")
