#!/usr/bin/env python3
"""
Supabase Template Downloader

This utility handles downloading template files from Supabase storage when they're not available locally.
It provides seamless integration between local templates and cloud-stored templates uploaded via the web interface.

Usage:
from utils.supabase_template_downloader import SupabaseTemplateDownloader

downloader = SupabaseTemplateDownloader()
template_path = downloader.get_template_path("template_filename.docx")
# Returns local path if exists, or downloads from Supabase and returns temp path
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase client not available. Cloud template functionality disabled.")


class SupabaseTemplateDownloader:
    """Downloads and manages templates from Supabase storage"""
    
    def __init__(self, 
                 local_templates_dir: str = "templates",
                 bucket_name: str = "resume-templates",
                 cache_dir: Optional[str] = None):
        """
        Initialize the template downloader
        
        Args:
            local_templates_dir: Local directory to check for templates first
            bucket_name: Supabase bucket name where templates are stored
            cache_dir: Directory to cache downloaded templates (default: temp dir)
        """
        self.local_templates_dir = Path(local_templates_dir)
        self.bucket_name = bucket_name
        
        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "section_e_templates"
        
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize Supabase client if available
        self.supabase = None
        self.supabase_available = False
        
        if SUPABASE_AVAILABLE:
            self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
            
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                self.supabase_available = True
                print(f"✅ Supabase template downloader initialized for bucket: {self.bucket_name}")
            else:
                print("⚠️ Supabase credentials not found. Cloud templates disabled.")
                
        except Exception as e:
            print(f"⚠️ Failed to initialize Supabase client: {e}")
    
    def get_template_path(self, filename: str) -> Optional[str]:
        """
        Get the path to a template file, downloading from Supabase if necessary
        
        Args:
            filename: Template filename to find
            
        Returns:
            str: Local path to template file, or None if not found anywhere
        """
        # Step 1: Check if template exists locally
        local_path = self.local_templates_dir / filename
        if local_path.exists():
            print(f"📄 Using local template: {local_path}")
            return str(local_path)
        
        # Step 2: Check cache
        cached_path = self.cache_dir / filename
        if cached_path.exists():
            print(f"📄 Using cached template: {cached_path}")
            return str(cached_path)
        
        # Step 3: Try to download from Supabase
        if self.supabase_available and self.supabase:
            try:
                downloaded_path = self._download_from_supabase(filename)
                if downloaded_path:
                    print(f"📄 Downloaded template from Supabase: {downloaded_path}")
                    return downloaded_path
            except Exception as e:
                print(f"⚠️ Failed to download template from Supabase: {e}")
        
        # Step 4: Template not found anywhere
        print(f"❌ Template not found anywhere: {filename}")
        return None
    
    def _download_from_supabase(self, filename: str) -> Optional[str]:
        """
        Download a template file from Supabase bucket
        
        Args:
            filename: Name of file to download
            
        Returns:
            str: Path to downloaded file, or None if download failed
        """
        if not self.supabase:
            return None
            
        try:
            # Download file from bucket
            file_data = self.supabase.storage.from_(self.bucket_name).download(filename)
            
            if not isinstance(file_data, bytes) or len(file_data) == 0:
                print(f"⚠️ Template file empty or invalid: {filename}")
                return None
            
            # Save to cache directory
            cache_path = self.cache_dir / filename
            
            with open(cache_path, 'wb') as f:
                f.write(file_data)
            
            print(f"📥 Downloaded template: {filename} ({len(file_data):,} bytes)")
            return str(cache_path)
            
        except Exception as e:
            print(f"❌ Error downloading {filename} from bucket {self.bucket_name}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the template cache directory"""
        try:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                print(f"🗑️ Cleared template cache: {self.cache_dir}")
        except Exception as e:
            print(f"⚠️ Error clearing cache: {e}")
    
    def list_available_templates(self) -> dict:
        """
        List all available templates (local + Supabase)
        
        Returns:
            dict: Lists of local and cloud templates
        """
        result = {
            'local': [],
            'cloud': [],
            'cached': []
        }
        
        # List local templates
        if self.local_templates_dir.exists():
            for file_path in self.local_templates_dir.glob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.docx', '.doc']:
                    result['local'].append(file_path.name)
        
        # List cached templates
        if self.cache_dir.exists():
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    result['cached'].append(file_path.name)
        
        # List cloud templates
        if self.supabase_available and self.supabase:
            try:
                response = self.supabase.storage.from_(self.bucket_name).list()
                if isinstance(response, list):
                    for file_info in response:
                        filename = file_info.get('name', '')
                        if filename and Path(filename).suffix.lower() in ['.pdf', '.docx', '.doc']:
                            result['cloud'].append(filename)
            except Exception as e:
                print(f"⚠️ Error listing cloud templates: {e}")
        
        return result
    
    def ensure_template_available(self, filename: str) -> bool:
        """
        Ensure a template is available for use (download if necessary)
        
        Args:
            filename: Template filename
            
        Returns:
            bool: True if template is available, False otherwise
        """
        template_path = self.get_template_path(filename)
        return template_path is not None


def main():
    """Test the template downloader"""
    print("🧪 Testing Supabase Template Downloader")
    print("=" * 50)
    
    downloader = SupabaseTemplateDownloader()
    
    # List all available templates
    templates = downloader.list_available_templates()
    
    print(f"📁 Local templates: {len(templates['local'])}")
    for template in templates['local']:
        print(f"  - {template}")
    
    print(f"☁️ Cloud templates: {len(templates['cloud'])}")  
    for template in templates['cloud']:
        print(f"  - {template}")
        
    print(f"💾 Cached templates: {len(templates['cached'])}")
    for template in templates['cached']:
        print(f"  - {template}")
    
    # Test downloading a specific template
    if templates['cloud']:
        test_template = templates['cloud'][0]
        print(f"\n🔄 Testing download of: {test_template}")
        
        path = downloader.get_template_path(test_template)
        if path:
            print(f"✅ Template available at: {path}")
        else:
            print(f"❌ Failed to get template: {test_template}")


if __name__ == "__main__":
    main() 