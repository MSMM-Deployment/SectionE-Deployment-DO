#!/usr/bin/env python3
"""
PDF Encoding Solution - Complete Solution for PDF Text Extraction Issues

This script demonstrates how to handle PDF encoding issues, CID codes, and 
garbled text before sending to OpenAI for processing.

Key improvements:
1. Multiple PDF extraction libraries with fallback
2. CID code decoding 
3. Garbled text pattern replacement
4. Unicode normalization
5. Text quality analysis
6. Enhanced preprocessing pipeline

Usage:
    python pdf_encoding_solution.py --input path/to/pdf --output result.json
    python pdf_encoding_solution.py --batch folder/ --output results.json
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to Python path for src module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.parsers.enhanced_text_extractor import EnhancedTextExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demonstrate_encoding_fixes(pdf_path: str) -> None:
    """Demonstrate the encoding issues and fixes"""
    
    print("🔍 PDF ENCODING ANALYSIS & SOLUTION")
    print("=" * 60)
    print(f"Analyzing: {pdf_path}")
    print()
    
    extractor = EnhancedTextExtractor()
    
    # Show the problem with different extraction methods
    print("📊 COMPARISON OF EXTRACTION METHODS:")
    print("-" * 40)
    
    methods = [
        ("pdfminer", extractor.extract_text_pdfminer),
        ("PyPDF2", extractor.extract_text_pypdf2), 
        ("pdfplumber", extractor.extract_text_pdfplumber),
        ("PyMuPDF", extractor.extract_text_pymupdf),
    ]
    
    for method_name, method_func in methods:
        try:
            raw_text = method_func(pdf_path)
            if raw_text:
                quality = extractor.analyze_text_quality(raw_text)
                print(f"{method_name:12}: {len(raw_text):5d} chars | Quality: {quality['quality']:4s} | Issues: {len(quality['issues'])}")
                if quality['cid_patterns'] > 0:
                    print(f"              ⚠ Contains {quality['cid_patterns']} CID patterns")
                if quality['garbled_patterns'] > 0:
                    print(f"              ⚠ Contains {quality['garbled_patterns']} garbled patterns")
            else:
                print(f"{method_name:12}: Failed to extract text")
        except Exception as e:
            print(f"{method_name:12}: Error - {str(e)[:50]}...")
    
    print()
    
    # Show the enhanced solution
    print("🔧 ENHANCED EXTRACTION SOLUTION:")
    print("-" * 40)
    
    cleaned_text, method_used = extractor.extract_text_with_fallback(pdf_path)
    quality = extractor.analyze_text_quality(cleaned_text)
    
    print(f"✓ Best method: {method_used}")
    print(f"✓ Text length: {len(cleaned_text)} characters")
    print(f"✓ Quality: {quality['quality']}")
    print(f"✓ Remaining issues: {len(quality['issues'])}")
    
    if quality['issues']:
        for issue in quality['issues']:
            print(f"  ⚠ {issue}")
    
    print()
    print("📄 SAMPLE EXTRACTED TEXT (first 300 chars):")
    print("-" * 40)
         sample_text = cleaned_text[:300] + "..." if len(cleaned_text) > 300 else cleaned_text
     print(sample_text)
    print()

def process_single_pdf(pdf_path: str, output_path: str = None) -> dict:
    """Process a single PDF with enhanced extraction"""
    
    # Load API key
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    client = OpenAI(api_key=api_key)
    extractor = EnhancedTextExtractor()
    
    print(f"🔄 Processing: {pdf_path}")
    
    # Extract and clean text
    text, method_used = extractor.extract_text_with_fallback(pdf_path)
    if not text:
        return {"error": "Failed to extract text", "method": method_used}
    
    # Analyze text quality
    quality = extractor.analyze_text_quality(text)
    print(f"✓ Extracted {len(text)} chars using {method_used} (quality: {quality['quality']})")
    
    # Process with OpenAI (using the same prompt as section_e_parser.py)
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": """You are a structured resume parser for U.S. Government Standard Form 330 Section E resumes.
Extract the following fields from the provided text and return them as a JSON object.

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

Return only the JSON object, no additional text or formatting."""},
                {"role": "user", "content": text}
            ],
            temperature=0,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        if not content:
            return {"error": "Empty response from OpenAI"}
        
        parsed_data = json.loads(content)
        
        result = {
            "filename": Path(pdf_path).name,
            "extraction_method": method_used,
            "text_quality": quality,
            "text_length": len(text),
            "data": parsed_data,
            "processed_at": datetime.now().isoformat()
        }
        
        # Save output if specified
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"✓ Results saved to: {output_path}")
        
        return result
        
     except json.JSONDecodeError as e:
         content_preview = content[:200] if content else "None"
         return {"error": f"JSON parsing failed: {e}", "raw_response": content_preview}
    except Exception as e:
        return {"error": f"OpenAI processing failed: {e}"}

def process_batch(folder_path: str, output_path: str) -> dict:
    """Process all PDFs in a folder"""
    
    folder = Path(folder_path)
    pdf_files = list(folder.glob("*.pdf"))
    
    if not pdf_files:
        raise ValueError(f"No PDF files found in {folder_path}")
    
    print(f"🔄 Processing {len(pdf_files)} PDFs from {folder_path}")
    
    results = []
    successful = 0
    failed = 0
    
    for pdf_file in pdf_files:
        try:
            result = process_single_pdf(str(pdf_file))
            if "error" in result:
                failed += 1
                print(f"✗ Failed: {pdf_file.name} - {result['error']}")
            else:
                successful += 1
                print(f"✓ Success: {pdf_file.name}")
            results.append(result)
        except Exception as e:
            failed += 1
            error_result = {
                "filename": pdf_file.name,
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
            results.append(error_result)
            print(f"✗ Failed: {pdf_file.name} - {e}")
    
    # Create final output
    output_data = {
        "batch_results": results,
        "metadata": {
            "total_files": len(pdf_files),
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful/len(pdf_files)*100):.1f}%",
            "processed_at": datetime.now().isoformat()
        }
    }
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 BATCH PROCESSING SUMMARY:")
    print(f"Total files: {len(pdf_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(successful/len(pdf_files)*100):.1f}%")
    print(f"Results saved to: {output_path}")
    
    return output_data

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="PDF Encoding Solution - Fix PDF text extraction issues before OpenAI processing"
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", help="Single PDF file to process")
    input_group.add_argument("--batch", help="Folder containing PDF files to process")
    
    # Analysis option
    parser.add_argument("--analyze", action="store_true", 
                       help="Only analyze encoding issues (don't process with OpenAI)")
    
    # Output option
    parser.add_argument("--output", help="Output JSON file path")
    
    args = parser.parse_args()
    
    try:
        if args.input:
            # Single file processing
            if not Path(args.input).exists():
                raise FileNotFoundError(f"PDF file not found: {args.input}")
            
            if args.analyze:
                # Just demonstrate the encoding analysis
                demonstrate_encoding_fixes(args.input)
            else:
                # Full processing with OpenAI
                result = process_single_pdf(args.input, args.output)
                if "error" in result:
                    print(f"❌ Processing failed: {result['error']}")
                    return 1
                else:
                    print("✅ Processing completed successfully!")
                    
        elif args.batch:
            # Batch processing
            if not Path(args.batch).exists():
                raise FileNotFoundError(f"Folder not found: {args.batch}")
            
            if args.analyze:
                # Analyze all PDFs in folder
                folder = Path(args.batch)
                pdf_files = list(folder.glob("*.pdf"))
                for pdf_file in pdf_files:
                    print(f"\n{'='*60}")
                    demonstrate_encoding_fixes(str(pdf_file))
            else:
                # Full batch processing
                if not args.output:
                    args.output = "batch_results.json"
                
                process_batch(args.batch, args.output)
                print("✅ Batch processing completed!")
                
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 