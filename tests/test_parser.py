#!/usr/bin/env python3
"""
Test script for the Section E Parser using OpenAI

This script demonstrates basic usage of the parser and helps verify 
that everything is set up correctly.

Usage:
python test_parser.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to Python path for src module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.parsers.section_e_parser import parse_resume_with_openai, extract_text_from_document


def test_single_file():
    """Test parsing a single PDF file"""
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        print("Please create a .env file with your API key:")
        print("OPENAI_API_KEY=your_api_key_here")
        return False
    
    client = OpenAI(api_key=api_key)
    
    # Find a sample PDF to test with
    sample_files = [
        "Sample-SectionE/Jeff-Shelden-1.pdf",
        "Sample-SectionE/Jim-Wilson-1.pdf",
        "Sample-SectionE/Manish-Mardia-1.pdf"
    ]
    
    test_file = None
    for file_path in sample_files:
        if os.path.exists(file_path):
            test_file = file_path
            break
    
    if not test_file:
        print("No sample PDF files found. Please ensure you have PDF files to test with.")
        return False
    
    print(f"Testing with file: {test_file}")
    
    try:
        # Extract text from PDF
        text = extract_text_from_document(test_file)
        if not text:
            print("Error: No text extracted from PDF")
            return False
        
        print(f"Extracted {len(text)} characters from PDF")
        
        # Parse the resume using OpenAI
        resume_data = parse_resume_with_openai(client, text)
        
        if not resume_data:
            print("Error: No data parsed from resume")
            return False
        
        # Display results
        print("\n" + "="*50)
        print("EXTRACTION RESULTS")
        print("="*50)
        
        print(f"Name: {resume_data.get('name', 'Not found')}")
        print(f"Role: {resume_data.get('role_in_contract', 'Not found')}")
        
        years_exp = resume_data.get('years_experience', {})
        print(f"Total Experience: {years_exp.get('total', 'Not found')} years")
        print(f"Current Firm Experience: {years_exp.get('with_current_firm', 'Not found')} years")
        
        print(f"Firm: {resume_data.get('firm_name_and_location', 'Not found')}")
        print(f"Education: {resume_data.get('education', 'Not found')}")
        print(f"Registration: {resume_data.get('current_professional_registration', 'Not found')}")
        print(f"Other Qualifications: {resume_data.get('other_professional_qualifications', 'Not found')}")
        
        projects = resume_data.get('relevant_projects', [])
        print(f"Number of Projects: {len(projects)}")
        
        if projects:
            print("\nProjects:")
            for i, project in enumerate(projects, 1):
                print(f"  {i}. {project.get('title_and_location', 'No title')}")
                year_completed = project.get('year_completed', {})
                if year_completed.get('professional_services'):
                    print(f"     Professional Services: {year_completed['professional_services']}")
                if year_completed.get('construction'):
                    print(f"     Construction: {year_completed['construction']}")
                description = project.get('description', '')
                if description:
                    desc = description[:100] + "..." if len(description) > 100 else description
                    print(f"     Description: {desc}")
                print()
        
        print("="*50)
        print("✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False


def test_json_serialization():
    """Test that the data can be properly serialized to JSON"""
    
    # Create sample data structure matching OpenAI output
    sample_data = {
        "name": "Test Engineer",
        "role_in_contract": "Lead Engineer",
        "years_experience": {
            "total": "10",
            "with_current_firm": "5"
        },
        "firm_name_and_location": "Test Firm, Test City",
        "education": "B.S. Engineering",
        "current_professional_registration": "PE License",
        "other_professional_qualifications": "Test Certification",
        "relevant_projects": [
            {
                "title_and_location": "Test Project, Test Location",
                "year_completed": {
                    "professional_services": "2023",
                    "construction": "2024"
                },
                "description": "Test project description"
            }
        ]
    }
    
    try:
        # Test JSON serialization
        json_data = json.dumps(sample_data, indent=2)
        print("JSON Serialization Test:")
        print(json_data[:200] + "..." if len(json_data) > 200 else json_data)
        print("✅ JSON serialization successful!")
        return True
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False


def test_pdf_extraction():
    """Test PDF text extraction"""
    
    # Find a sample PDF to test with
    sample_files = [
        "Sample-SectionE/Jeff-Shelden-1.pdf",
        "Sample-SectionE/Jim-Wilson-1.pdf"
    ]
    
    test_file = None
    for file_path in sample_files:
        if os.path.exists(file_path):
            test_file = file_path
            break
    
    if not test_file:
        print("No sample PDF files found for extraction test")
        return False
    
    try:
        text = extract_text_from_document(test_file)
        if text:
            print(f"✅ PDF text extraction successful! Extracted {len(text)} characters")
            print("Sample text:", text[:100] + "..." if len(text) > 100 else text)
            return True
        else:
            print("❌ PDF text extraction failed - no text returned")
            return False
    except Exception as e:
        print(f"❌ PDF text extraction failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Section E Parser - Test Suite (OpenAI Version)")
    print("=" * 50)
    
    # Test 1: JSON serialization
    print("\n1. Testing JSON serialization...")
    json_test = test_json_serialization()
    
    # Test 2: PDF text extraction
    print("\n2. Testing PDF text extraction...")
    pdf_test = test_pdf_extraction()
    
    # Test 3: Single file parsing (requires API key)
    print("\n3. Testing single file parsing with OpenAI...")
    file_test = test_single_file()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"JSON Serialization: {'✅ PASS' if json_test else '❌ FAIL'}")
    print(f"PDF Text Extraction: {'✅ PASS' if pdf_test else '❌ FAIL'}")
    print(f"OpenAI Parsing: {'✅ PASS' if file_test else '❌ FAIL'}")
    
    if json_test and pdf_test and file_test:
        print("\n🎉 All tests passed! The parser is ready to use.")
        print("\nTo process multiple files, run:")
        print("python src/parsers/section_e_parser.py --folder data/Sample-SectionE --output results.json")
    else:
        print("\n⚠️  Some tests failed. Please check your setup:")
        if not file_test:
            print("- Ensure you have a valid OPENAI_API_KEY in your .env file")
        if not pdf_test:
            print("- Check that PDF files exist and are readable")
        print("- Verify you have PDF files to test with")
        print("- Check your internet connection for OpenAI API calls")


if __name__ == "__main__":
    main() 