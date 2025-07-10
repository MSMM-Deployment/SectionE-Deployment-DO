#!/usr/bin/env python3
"""
Launcher script for Section E Resume Parser

This script provides a convenient way to run the parser from the root directory
without needing to remember the new folder structure.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Path to the actual parser script
    parser_script = Path("src/parsers/section_e_parser.py")
    
    if not parser_script.exists():
        print("❌ Error: Parser script not found at src/parsers/section_e_parser.py")
        print("Make sure you're running this from the project root directory.")
        return 1
    
    # Pass all command line arguments to the actual parser
    cmd = ["python3", str(parser_script)] + sys.argv[1:]
    
    # Execute the parser
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⌨️ Parser interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running parser: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 