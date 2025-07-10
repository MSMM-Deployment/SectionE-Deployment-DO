#!/usr/bin/env python3
"""
Launcher script for Supabase Database Loader

This script provides a convenient way to load data into the database from the root directory.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Path to the actual loader script
    loader_script = Path("src/database/supabase_loader_simple.py")
    
    if not loader_script.exists():
        print("❌ Error: Database loader script not found at src/database/supabase_loader_simple.py")
        print("Make sure you're running this from the project root directory.")
        return 1
    
    # Pass all command line arguments to the actual loader
    cmd = ["python3", str(loader_script)] + sys.argv[1:]
    
    # Execute the loader
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⌨️ Database loader interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running database loader: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 