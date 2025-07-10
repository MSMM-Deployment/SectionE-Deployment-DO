#!/usr/bin/env python3
"""
Standard Form 330 Section E Resume Parser using OpenAI API for structured extraction.

This script processes PDF and Word document resumes in Standard Form 330 Section E format by:
1. Using enhanced text extraction for PDF and Word documents (.pdf, .docx, .doc)
2. Sending the text to OpenAI GPT-4-turbo to extract structured data

Requirements:
- OPENAI_API_KEY environment variable must be set
- pip install openai pdfminer.six python-dotenv python-docx docx2txt pymupdf pdfplumber

Usage:
python section_e_parser.py --folder /path/to/resumes --output results.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to Python path for src module imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.parsers.enhanced_text_extractor import EnhancedTextExtractor

# System prompt for OpenAI to extract structured data from resumes
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


def parse_resume_with_openai(client: OpenAI, text: str) -> dict:
    """
    Parse resume text using OpenAI GPT-4-turbo
    
    Args:
        client (OpenAI): OpenAI client instance
        text (str): Extracted PDF text
        
    Returns:
        dict: Parsed resume data as dictionary
    """
    try:
        response = client.chat.completions.create(
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


def extract_text_from_document(file_path: str) -> str:
    """
    Extract text from PDF or Word document using enhanced extraction with encoding fixes
    
    Args:
        file_path (str): Path to PDF or Word document file
        
    Returns:
        str: Extracted and cleaned text content
    """
    try:
        extractor = EnhancedTextExtractor()
        text, method_used = extractor.extract_text_with_fallback(file_path)
        
        if text:
            file_type = Path(file_path).suffix.upper()
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


def process_resume(client: OpenAI, file_path: Path) -> dict:
    """
    Process a single resume file (PDF or Word document)
    
    Args:
        client (OpenAI): OpenAI client instance
        file_path (Path): Path to resume file
        
    Returns:
        dict: Processing result with filename, data, and metadata
    """
    print(f"Processing {file_path.name}...")
    
    try:
        # Extract text from document
        text = extract_text_from_document(str(file_path))
        if not text:
            print(f"Warning: No text extracted from {file_path.name}")
            return {
                "filename": file_path.name,
                "error": "No text extracted from document",
                "processed_at": datetime.utcnow().isoformat()
            }
        
        # Parse with OpenAI
        parsed_data = parse_resume_with_openai(client, text)
        
        if not parsed_data:
            return {
                "filename": file_path.name,
                "error": "Failed to parse resume data",
                "processed_at": datetime.utcnow().isoformat()
            }
        
        return {
            "filename": file_path.name,
            "data": parsed_data,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Failed to process {file_path.name}: {e}")
        return {
            "filename": file_path.name,
            "error": str(e),
            "processed_at": datetime.utcnow().isoformat()
        }


def main():
    """Main function to process all PDFs in a folder"""
    # Load environment variables
    load_dotenv()
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description="Parse Standard Form 330 Section E resumes (PDF and Word docs) using OpenAI GPT-4-turbo"
    )
    parser.add_argument("--folder", required=True, help="Path to folder containing resume files (PDF, DOCX, DOC)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--file", help="Process only this specific file (optional)")
    args = parser.parse_args()

    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set your OpenAI API key in the .env file:")
        print("OPENAI_API_KEY=your_api_key_here")
        return

    client = OpenAI(api_key=api_key)
    
    # Find resume files (PDF and Word documents)
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"Error: Folder {args.folder} does not exist.")
        return
    
    # Supported file extensions
    supported_extensions = ['.pdf', '.docx', '.doc']
    
    if args.file:
        # Process only the specified file
        target_file = folder_path / args.file
        if not target_file.exists():
            print(f"Error: File {args.file} not found in {args.folder}")
            return
        if target_file.suffix.lower() not in supported_extensions:
            print(f"Error: {args.file} is not a supported file type. Supported: {', '.join(supported_extensions)}")
            return
        resume_files = [target_file]
        print(f"Processing single file: {args.file}")
    else:
        # Process all supported files in folder
        resume_files = []
        for ext in supported_extensions:
            resume_files.extend(folder_path.glob(f"*{ext}"))
        
        if not resume_files:
            print(f"No supported resume files found in {args.folder}")
            print(f"Supported formats: {', '.join(supported_extensions)}")
            return
        
        # Sort files for consistent processing order
        resume_files.sort(key=lambda x: x.name)
        
        # Show breakdown by file type
        file_counts = {}
        for file in resume_files:
            ext = file.suffix.lower()
            file_counts[ext] = file_counts.get(ext, 0) + 1
        
        print(f"Found {len(resume_files)} resume files to process:")
        for ext, count in file_counts.items():
            print(f"  {ext.upper()}: {count} files")
    
    # Process all resume files
    results = []
    successful = 0
    failed = 0
    
    for file_path in resume_files:
        result = process_resume(client, file_path)
        results.append(result)
        
        if "error" in result:
            failed += 1
            print(f"  ✗ Failed to process {file_path.name}")
        else:
            successful += 1
            print(f"  ✓ Successfully processed {file_path.name}")
    
    # Create final output with metadata
    output_data = {
        "resumes": results,
        "metadata": {
            "total_files": len(resume_files),
            "successful": successful,
            "failed": failed,
            "processed_at": datetime.utcnow().isoformat()
        }
    }

    # Save results
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Processing complete!")
    print(f"Results saved to: {args.output}")
    print(f"Total files: {len(resume_files)}")
    print(f"Successfully processed: {successful}")
    print(f"Failed: {failed}")
    
    if successful > 0:
        success_rate = (successful / len(resume_files)) * 100
        print(f"Success rate: {success_rate:.1f}%")


if __name__ == "__main__":
    main()
 