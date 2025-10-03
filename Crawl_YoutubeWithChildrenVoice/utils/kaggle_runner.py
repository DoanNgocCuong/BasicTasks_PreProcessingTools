# ============================================================================
# KAGGLE RUNNER FOR YOUTUBE VIDEO CRAWLER - SMART VERSION
# ============================================================================
# Copy and paste this entire script into Kaggle
# It will automatically:
# 1. Use your uploaded project files (upload them manually to Kaggle)
# 2. Install ONLY missing requirements (no reinstall = no runtime restart needed)
# 3. Run the YouTube crawler
# ============================================================================

# Cell 1: Setup and imports
print("Setting up YouTube Video Crawler on Kaggle...")
print("=" * 60)

# Install required packages for the setup
!pip install --upgrade pip

# Cell 2: Project files setup (for Kaggle)
print("\nSTEP 1: PROJECT FILES SETUP")
print("=" * 60)
print("IMPORTANT: Make sure you have uploaded your project files to Kaggle!")
print("1. Upload your project ZIP file to Kaggle (or individual files)")
print("2. Or use git clone if your project is in a repository")
print("3. The script will look for existing files")

import zipfile
import os
import shutil
import subprocess
import json

# Function to upload ZIP file using Kaggle API
def upload_zip_to_kaggle(zip_file_path, dataset_name="youtube-crawler-project"):
    """Upload a ZIP file to Kaggle using the Kaggle API"""
    try:
        # Check if kaggle CLI is available
        result = subprocess.run(['kaggle', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Kaggle CLI not available. Installing...")
            !pip install kaggle
            print("Kaggle CLI installed")
        
        # Check if kaggle.json credentials exist
        kaggle_creds = os.path.expanduser('~/.kaggle/kaggle.json')
        if not os.path.exists(kaggle_creds):
            print("Kaggle credentials not found.")
            print("Please create kaggle.json with your API credentials:")
            print("   Go to: https://www.kaggle.com/settings/account")
            print("   Download kaggle.json and place it in ~/.kaggle/")
            print("   Or upload it manually to this Kaggle notebook")
            return False
        
        # Create dataset if it doesn't exist
        print(f"Creating/updating dataset: {dataset_name}")
        try:
            subprocess.run(['kaggle', 'datasets', 'create', '--name', dataset_name, '--dir-mode', 'zip'], 
                         capture_output=True, text=True)
        except:
            pass  # Dataset might already exist
        
        # Upload the ZIP file
        print(f"Uploading {zip_file_path} to Kaggle...")
        result = subprocess.run([
            'kaggle', 'datasets', 'version', '--message', 'Updated project files', 
            '--path', zip_file_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("ZIP file uploaded successfully to Kaggle!")
            print("You can now access it in the Kaggle input directory")
            return True
        else:
            print(f"Upload failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error uploading to Kaggle: {e}")
        return False

# Function to create and upload project ZIP
def create_and_upload_project_zip():
    """Create a ZIP file of the current project and upload it to Kaggle"""
    try:
        # Create a temporary ZIP file
        import tempfile
        import zipfile
        
        # Get current working directory
        current_dir = os.getcwd()
        project_name = os.path.basename(current_dir)
        
        # Create ZIP file
        zip_filename = f"{project_name}_kaggle_upload.zip"
        print(f"Creating project ZIP: {zip_filename}")
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk('.'):
                # Skip certain directories and files
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv']]
                
                for file in files:
                    if not file.endswith(('.pyc', '.log', '.tmp', '.zip')):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arcname)
                        print(f"  Added: {arcname}")
        
        print(f"ZIP file created: {zip_filename}")
        
        # Try to upload to Kaggle
        if upload_zip_to_kaggle(zip_filename):
            print("Project successfully uploaded to Kaggle!")
            print("You can now access your files in the Kaggle input directory")
        else:
            print("Automatic upload failed. Please upload manually:")
            print(f"   1. Download {zip_filename} from this notebook")
            print(f"   2. Upload it to Kaggle manually")
            print(f"   3. Or use git clone if your project is in a repository")
        
        # Clean up temporary ZIP
        os.remove(zip_filename)
        print(f"Cleaned up temporary file: {zip_filename}")
        
    except Exception as e:
        print(f"Error creating project ZIP: {e}")

# Check if we need to extract a ZIP file
print("Checking for uploaded project files...")
zip_files = [f for f in os.listdir('/kaggle/input') if f.endswith('.zip')]
if zip_files:
    print(f"Found ZIP files: {zip_files}")
    for zip_file in zip_files:
        zip_path = f"/kaggle/input/{zip_file}"
        print(f"Extracting {zip_file}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall('.')
            print(f"{zip_file} extracted successfully")
        except Exception as e:
            print(f"Error extracting {zip_file}: {e}")
else:
    print("No ZIP files found in Kaggle input directory")

# Copy files from input directory if they exist
input_dir = "/kaggle/input"
if os.path.exists(input_dir):
    print(f"\nChecking input directory: {input_dir}")
    input_files = os.listdir(input_dir)
    if input_files:
        print(f"Found {len(input_files)} items in input directory:")
        for item in input_files:
            item_path = os.path.join(input_dir, item)
            if os.path.isfile(item_path) and not item.endswith('.zip'):
                # Copy individual files
                try:
                    shutil.copy2(item_path, '.')
                    print(f"  Copied: {item}")
                except Exception as e:
                    print(f"  Failed to copy {item}: {e}")
            elif os.path.isdir(item_path):
                print(f"  Directory: {item}/")
                # Copy all files from subdirectory
                try:
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        if os.path.isfile(subitem_path):
                            shutil.copy2(subitem_path, '.')
                            print(f"    Copied: {subitem}")
                        elif os.path.isdir(subitem_path):
                            # Copy subdirectory contents
                            subdir_dest = os.path.join('.', subitem)
                            if not os.path.exists(subdir_dest):
                                shutil.copytree(subitem_path, subdir_dest)
                                print(f"    Copied directory: {subitem}/")
                            else:
                                # Copy files from existing subdirectory
                                for subfile in os.listdir(subitem_path):
                                    subfile_path = os.path.join(subitem_path, subfile)
                                    if os.path.isfile(subfile_path):
                                        shutil.copy2(subfile_path, subdir_dest)
                                        print(f"      Copied: {subitem}/{subfile}")
                except Exception as e:
                    print(f"    Failed to copy from {item}: {e}")
            else:
                print(f"  Skipped: {item}")
    else:
        print("Input directory is empty")
else:
    print("Input directory not found")

# Cell 3: Find and navigate to project directory
print("\nSTEP 2: LOCATE PROJECT DIRECTORY")
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
        print("Could not find youtube_video_crawler.py")
        print("Make sure you've uploaded your project files to Kaggle")
        print("\nIf you have files as a dataset, make sure to:")
        print("1. Add the dataset to your notebook")
        print("2. Check that the files are accessible in /kaggle/input/")

if project_dir:
    print(f"Project directory found: {project_dir}")
    os.chdir(project_dir)
    print(f"Changed to directory: {os.getcwd()}")
    
    # List files to verify
    print("\nProject files:")
    for item in os.listdir('.'):
        if os.path.isfile(item):
            print(f"  File: {item}")
        else:
            print(f"  Directory: {item}/")

# Cell 4: Smart package installation (NO REINSTALL = NO RUNTIME RESTART)
print("\nSTEP 3: SMART PACKAGE INSTALLATION")
print("=" * 60)

# Check GPU availability
print("Checking GPU availability...")
try:
    import torch
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        print(f"✅ GPU detected: {gpu_name}")
        print(f"✅ GPU count: {gpu_count}")
        print(f"✅ CUDA version: {torch.version.cuda}")
        
        # Set device to GPU
        device = torch.device("cuda:0")
        print(f"✅ Using device: {device}")
    else:
        print("⚠️  No GPU detected - using CPU")
        device = torch.device("cpu")
except Exception as e:
    print(f"⚠️  GPU check failed: {e}")
    device = torch.device("cpu")

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
        print(f"{package_name} already installed - skipping")
        return True
    else:
        print(f"Installing {package_name}...")
        try:
            !pip install {install_name}
            print(f"{package_name} installed successfully")
            return True
        except Exception as e:
            print(f"Failed to install {package_name}: {e}")
            return False

# Check and install packages one by one (no bulk install = no conflicts)
print("Checking existing packages and installing only what's missing...")

# Core packages
install_if_missing("google", "google-api-python-client")
install_if_missing("yt_dlp", "yt-dlp")
# install_if_missing("whisper", "openai-whisper")  # REMOVED: No longer using Whisper
install_if_missing("ffmpeg", "ffmpeg-python")
install_if_missing("audioread")
install_if_missing("dotenv", "python-dotenv")

# Check PyTorch compatibility and optimize for GPU
print("\nChecking PyTorch compatibility...")
try:
    import torch
    import torchvision
    
    # Check if we need to reinstall PyTorch for GPU
    if torch.cuda.is_available() and not torch.version.cuda:
        print("⚠️  PyTorch CPU version detected but GPU is available")
        print("🔧 Installing PyTorch with CUDA support...")
        !pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
        print("✅ PyTorch with CUDA installed")
        # Reload torch after reinstall
        import importlib
        importlib.reload(torch)
        importlib.reload(torchvision)
    
    print(f"PyTorch version: {torch.__version__}")
    print(f"TorchVision version: {torchvision.__version__}")
    
    if torch.cuda.is_available():
        print(f"✅ CUDA available: {torch.version.cuda}")
        print(f"✅ GPU device: {torch.cuda.get_device_name(0)}")
        print(f"✅ GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Test if there are compatibility issues
    try:
        from transformers import Wav2Vec2Processor
        print("✅ Transformers import test passed")
        
        # Test GPU acceleration for transformers
        if torch.cuda.is_available():
            try:
                processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base")
                print("✅ Transformers GPU acceleration available")
            except Exception as e:
                print(f"⚠️  Transformers GPU test failed: {e}")
        
    except Exception as e:
        print(f"Transformers import failed: {e}")
        print("Fixing PyTorch compatibility...")
        
        # Install compatible versions based on GPU availability
        if torch.cuda.is_available():
            !pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
        else:
            !pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --force-reinstall
        
        !pip install transformers==4.35.0 --force-reinstall
        print("PyTorch compatibility fixed")
        
except Exception as e:
    print(f"PyTorch check failed: {e}")
    print("Installing PyTorch...")
    
    # Install appropriate PyTorch version
    if device.type == "cuda":
        !pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121
    else:
        !pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0
    
    !pip install transformers==4.35.0

print("Package installation completed")

# GPU optimization tips
if device.type == "cuda":
    print("\n🚀 GPU OPTIMIZATION TIPS:")
    print("✅ Use GPU for audio processing and AI models")
    print("✅ Batch process multiple audio files together")
    print("✅ Monitor GPU memory usage during processing")
    print("✅ Consider using mixed precision for large models")
else:
    print("\n💡 CPU OPTIMIZATION TIPS:")
    print("✅ Process files in smaller batches")
    print("✅ Add delays between heavy operations")
    print("✅ Monitor CPU usage and add rate limiting")

# Cell 5: Verify environment files
print("\nSTEP 4: VERIFY ENVIRONMENT FILES")
print("=" * 60)

if os.path.exists('.env'):
    print(".env file found")
else:
    print(".env file not found - make sure you uploaded it")

if os.path.exists('cookies.txt'):
    print("cookies.txt file found")
else:
    print("cookies.txt file not found - make sure you uploaded it")

# Cell 6: Setup output directory for Kaggle
print("\nSTEP 5: SETUP KAGGLE OUTPUT DIRECTORY")
print("=" * 60)

# Create output directory for Kaggle
output_dir = "/kaggle/working"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
print(f"Output directory: {output_dir}")

# Function to save collected URLs to Kaggle output
def save_collected_urls():
    """Save the collected_video_urls.txt to Kaggle output directory"""
    urls_file = "youtube_url_outputs/collected_video_urls.txt"
    if os.path.exists(urls_file):
        try:
            output_file = os.path.join(output_dir, "collected_video_urls.txt")
            shutil.copy2(urls_file, output_file)
            print(f"Saved to Kaggle output: {output_file}")
            return True
        except Exception as e:
            print(f"Save failed: {e}")
            return False
    else:
        print(f"File not found: {urls_file}")
        return False

# Test save function
print("Testing save function...")
save_collected_urls()

# Cell 7: Run the YouTube crawler with auto-save
print("\nSTEP 6: RUN YOUTUBE VIDEO CRAWLER WITH AUTO-SAVE")
print("=" * 60)

if os.path.exists('youtube_video_crawler.py'):
    print("Starting YouTube Video Crawler...")
    print("Auto-saving collected_video_urls.txt every 10 minutes...")
    print("Files will be saved to Kaggle output directory")
    print("Note: The crawler will run in the foreground.")
    print("You can stop it with Ctrl+C when needed.")
    print("\n" + "="*60)
    
    # Import threading for background save
    import threading
    import time
    
    # Flag to control the save thread
    save_running = True
    
    def auto_save_worker():
        """Background worker to save file every 10 minutes"""
        while save_running:
            time.sleep(600)  # Wait 10 minutes (600 seconds)
            if save_running:  # Check again in case we're stopping
                print(f"\nAuto-saving collected_video_urls.txt...")
                save_collected_urls()
    
    # Start the auto-save thread
    save_thread = threading.Thread(target=auto_save_worker, daemon=True)
    save_thread.start()
    print("[START] Auto-save thread started (every 10 minutes)")
    
    try:
        # Run the crawler
        !python youtube_video_crawler.py
    except KeyboardInterrupt:
        print("\nCrawler stopped by user")
    finally:
        # Stop the save thread
        save_running = False
        print("[STOP] Auto-save thread stopped")
        
        # Final save
        print("Final save of collected_video_urls.txt...")
        save_collected_urls()
        
else:
    print("youtube_video_crawler.py not found!")
    print("Make sure you've uploaded your project files to Kaggle")
    print("\nIf you have files as a dataset, make sure to:")
    print("1. Add the dataset to your notebook")
    print("2. Check that the files are accessible in /kaggle/input/")

print("\nSetup complete!")
print("Check the output above for any errors or success messages.")
print("collected_video_urls.txt was auto-saved to Kaggle output every 10 minutes during runtime.")
print("Check the Kaggle output tab to download your results!")
print("No runtime restart needed - packages installed intelligently!")
