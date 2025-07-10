#!/usr/bin/env python3
"""
Build script for Netlify deployment

This script prepares the application for deployment by:
1. Creating the dist directory for static files
2. Copying and processing HTML files 
3. Copying necessary data files
4. Setting up proper directory structure
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

def create_dist_directory():
    """Create and clean the dist directory"""
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    dist_dir.mkdir()
    print("✅ Created dist directory")
    return dist_dir

def copy_html_files(dist_dir):
    """Copy HTML files to dist directory"""
    src_web_dir = Path("src/web")
    
    html_files = ["index.html", "login.html", "signup.html"]
    
    for html_file in html_files:
        src_file = src_web_dir / html_file
        if src_file.exists():
            shutil.copy2(src_file, dist_dir / html_file)
            print(f"✅ Copied {html_file}")
        else:
            print(f"⚠️  Warning: {html_file} not found")

def copy_data_files(dist_dir):
    """Copy necessary data files for the application"""
    
    # DON'T copy templates to dist - they stay in project root for serverless functions
    templates_dir = Path("templates")
    if not templates_dir.exists():
        templates_dir.mkdir()
        print("✅ Created templates directory")
    
    # DON'T copy data to dist - it stays in project root for serverless functions
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir()
        
    # Ensure ParsedFiles directory exists in project root (not dist)
    parsed_files_dir = data_dir / "ParsedFiles"
    if not parsed_files_dir.exists():
        parsed_files_dir.mkdir()
        print("✅ Created ParsedFiles directory")
    
    # Ensure trigger_queue directory exists in project root
    trigger_queue_dir = data_dir / "trigger_queue"
    if not trigger_queue_dir.exists():
        trigger_queue_dir.mkdir()
        print("✅ Created trigger_queue directory")
    
    # Ensure processed_bucket_files.json exists in project root
    processed_files = data_dir / "processed_bucket_files.json"
    if not processed_files.exists():
        # Create empty processed files log
        with open(processed_files, 'w') as f:
            json.dump({"processed_files": [], "last_updated": datetime.now().isoformat()}, f)
        print("✅ Created processed bucket files log")
    
    print("✅ Data directories remain in project root for serverless functions")

def create_redirects_file(dist_dir):
    """Create _redirects file for Netlify"""
    redirects_content = """# Netlify redirects file
# API endpoints redirect to functions
/api/* /.netlify/functions/:splat 200
/health /.netlify/functions/health 200

# SPA fallback
/* /index.html 200
"""
    
    with open(dist_dir / "_redirects", "w") as f:
        f.write(redirects_content)
    print("✅ Created _redirects file")

def create_env_template(dist_dir):
    """Create environment variables template for reference"""
    env_template = """# Environment Variables for Netlify Deployment
# Set these in Netlify UI: Site Settings > Environment Variables

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# OpenAI Configuration (for AI features)
OPENAI_API_KEY=your_openai_api_key

# Netlify automatically sets PORT
"""
    
    with open(dist_dir / ".env.example", "w") as f:
        f.write(env_template)
    print("✅ Created .env.example template")

def create_package_json(dist_dir):
    """Create package.json for Netlify build"""
    package_data = {
        "name": "section-e-resume-app",
        "version": "1.0.0",
        "description": "Section E Resume Database - Netlify Deployment",
        "scripts": {
            "build": "python3 build.py",
            "start": "echo 'Built for Netlify deployment'"
        },
        "dependencies": {},
        "engines": {
            "python": "3.9"
        }
    }
    
    with open(dist_dir / "package.json", "w") as f:
        json.dump(package_data, f, indent=2)
    print("✅ Created package.json")

def main():
    """Main build function"""
    print("🚀 Building application for Netlify deployment...")
    print("=" * 50)
    
    # Create dist directory
    dist_dir = create_dist_directory()
    
    # Copy static files
    copy_html_files(dist_dir)
    copy_data_files(dist_dir)
    
    # Create Netlify-specific files
    create_redirects_file(dist_dir)
    create_env_template(dist_dir)
    create_package_json(dist_dir)
    
    print("\n✅ Build completed successfully!")
    print(f"📁 Static files ready in: {dist_dir.absolute()}")
    print("🚀 Ready for Netlify deployment!")

if __name__ == "__main__":
    main() 