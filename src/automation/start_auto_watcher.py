#!/usr/bin/env python3
"""
Startup script for the automatic resume parser watcher

This script will:
1. Check and install required dependencies
2. Start the automatic file watcher
"""

import subprocess
import sys
import os
from pathlib import Path

def check_and_install_dependencies():
    """Check if watchdog is installed and install it if not"""
    try:
        import watchdog
        print("✅ Watchdog already installed")
        return True
    except ImportError:
        print("📦 Installing watchdog dependency...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "watchdog>=3.0.0"])
            print("✅ Watchdog successfully installed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install watchdog: {e}")
            return False

def check_environment():
    """Check if environment is properly configured"""
    from dotenv import load_dotenv
    load_dotenv()
    
    issues = []
    
    if not os.getenv("OPENAI_API_KEY"):
        issues.append("OPENAI_API_KEY not set in .env file")
    
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        issues.append("Supabase credentials (SUPABASE_URL, SUPABASE_KEY) not set in .env file")
    
    if not Path("data/Sample-SectionE").exists():
        issues.append("data/Sample-SectionE folder does not exist")
    
    if not Path("src/parsers/section_e_parser.py").exists():
        issues.append("src/parsers/section_e_parser.py not found")
    
    if not Path("src/database/supabase_loader_simple.py").exists():
        issues.append("src/database/supabase_loader_simple.py not found")
    
    return issues

def main():
    print("🚀 RESUME PARSER AUTO-WATCHER STARTUP")
    print("=" * 45)
    
    # Check dependencies
    if not check_and_install_dependencies():
        print("❌ Failed to install dependencies. Please install manually:")
        print("   pip install watchdog>=3.0.0")
        return
    
    # Check environment
    issues = check_environment()
    if issues:
        print("⚠️  Environment Issues Found:")
        for issue in issues:
            print(f"   - {issue}")
        
        if "OPENAI_API_KEY" in str(issues):
            print("\n❌ OpenAI API key is required. Cannot continue.")
            return
        
        if "Supabase" in str(issues):
            print("\n⚠️  Supabase not configured - database loading will be skipped")
        
        if any("not found" in issue or "does not exist" in issue for issue in issues):
            print("\n❌ Missing required files. Please run from the correct directory.")
            return
    
    print("\n✅ Environment check passed!")
    
    # Start the auto watcher
    try:
        from auto_parser_watcher import main as start_watcher
        start_watcher()
    except ImportError as e:
        print(f"❌ Failed to import auto_parser_watcher: {e}")
        print("Please ensure auto_parser_watcher.py is in the same directory")
    except KeyboardInterrupt:
        print("\n👋 Auto-watcher stopped by user")
    except Exception as e:
        print(f"❌ Error starting auto-watcher: {e}")

if __name__ == "__main__":
    main() 