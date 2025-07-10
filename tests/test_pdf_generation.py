#!/usr/bin/env python3
"""
PDF Generation Test Suite

This script comprehensively tests all PDF generation capabilities
in the Section E system without requiring a full server setup.

Test Coverage:
- JSON-based PDF generation using ReportLab
- Supabase database connectivity
- PDF form filling with template
- Error handling and fallback mechanisms

Usage:
python test_pdf_generation.py

Requirements:
- Parsed resume data in ParsedFiles/real_parsed_results.json
- Valid .env file with Supabase credentials
- PDF template: "Section E template.pdf"
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path for src module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_json_based_pdf():
    """
    Test PDF generation using JSON data (fallback method)
    
    This test verifies that we can create PDFs using only the parsed JSON data
    and ReportLab library, without requiring database connectivity or template forms.
    """
    print("🧪 Testing JSON-based PDF generation...")
    
    try:
        # Check if parsed resume data exists from section_e_parser.py
        json_file = "ParsedFiles/real_parsed_results.json"
        if not os.path.exists(json_file):
            print(f"❌ Error: {json_file} not found")
            print("💡 Run src/parsers/section_e_parser.py first to generate resume data")
            return False
        
        # Load data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        resumes = data.get('resumes', [])
        if not resumes:
            print("❌ No resume data found in JSON file")
            return False
        
        print(f"📊 Found {len(resumes)} resumes in data")
        
        # Try to test with reportlab
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io
            
            # Test PDF creation with first employee
            first_resume = resumes[0]
            employee_data = first_resume.get('data', {})
            employee_name = employee_data.get('name', 'Test Employee')
            
            print(f"📝 Testing PDF generation for: {employee_name}")
            
            # Create test PDF
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, height - 50, "TEST SECTION E PDF")
            p.setFont("Helvetica", 12)
            p.drawString(50, height - 80, f"Employee: {employee_name}")
            p.save()
            
            pdf_content = buffer.getvalue()
            buffer.close()
            
            # Save test PDF
            output_dir = Path("OutputFiles/PDFs")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            test_pdf_path = output_dir / "test_pdf_generation.pdf"
            with open(test_pdf_path, 'wb') as pdf_file:
                pdf_file.write(pdf_content)
            
            print(f"✅ Test PDF created successfully: {test_pdf_path}")
            print(f"📦 PDF size: {len(pdf_content)} bytes")
            return True
            
        except ImportError as e:
            print(f"⚠️ ReportLab not available: {e}")
            print("💡 Install with: pip install reportlab")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_supabase_connection():
    """
    Test Supabase connection for database-based PDF generation
    
    This test verifies that we can connect to Supabase and retrieve employee data,
    which is required for the sophisticated PDF form filling functionality.
    """
    print("\n🔗 Testing Supabase connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()  # Load credentials from .env file
        
        # Get Supabase credentials (service role key needed for full access)
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            print("⚠️ Supabase credentials not found in .env")
            print("💡 Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to .env file")
            return False
        
        try:
            from supabase import create_client
            client = create_client(supabase_url, supabase_key)
            
            # Test simple query
            result = client.table('employees').select('employee_id, employee_name').limit(1).execute()
            
            if result.data:
                employee = result.data[0]
                print(f"✅ Supabase connection successful")
                print(f"📋 Sample employee: {employee.get('employee_name')} (ID: {employee.get('employee_id')})")
                return True
            else:
                print("⚠️ Supabase connected but no employee data found")
                return False
                
        except ImportError:
            print("⚠️ Supabase client not available")
            print("💡 Install with: pip install supabase")
            return False
            
    except Exception as e:
        print(f"❌ Supabase test failed: {e}")
        return False

def test_pdf_form_filler():
    """
    Test the main PDF form filler functionality
    
    This test validates the complete PDF form filling workflow:
    - Loading employee data from database or JSON
    - Using the Section E template with fillable fields
    - Generating professional PDF resumes
    """
    print("\n📄 Testing PDF form filler...")
    
    try:
        from src.generators.pdf_form_filler import SectionEPDFGenerator
        
        # Initialize the PDF generator (handles both database and JSON modes)
        generator = SectionEPDFGenerator()
        
        # Get list of available employees for testing
        employees = generator.list_employees()
        if employees:
            print(f"✅ PDF generator loaded successfully")
            print(f"👥 Found {len(employees)} employees in database")
            
            # Test with first employee
            first_employee = employees[0]
            employee_name = first_employee.get('employee_name')
            
            if not employee_name:
                print("❌ No employee name found in first record")
                return False
            
            print(f"🧪 Testing PDF generation for: {employee_name}")
            pdf_path = generator.generate_resume_by_name(employee_name)
            
            if pdf_path and os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"✅ PDF generated successfully: {pdf_path}")
                print(f"📦 File size: {file_size} bytes")
                return True
            else:
                print("❌ PDF generation failed")
                return False
        else:
            print("⚠️ No employees found in database")
            return False
            
    except ImportError as e:
        print(f"⚠️ PDF form filler dependencies missing: {e}")
        return False
    except Exception as e:
        print(f"❌ PDF form filler test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting PDF Generation Tests")
    print("=" * 50)
    
    tests = [
        ("JSON-based PDF Generation", test_json_based_pdf),
        ("Supabase Connection", test_supabase_connection),
        ("PDF Form Filler", test_pdf_form_filler)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! PDF generation is ready to use.")
    elif passed > 0:
        print("⚠️ Some tests passed. Check the failed tests above.")
    else:
        print("❌ All tests failed. Check your setup and dependencies.")
    
    print("\n💡 To install dependencies: pip install -r requirements.txt")
    print("💡 To start the server: python src/web/serve_ui.py")

if __name__ == "__main__":
    main() 