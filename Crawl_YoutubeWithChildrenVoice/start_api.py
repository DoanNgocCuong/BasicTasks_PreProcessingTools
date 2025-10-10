#!/usr/bin/env python3
"""
YouTube Output Filterer API Startup Script

Simple script to start the API server with proper configuration.
"""

import argparse
import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    try:
        import fastapi
    except ImportError:
        missing_deps.append("fastapi")
    
    try:
        import uvicorn
    except ImportError:
        missing_deps.append("uvicorn")
    
    # Check if filterer module exists
    if not Path("youtube_output_filterer.py").exists():
        missing_deps.append("youtube_output_filterer.py (file not found)")
    
    # Check if audio classifier exists
    if not Path("youtube_audio_classifier.py").exists():
        missing_deps.append("youtube_audio_classifier.py (file not found)")
    
    return missing_deps

def main():
    parser = argparse.ArgumentParser(
        description="Start YouTube Output Filterer API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_api.py                    # Start with default settings
  python start_api.py --port 8080        # Use custom port
  python start_api.py --host 127.0.0.1   # Local access only
  python start_api.py --reload            # Development mode with auto-reload
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    print("YouTube Output Filterer API Startup")
    print("=" * 50)
    
    # Check dependencies
    print("Checking dependencies...")
    missing_deps = check_dependencies()
    
    if missing_deps:
        print("❌ Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\nPlease install missing dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    print("✅ All dependencies available")
    
    # Check default manifest
    default_manifest = Path("final_audio_files/manifest.json")
    if default_manifest.exists():
        print(f"✅ Default manifest found: {default_manifest}")
    else:
        print(f"⚠️  Default manifest not found: {default_manifest}")
        print("   The API will still work with custom manifest paths")
    
    print(f"\nStarting API server...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reload: {args.reload}")
    print(f"Log Level: {args.log_level}")
    print("=" * 50)
    print(f"📖 API Documentation: http://localhost:{args.port}/docs")
    print(f"❤️  Health Check: http://localhost:{args.port}/health")
    print(f"📊 Statistics: http://localhost:{args.port}/stats")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        import uvicorn
        uvicorn.run(
            "api_youtube_filterer:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()