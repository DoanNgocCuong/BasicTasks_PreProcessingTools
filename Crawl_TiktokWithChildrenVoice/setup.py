#!/usr/bin/env python3
"""
TikTok Children's Voice Crawler - Setup Helper

This script helps set up the TikTok crawler environment and guides users 
through the initial configuration process.
"""

import os
import sys
import shutil
from pathlib import Path

def create_env_file():
    """Create .env file from .env.example."""
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if not env_example.exists():
        print("❌ .env.example file not found")
        return False
    
    try:
        shutil.copy2(env_example, env_file)
        print("✅ Created .env file from .env.example")
        print("📝 Please edit .env file and add your TikTok RapidAPI key")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        ("requests", "HTTP requests"),
        ("python-dotenv", "Environment variable loading"),
        ("librosa", "Audio processing"),
        ("soundfile", "Audio file handling"),
        ("numpy", "Numerical computing"),
        ("transformers", "ML models (optional for children's voice detection)"),
        ("torch", "PyTorch (optional for children's voice detection)"),
        ("whisper", "OpenAI Whisper (optional for transcription)"),
        ("groq", "Groq API (optional for transcription)")
    ]
    
    missing_packages = []
    optional_missing = []
    
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            if package in ["transformers", "torch", "whisper", "groq"]:
                print(f"⚠️ {package} - {description} (optional)")
                optional_missing.append(package)
            else:
                print(f"❌ {package} - {description} (required)")
                missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    elif optional_missing:
        print(f"\n⚠️ Optional packages missing: {', '.join(optional_missing)}")
        print("For full functionality, install with:")
        print("pip install " + " ".join(optional_missing))
        return True
    else:
        print("\n✅ All dependencies are installed!")
        return True

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    print("\n🔍 Checking FFmpeg...")
    
    import subprocess
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg is installed and working")
            return True
        else:
            print("⚠️ FFmpeg command exists but may not be working properly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ FFmpeg not found")
        print("📝 Please install FFmpeg:")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        print("   Mac: brew install ffmpeg")
        print("   Linux: sudo apt install ffmpeg (Ubuntu/Debian)")
        return False
    except Exception as e:
        print(f"⚠️ Error checking FFmpeg: {e}")
        return False

def create_output_directories():
    """Create necessary output directories."""
    print("\n🔍 Creating output directories...")
    
    directories = [
        "tiktok_url_outputs",
        "temp_audio",
        "final_audio_files"
    ]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        try:
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Created directory: {dir_name}")
        except Exception as e:
            print(f"❌ Failed to create directory {dir_name}: {e}")
            return False
    
    return True

def show_api_key_instructions():
    """Show instructions for getting TikTok RapidAPI key."""
    print("\n📋 TikTok RapidAPI Key Setup Instructions:")
    print("=" * 50)
    print("1. Go to: https://rapidapi.com/Sonjoy/api/tiktok-api23")
    print("2. Create a RapidAPI account (if you don't have one)")
    print("3. Subscribe to the TikTok API (free tier available)")
    print("4. Copy your API key from the dashboard")
    print("5. Edit the .env file and replace 'your_tiktok_api_key_here' with your actual key")
    print("\nExample .env content:")
    print("TIKTOK_API_KEY=your_actual_api_key_here")
    print("DEBUG_MODE=true")
    print("MAX_WORKERS=4")

def main():
    """Run the setup process."""
    print("🚀 TikTok Children's Voice Crawler - Setup Helper")
    print("=" * 60)
    
    steps = [
        ("Create .env file", create_env_file),
        ("Check dependencies", check_dependencies),
        ("Check FFmpeg", check_ffmpeg),
        ("Create output directories", create_output_directories)
    ]
    
    all_good = True
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            if not step_func():
                all_good = False
        except Exception as e:
            print(f"❌ {step_name} failed: {e}")
            all_good = False
    
    # Always show API key instructions
    show_api_key_instructions()
    
    print("\n" + "=" * 60)
    if all_good:
        print("🎉 Setup completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Edit .env file and add your TikTok RapidAPI key")
        print("2. Run: python test_system.py (to verify everything works)")
        print("3. Run: python tiktok_video_crawler.py (to start crawling)")
    else:
        print("⚠️ Setup completed with issues. Please fix the problems above.")
        print("Run this setup script again after fixing issues.")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())