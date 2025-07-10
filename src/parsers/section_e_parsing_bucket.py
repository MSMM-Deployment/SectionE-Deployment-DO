#!/usr/bin/env python3
"""
Standard Form 330 Section E Resume Parser for Supabase Storage Bucket

This script processes PDF and Word document resumes stored in a Supabase bucket by:
1. Connecting to Supabase storage bucket "msmm-resumes"
2. Downloading files temporarily for processing
3. Using the same parsing logic as section_e_parser.py
4. Uploading results JSON to "ParsedFiles" folder in the same bucket
5. Cleaning up temporary files

Requirements:
- SUPABASE_URL and SUPABASE_KEY environment variables must be set
- pip install supabase openai pdfminer.six python-dotenv python-docx docx2txt pymupdf pdfplumber

Usage:
python section_e_parsing_bucket.py --output parsed_results.json
"""

import os
import sys
import json
import argparse
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to Python path for src module imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.parsers.enhanced_text_extractor import EnhancedTextExtractor

try:
    from supabase import create_client, Client
except ImportError:
    print("Missing required package. Please install: pip install supabase")
    exit(1)

# System prompt for OpenAI (same as original parser)
SYSTEM_PROMPT = """You are a structured resume parser for U.S. Government Standard Form 330 Section E resumes.
Extract the following fields from the provided text and return them as a JSON object.

IMPORTANT PARSING INSTRUCTIONS:
- Look for ACTUAL detailed project descriptions, NOT placeholder text
- Ignore text like "Brief scope, size, cost, etc." - find the real project details
- For project scope, extract the detailed technical description that follows "Scope:" 
- Extract specific technical details, methodologies, and project deliverables
- For costs and fees, look for actual dollar amounts (e.g., "$4.1M", "$349k")
- If information is not provided or unclear, use empty string "" rather than placeholder text

{
  "name": "",
  "role_in_contract": "",
  "years_experience": {
    "total": "",
    "with_current_firm": ""
  },
  "firm_name_and_location": "",
  "education": "",
  "current_professional_registration": "",
  "other_professional_qualifications": "",
  "relevant_projects": [
    {
      "title_and_location": "",
      "year_completed": {
        "professional_services": "",
        "construction": ""
      },
      "description": {
        "scope": "",  
        "cost": "",
        "fee": "",
        "role": ""
      }
    }
  ]
}

CRITICAL: For the "scope" field, extract the FULL detailed project description that appears after "Scope:" in the document. 
This should include specific technical details about what work was performed, methodologies used, project components, etc.
DO NOT use placeholder text like "Brief scope, size, cost, etc." - extract the actual detailed project information.

There can be multiple relevant projects. Use best effort to extract and normalize each section.
Return only the JSON object, no additional text or formatting."""


class SupabaseBucketParser:
    """Parse resumes from Supabase storage bucket"""
    
    def __init__(self, supabase_url: str, supabase_key: str, openai_client: OpenAI):
        """
        Initialize the bucket parser
        
        Args:
            supabase_url (str): Supabase project URL
            supabase_key (str): Supabase service role key
            openai_client (OpenAI): OpenAI client instance
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.openai_client = openai_client
        self.bucket_name = "msmm-resumes"
        self.parsed_files_folder = "ParsedFiles"
        self.supported_extensions = ['.pdf', '.docx', '.doc']
        
        # Create temporary directory for processing
        self.temp_dir = Path(tempfile.mkdtemp(prefix="section_e_parser_"))
        print(f"Created temporary directory: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
    
    def list_bucket_files(self) -> list:
        """
        List all supported resume files in the bucket
        
        Returns:
            list: List of file paths in the bucket
        """
        try:
            # List all files in the bucket
            response = self.supabase.storage.from_(self.bucket_name).list()
            
            if not response:
                print(f"No files found in bucket '{self.bucket_name}'")
                return []
            
            # Filter for supported file types
            resume_files = []
            for file_info in response:
                file_name = file_info['name']
                file_path = Path(file_name)
                
                # Skip directories and unsupported files
                if file_path.suffix.lower() in self.supported_extensions:
                    resume_files.append(file_name)
            
            return resume_files
            
        except Exception as e:
            print(f"Error listing bucket files: {e}")
            return []
    
    def download_file(self, file_path: str) -> Path:
        """
        Download a file from the bucket to temporary directory
        
        Args:
            file_path (str): Path to file in bucket
            
        Returns:
            Path: Local path to downloaded file
        """
        try:
            # Download file from bucket
            response = self.supabase.storage.from_(self.bucket_name).download(file_path)
            
            if not response:
                raise Exception(f"Failed to download {file_path}")
            
            # Save to temporary directory
            local_file_path = self.temp_dir / Path(file_path).name
            with open(local_file_path, 'wb') as f:
                f.write(response)
            
            print(f"  📥 Downloaded {file_path} to {local_file_path}")
            return local_file_path
            
        except Exception as e:
            print(f"Error downloading {file_path}: {e}")
            raise
    
    def upload_results(self, json_data: dict, output_filename: str) -> bool:
        """
        Upload parsing results to the ParsedFiles folder in the bucket
        
        Args:
            json_data (dict): Parsed results data
            output_filename (str): Name for the output file
            
        Returns:
            bool: Success status
        """
        try:
            # Convert to JSON string
            json_content = json.dumps(json_data, indent=2, ensure_ascii=False)
            json_bytes = json_content.encode('utf-8')
            
            # Upload to ParsedFiles folder
            bucket_path = f"{self.parsed_files_folder}/{output_filename}"
            
            # Try to upload (upsert to overwrite if exists)
            try:
                response = self.supabase.storage.from_(self.bucket_name).upload(
                    bucket_path, 
                    json_bytes
                )
            except Exception as upload_error:
                # If upload fails, try to update existing file
                if "already exists" in str(upload_error).lower():
                    response = self.supabase.storage.from_(self.bucket_name).update(
                        bucket_path,
                        json_bytes
                    )
                else:
                    raise upload_error
            
            if response:
                print(f"  ✅ Uploaded results to {bucket_path}")
                return True
            else:
                print(f"  ❌ Failed to upload results to {bucket_path}")
                return False
                
        except Exception as e:
            print(f"Error uploading results: {e}")
            return False
    
    def parse_resume_with_openai(self, text: str) -> dict:
        """
        Parse resume text using OpenAI GPT-4-turbo
        
        Args:
            text (str): Extracted document text
            
        Returns:
            dict: Parsed resume data as dictionary
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0,
                max_tokens=4000
            )
            content = response.choices[0].message.content
            
            # Check if content is valid
            if not content:
                print("Error: Empty response from OpenAI")
                return {}
            
            # Try to parse the JSON response
            parsed_data = json.loads(content)
            return parsed_data
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            content_preview = content[:200] if content else "None"
            print(f"Raw response: {content_preview}...")
            return {}
        except Exception as e:
            print(f"OpenAI parsing failed: {e}")
            return {}
    
    def extract_text_from_document(self, file_path: Path) -> str:
        """
        Extract text from PDF or Word document using enhanced extraction
        
        Args:
            file_path (Path): Path to document file
            
        Returns:
            str: Extracted and cleaned text content
        """
        try:
            extractor = EnhancedTextExtractor()
            text, method_used = extractor.extract_text_with_fallback(str(file_path))
            
            if text:
                file_type = file_path.suffix.upper()
                print(f"  ✓ {file_type} text extracted using {method_used} (length: {len(text)})")
                
                # Analyze text quality for reporting
                quality = extractor.analyze_text_quality(text)
                if quality['issues']:
                    print(f"  ⚠ Text quality: {quality['quality']} - {', '.join(quality['issues'])}")
                else:
                    print(f"  ✓ Text quality: {quality['quality']}")
                    
                return text
            else:
                print(f"  ✗ Failed to extract text using enhanced extractor")
                return ""
                
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def process_resume(self, file_path: str) -> dict:
        """
        Process a single resume file from the bucket
        
        Args:
            file_path (str): Path to resume file in bucket
            
        Returns:
            dict: Processing result with filename, data, and metadata
        """
        print(f"Processing {file_path}...")
        
        try:
            # Download file to temporary directory
            local_file_path = self.download_file(file_path)
            
            # Extract text from document
            text = self.extract_text_from_document(local_file_path)
            if not text:
                print(f"Warning: No text extracted from {file_path}")
                return {
                    "filename": file_path,
                    "error": "No text extracted from document",
                    "processed_at": datetime.utcnow().isoformat()
                }
            
            # Parse with OpenAI
            parsed_data = self.parse_resume_with_openai(text)
            
            if not parsed_data:
                return {
                    "filename": file_path,
                    "error": "Failed to parse resume data",
                    "processed_at": datetime.utcnow().isoformat()
                }
            
            return {
                "filename": file_path,
                "data": parsed_data,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")
            return {
                "filename": file_path,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def process_all_resumes(self, specific_file: Optional[str] = None) -> dict:
        """
        Process all resume files in the bucket
        
        Args:
            specific_file (str): Optional specific file to process
            
        Returns:
            dict: Processing results with metadata
        """
        try:
            # Get list of files to process
            if specific_file:
                if not specific_file.endswith(tuple(self.supported_extensions)):
                    print(f"Error: {specific_file} is not a supported file type. Supported: {', '.join(self.supported_extensions)}")
                    return {"error": "Unsupported file type"}
                
                resume_files = [specific_file]
                print(f"Processing single file: {specific_file}")
            else:
                resume_files = self.list_bucket_files()
                
                if not resume_files:
                    print(f"No supported resume files found in bucket '{self.bucket_name}'")
                    return {"error": "No files found"}
                
                # Show breakdown by file type
                file_counts = {}
                for file_path in resume_files:
                    ext = Path(file_path).suffix.lower()
                    file_counts[ext] = file_counts.get(ext, 0) + 1
                
                print(f"Found {len(resume_files)} resume files to process:")
                for ext, count in file_counts.items():
                    print(f"  {ext.upper()}: {count} files")
            
            # Process all resume files
            results = []
            successful = 0
            failed = 0
            
            for file_path in resume_files:
                result = self.process_resume(file_path)
                results.append(result)
                
                if "error" in result:
                    failed += 1
                    print(f"  ✗ Failed to process {file_path}")
                else:
                    successful += 1
                    print(f"  ✓ Successfully processed {file_path}")
            
            # Create final output with metadata
            output_data = {
                "resumes": results,
                "metadata": {
                    "total_files": len(resume_files),
                    "successful": successful,
                    "failed": failed,
                    "processed_at": datetime.utcnow().isoformat(),
                    "bucket_name": self.bucket_name,
                    "source": "supabase_bucket"
                }
            }
            
            print(f"\n🎉 Processing complete!")
            print(f"Total files: {len(resume_files)}")
            print(f"Successfully processed: {successful}")
            print(f"Failed: {failed}")
            
            if successful > 0:
                success_rate = (successful / len(resume_files)) * 100
                print(f"Success rate: {success_rate:.1f}%")
            
            return output_data
            
        except Exception as e:
            print(f"Error processing resumes: {e}")
            return {"error": str(e)}


def main():
    """Main function to process all resumes in Supabase bucket"""
    # Load environment variables
    load_dotenv()
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description="Parse Standard Form 330 Section E resumes from Supabase bucket using OpenAI GPT-4-turbo"
    )
    parser.add_argument("--output", required=True, help="Output JSON filename (will be uploaded to ParsedFiles folder)")
    parser.add_argument("--file", help="Process only this specific file (optional)")
    args = parser.parse_args()

    # Get credentials from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Validate credentials
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set your OpenAI API key in the .env file:")
        print("OPENAI_API_KEY=your_api_key_here")
        return
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found.")
        print("Please set SUPABASE_URL and SUPABASE_KEY environment variables in your .env file:")
        print("  SUPABASE_URL=your_supabase_url")
        print("  SUPABASE_KEY=your_supabase_service_role_key")
        return

    # Initialize clients
    openai_client = OpenAI(api_key=openai_api_key)
    
    # Create bucket parser
    bucket_parser = None
    try:
        bucket_parser = SupabaseBucketParser(supabase_url, supabase_key, openai_client)
        
        print(f"🚀 Starting Section E Resume Parser (Supabase Bucket)")
        print(f"📦 Bucket: {bucket_parser.bucket_name}")
        print(f"📁 Output folder: {bucket_parser.parsed_files_folder}")
        print(f"📄 Output file: {args.output}")
        
        # Process resumes
        results = bucket_parser.process_all_resumes(args.file)
        
        if "error" in results:
            print(f"❌ Processing failed: {results['error']}")
            return
        
        # Upload results to bucket
        upload_success = bucket_parser.upload_results(results, args.output)
        
        if upload_success:
            print(f"\n✅ Results successfully uploaded to bucket!")
            print(f"📍 Location: {bucket_parser.bucket_name}/{bucket_parser.parsed_files_folder}/{args.output}")
        else:
            print(f"\n❌ Failed to upload results to bucket")
            
            # Save locally as fallback
            local_path = args.output
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"💾 Results saved locally as fallback: {local_path}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        # Clean up temporary files
        if bucket_parser:
            bucket_parser.cleanup()


if __name__ == "__main__":
    main() 