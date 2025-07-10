#!/usr/bin/env python3
"""
Launcher script for Auto Resume Parser Watcher

This script provides a convenient way to start the auto watcher from the root directory.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Path to the actual watcher script
    watcher_script = Path("src/automation/start_auto_watcher.py")
    
    if not watcher_script.exists():
        print("❌ Error: Auto watcher script not found at src/automation/start_auto_watcher.py")
        print("Make sure you're running this from the project root directory.")
        return 1
    
    # Pass all command line arguments to the actual watcher
    cmd = ["python3", str(watcher_script)] + sys.argv[1:]
    
    # Execute the watcher
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⌨️ Auto watcher stopped by user")
        return 1
    except Exception as e:
        print(f"❌ Error running auto watcher: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 