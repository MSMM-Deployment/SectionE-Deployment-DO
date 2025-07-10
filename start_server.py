#!/usr/bin/env python3
"""
Launcher script for Section E Web Server

This script provides a convenient way to start the web interface from the root directory.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Path to the actual web server script
    server_script = Path("src/web/serve_ui.py")
    
    if not server_script.exists():
        print("❌ Error: Web server script not found at src/web/serve_ui.py")
        print("Make sure you're running this from the project root directory.")
        return 1
    
    # Pass all command line arguments to the actual server
    cmd = ["python3", str(server_script)] + sys.argv[1:]
    
    # Execute the server
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⌨️ Web server stopped by user")
        return 1
    except Exception as e:
        print(f"❌ Error running web server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 