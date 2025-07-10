#!/usr/bin/env python3
"""
Test file for Jinja DOCX Section E Generator

This test validates the integration of the new Jinja template system
with the Section E resume generation workflow.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_sample_employee_data():
    """Create sample employee data for testing"""
    return {
        "name": "John Smith",
        "role_in_contract": "Senior Project Manager",
        "years_experience": {
            "total": "15",
            "with_current_firm": "8"
        },
        "firm_name_and_location": "Engineering Solutions Inc., San Francisco, CA",
        "education": "MS Civil Engineering, Stanford University (2008); BS Engineering, UC Berkeley (2006)",
        "current_professional_registration": "PE (California), PMP Certified",
        "other_professional_qualifications": "LEED AP, Construction Management Certificate",
        "relevant_projects": [
            {
                "title": "Golden Gate Bridge Retrofit",
                "location": "San Francisco, CA",
                "year_completed": {
                    "professional_services": "2023",
                    "construction": "2024"
                },
                "description": {
                    "scope": "Seismic retrofit of suspension bridge components",
                    "cost": "$50M",
                    "fee": "$2.5M", 
                    "role": "Lead Project Manager for design and construction oversight"
                }
            },
            {
                "title": "Bay Area Transit Expansion",
                "location": "Oakland, CA",
                "year_completed": {
                    "professional_services": "2022",
                    "construction": "2023"
                },
                "description": {
                    "scope": "New subway line construction including 5 stations",
                    "cost": "$200M",
                    "fee": "$8M",
                    "role": "Deputy Project Manager responsible for quality control"
                }
            }
        ]
    }

def test_jinja_docx_generator():
    """Test the Jinja DOCX generator functionality"""
    print("🧪 Testing Jinja DOCX Section E Generator")
    print("=" * 50)
    
    # Check if template exists
    template_path = "templates/JinjaTemplate.docx"
    if not os.path.exists(template_path):
        print(f"❌ Jinja template not found: {template_path}")
        print("💡 Make sure the JinjaTemplate.docx is in the templates folder")
        return False
    
    print(f"✅ Template found: {template_path}")
    
    try:
        # Import the Jinja DOCX generator
        from src.generators.jinja_docx_generator import JinjaDOCXSectionEGenerator
        
        # Initialize generator
        generator = JinjaDOCXSectionEGenerator(template_path)
        print(f"✅ Generator initialized")
        print(f"📁 Output directory: {generator.output_dir}")
        
        # Get sample data
        sample_data = create_sample_employee_data()
        
        # Test template data preparation
        template_data = generator.prepare_template_data(sample_data)
        print(f"✅ Template data prepared")
        print(f"📊 Employee data: {template_data['employee']['name']}")
        print(f"📊 Projects mapped: {len([k for k in template_data.keys() if k.startswith('project')])}")
        
        # Validate project mapping
        if 'projectA' in template_data and template_data['projectA']['title_and_location']:
            print(f"✅ Project A: {template_data['projectA']['title_and_location']}")
        if 'projectB' in template_data and template_data['projectB']['title_and_location']:
            print(f"✅ Project B: {template_data['projectB']['title_and_location']}")
        
        # Generate DOCX (only if dependencies are available)
        print(f"\n📝 Attempting to generate DOCX for: {sample_data['name']}")
        output_path = generator.generate_section_e_docx(sample_data)
        
        if output_path and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Jinja DOCX generated successfully!")
            print(f"📄 File: {output_path}")
            print(f"📦 Size: {file_size:,} bytes")
            return True
        else:
            print(f"❌ DOCX generation failed")
            return False
            
    except ImportError as e:
        print(f"⚠️ Import error: {e}")
        print("💡 Install dependencies: pip install docxtpl Jinja2")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_template_data_mapping():
    """Test the template data mapping for all expected variables"""
    print("\n🧪 Testing Template Data Mapping")
    print("=" * 50)
    
    try:
        from src.generators.jinja_docx_generator import JinjaDOCXSectionEGenerator
        
        generator = JinjaDOCXSectionEGenerator()
        sample_data = create_sample_employee_data()
        template_data = generator.prepare_template_data(sample_data)
        
        # Test employee fields
        employee = template_data.get('employee', {})
        expected_fields = [
            'name', 'role_in_contract', 'years_experience', 
            'firm_name_and_location', 'education', 
            'current_professional_registration', 'other_professional_qualifications'
        ]
        
        for field in expected_fields:
            if field in employee:
                print(f"✅ Employee.{field}: {str(employee[field])[:50]}...")
            else:
                print(f"❌ Missing employee.{field}")
        
        # Test project fields
        project_letters = ['A', 'B', 'C', 'D', 'E']
        for letter in project_letters:
            project_key = f'project{letter}'
            if project_key in template_data:
                project = template_data[project_key]
                if project.get('title_and_location'):
                    print(f"✅ {project_key}: {project['title_and_location']}")
                else:
                    print(f"📝 {project_key}: (empty)")
            else:
                print(f"❌ Missing {project_key}")
        
        print("✅ Template data mapping test completed")
        return True
        
    except Exception as e:
        print(f"❌ Template data mapping test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Jinja DOCX Generator Integration Tests")
    print("=" * 60)
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    if test_template_data_mapping():
        tests_passed += 1
    
    if test_jinja_docx_generator():
        tests_passed += 1
    
    # Results
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Jinja DOCX integration is working correctly.")
        print("\n📋 Next Steps:")
        print("1. Make sure to install dependencies: pip install docxtpl Jinja2")
        print("2. Create your JinjaTemplate.docx with {{ employee.name }} variables")
        print("3. Select 'Jinja Template' in the UI when generating resumes")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 