#!/usr/bin/env python3
"""
Installation Verification Script for Section E Parser

This script verifies that all required dependencies are properly installed
and working correctly for both PDF and Word document processing.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

# Add project root to Python path for src module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def check_python_packages():
    """Check if required Python packages are installed"""
    print("🐍 Checking Python packages...")
    
    required_packages = {
        "openai": "openai",
        "python-dotenv": "dotenv", 
        "pdfminer.six": "pdfminer",
        "pymupdf": "fitz",
        "pdfplumber": "pdfplumber", 
        "PyPDF2": "PyPDF2",
        "python-docx": "docx",
        "docx2txt": "docx2txt",
        "supabase": "supabase"
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - MISSING")
            missing_packages.append(package_name)
    
    return missing_packages

def check_system_dependencies():
    """Check if system dependencies are installed"""
    print("\n🔧 Checking system dependencies...")
    
    # Check antiword
    antiword_path = shutil.which('antiword')
    if antiword_path:
        print(f"  ✅ antiword - Found at {antiword_path}")
        antiword_available = True
    else:
        print("  ❌ antiword - NOT FOUND")
        print("     Install with: brew install antiword (macOS)")
        print("     Install with: sudo apt-get install antiword (Ubuntu/Debian)")
        antiword_available = False
    
    # Check catdoc (optional)
    catdoc_path = shutil.which('catdoc')
    if catdoc_path:
        print(f"  ✅ catdoc - Found at {catdoc_path}")
    else:
        print("  ⚠️  catdoc - NOT FOUND (optional)")
    
    return antiword_available

def test_text_extraction():
    """Test text extraction capabilities"""
    print("\n📄 Testing text extraction...")
    
    try:
        from src.parsers.enhanced_text_extractor import EnhancedTextExtractor
        extractor = EnhancedTextExtractor()
        print("  ✅ EnhancedTextExtractor imported successfully")
        
        # Test with a dummy path to check method availability
        print("  📝 Available extraction methods:")
        print(f"    PyMuPDF: {'✅' if hasattr(extractor, 'extract_text_pymupdf') else '❌'}")
        print(f"    PyPDF2: {'✅' if hasattr(extractor, 'extract_text_pypdf2') else '❌'}")
        print(f"    pdfplumber: {'✅' if hasattr(extractor, 'extract_text_pdfplumber') else '❌'}")
        print(f"    python-docx: {'✅' if hasattr(extractor, 'extract_text_python_docx') else '❌'}")
        print(f"    docx2txt: {'✅' if hasattr(extractor, 'extract_text_docx2txt') else '❌'}")
        print(f"    antiword: {'✅' if hasattr(extractor, 'extract_text_antiword') else '❌'}")
        
        return True
    except Exception as e:
        print(f"  ❌ EnhancedTextExtractor failed: {e}")
        return False

def check_environment_variables():
    """Check if required environment variables are set"""
    print("\n🔐 Checking environment variables...")
    
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        required_vars = {
            'OPENAI_API_KEY': 'OpenAI API key for AI processing',
            'SUPABASE_URL': 'Supabase project URL', 
            'SUPABASE_KEY': 'Supabase service role key'
        }
        
        missing_vars = []
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                # Mask the key for security
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"  ✅ {var} - Set ({masked_value})")
            else:
                print(f"  ❌ {var} - NOT SET ({description})")
                missing_vars.append(var)
        
        return missing_vars
        
    except Exception as e:
        print(f"  ❌ Error checking environment: {e}")
        return ['ALL']

def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n🤖 Testing OpenAI connection...")
    
    try:
        from dotenv import load_dotenv
        import os
        from openai import OpenAI
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("  ❌ OPENAI_API_KEY not set")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("  ✅ OpenAI API connection successful")
        print(f"  ✅ Model: gpt-4-turbo responding")
        return True
        
    except Exception as e:
        print(f"  ❌ OpenAI API test failed: {e}")
        return False

def main():
    """Run all verification checks"""
    print("🔍 Section E Parser Installation Verification")
    print("=" * 50)
    
    all_good = True
    
    # Check Python packages
    missing_packages = check_python_packages()
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        all_good = False
    
    # Check system dependencies
    antiword_available = check_system_dependencies()
    if not antiword_available:
        print("\n⚠️  antiword not available - .doc file processing will be limited")
    
    # Test text extraction
    if not test_text_extraction():
        all_good = False
    
    # Check environment variables
    missing_env_vars = check_environment_variables()
    if missing_env_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_env_vars)}")
        print("Create .env file with required variables")
        all_good = False
    
    # Test OpenAI connection (only if env vars are set)
    if not missing_env_vars:
        if not test_openai_connection():
            all_good = False
    
    # Final summary
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 ALL CHECKS PASSED! Your installation is ready.")
        print("\n📚 Next steps:")
        print("  1. Run: python3 src/parsers/section_e_parser.py --folder data/Sample-SectionE --output results.json")
        print("  2. Run: python3 src/database/supabase_loader_simple.py --input results.json")
        print("  3. Run: python3 src/web/serve_ui.py")
    else:
        print("⚠️  SOME ISSUES FOUND - Please fix the issues above")
        print("\n📖 Installation guide: README.md")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main()) 