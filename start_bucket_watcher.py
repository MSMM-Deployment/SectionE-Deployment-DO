#!/usr/bin/env python3
"""
Start Supabase Bucket Watcher

Simple script to start monitoring the 'msmm-resumes' Supabase bucket
for new uploaded files and automatically process them.

Usage:
python3 start_bucket_watcher.py
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Start the Supabase bucket watcher"""
    print("🚀 Starting Supabase Bucket Resume Automation")
    print("=" * 50)
    
    # Check if .env exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ Error: .env file not found")
        print("💡 Make sure you have SUPABASE_URL and SUPABASE_KEY in .env file")
        sys.exit(1)
    
    # Import and run the bucket watcher
    try:
        from src.automation.supabase_bucket_watcher import SupabaseBucketWatcher
        
        print("✅ Environment configured")
        print("🪣 Initializing bucket watcher...")
        
        # Create watcher with default settings
        watcher = SupabaseBucketWatcher(
            bucket_name="msmm-resumes",
            polling_interval=30  # Check every 30 seconds
        )
        
        print("\n💡 Upload files using the 'Upload Resume' button in the web interface")
        print("💡 Files will be automatically processed and loaded to database")
        print("💡 Use Ctrl+C to stop the watcher\n")
        
        # Start monitoring
        watcher.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 