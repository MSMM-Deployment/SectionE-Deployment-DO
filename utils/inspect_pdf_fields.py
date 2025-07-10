#!/usr/bin/env python3
"""
PDF Field Inspector for Section E Template

This script inspects the fillable fields in the Section E template PDF
to understand the exact field names and structure.

Usage:
python inspect_pdf_fields.py
"""

import os
from pathlib import Path

def inspect_with_pdfrw():
    """Inspect PDF fields using pdfrw library"""
    try:
        from pdfrw import PdfReader
        
        template_path = "Section E template.pdf"
        if not os.path.exists(template_path):
            print(f"❌ Template not found: {template_path}")
            return
        
        print("🔍 Inspecting PDF fields with pdfrw...")
        template = PdfReader(template_path)
        
        print(f"📄 PDF Info:")
        print(f"  - Pages: {len(template.pages) if template.pages else 'Unknown'}")
        print(f"  - Has AcroForm: {hasattr(template.Root, 'AcroForm') and template.Root.AcroForm is not None}")
        
        if hasattr(template.Root, 'AcroForm') and template.Root.AcroForm:
            acro_form = template.Root.AcroForm
            print(f"  - AcroForm Fields: {hasattr(acro_form, 'Fields') and acro_form.Fields is not None}")
            
            if hasattr(acro_form, 'Fields') and acro_form.Fields:
                fields = acro_form.Fields
                print(f"\n📋 Found {len(fields)} fillable fields:")
                
                for i, field in enumerate(fields):
                    field_name = "Unknown"
                    field_type = "Unknown"
                    
                    if hasattr(field, 'T') and field.T:
                        field_name = str(field.T).replace('(', '').replace(')', '')
                    
                    if hasattr(field, 'FT') and field.FT:
                        field_type = str(field.FT).replace('/', '')
                    
                    print(f"  {i+1:2d}. {field_name:<40} (Type: {field_type})")
                
                return fields
            else:
                print("  - No Fields found in AcroForm")
        else:
            print("  - No AcroForm found")
            
    except ImportError:
        print("⚠️ pdfrw not available. Install with: pip install pdfrw")
    except Exception as e:
        print(f"❌ Error with pdfrw: {e}")

def inspect_with_pypdf2():
    """Inspect PDF fields using PyPDF2 library"""
    try:
        from PyPDF2 import PdfReader
        
        template_path = "Section E template.pdf"
        if not os.path.exists(template_path):
            print(f"❌ Template not found: {template_path}")
            return
        
        print("\n🔍 Inspecting PDF fields with PyPDF2...")
        with open(template_path, 'rb') as file:
            reader = PdfReader(file)
            
            print(f"📄 PDF Info:")
            print(f"  - Pages: {len(reader.pages)}")
            
            # Try to get form fields
            if hasattr(reader, 'get_form_text_fields'):
                fields = reader.get_form_text_fields()
                if fields:
                    print(f"\n📋 Found {len(fields)} text fields:")
                    for name, value in fields.items():
                        print(f"  - {name}: {value}")
                else:
                    print("  - No text fields found")
            
            # Try alternative method
            if hasattr(reader, 'get_fields'):
                fields = reader.get_fields()
                if fields:
                    print(f"\n📋 Found {len(fields)} fields:")
                    for name, field in fields.items():
                        field_type = field.get('/FT', 'Unknown')
                        print(f"  - {name:<40} (Type: {field_type})")
                else:
                    print("  - No fields found")
                    
    except ImportError:
        print("⚠️ PyPDF2 not available. Install with: pip install PyPDF2")
    except Exception as e:
        print(f"❌ Error with PyPDF2: {e}")

def create_sample_mapping():
    """Create a sample field mapping based on typical Section E forms"""
    print("\n📝 Sample Field Mapping (update based on actual field names):")
    
    sample_mapping = {
        # Common field name patterns in government forms
        "Name": "employee_name",
        "12_NAME": "employee_name", 
        "NAME_12": "employee_name",
        "field_12": "employee_name",
        
        "Role": "role_in_contract",
        "13_ROLE": "role_in_contract",
        "ROLE_13": "role_in_contract",
        "field_13": "role_in_contract",
        
        "Total_Experience": "years_experience.total",
        "14a_TOTAL": "years_experience.total",
        "field_14a": "years_experience.total",
        
        "Current_Firm_Experience": "years_experience.with_current_firm",
        "14b_WITH_CURRENT_FIRM": "years_experience.with_current_firm",
        "field_14b": "years_experience.with_current_firm",
        
        "Firm_Name": "firm_name_and_location",
        "15_FIRM": "firm_name_and_location",
        "field_15": "firm_name_and_location",
        
        "Education": "education",
        "16_EDUCATION": "education",
        "field_16": "education",
        
        "Registration": "current_professional_registration",
        "17_REGISTRATION": "current_professional_registration",
        "field_17": "current_professional_registration",
        
        "Qualifications": "other_professional_qualifications",
        "18_QUALIFICATIONS": "other_professional_qualifications",
        "field_18": "other_professional_qualifications",
        
        # Project fields
        "Project_A_Title": "projects.0.title_and_location",
        "a_1_TITLE": "projects.0.title_and_location",
        "field_a1": "projects.0.title_and_location",
        
        "Project_A_Year": "projects.0.year_completed.professional_services",
        "a_2_YEAR": "projects.0.year_completed.professional_services",
        "field_a2": "projects.0.year_completed.professional_services",
        
        "Project_A_Description": "projects.0.description.scope",
        "a_3_DESCRIPTION": "projects.0.description.scope",
        "field_a3": "projects.0.description.scope",
    }
    
    for pdf_field, data_path in sample_mapping.items():
        print(f"  '{pdf_field}': '{data_path}',")

def generate_updated_mapping_code(fields):
    """Generate Python code for field mapping based on discovered fields"""
    if not fields:
        return
    
    print("\n🔧 Generated Field Mapping Code:")
    print("def create_field_mapping(self) -> Dict[str, str]:")
    print("    \"\"\"Create mapping between PDF fields and our data structure\"\"\"")
    print("    return {")
    
    # Try to map common patterns
    for field in fields:
        field_name = str(field.T).replace('(', '').replace(')', '') if hasattr(field, 'T') and field.T else "unknown"
        
        # Basic pattern matching
        data_path = "unknown"
        if "name" in field_name.lower() or "12" in field_name:
            data_path = "name"
        elif "role" in field_name.lower() or "13" in field_name:
            data_path = "role_in_contract"
        elif "total" in field_name.lower() or "14a" in field_name:
            data_path = "years_experience.total"
        elif "firm" in field_name.lower() or "current" in field_name.lower() or "14b" in field_name:
            data_path = "years_experience.with_current_firm"
        elif "firm" in field_name.lower() or "15" in field_name:
            data_path = "firm_name_and_location"
        elif "education" in field_name.lower() or "16" in field_name:
            data_path = "education"
        elif "registration" in field_name.lower() or "17" in field_name:
            data_path = "current_professional_registration"
        elif "qualification" in field_name.lower() or "18" in field_name:
            data_path = "other_professional_qualifications"
        
        print(f"        '{field_name}': '{data_path}',")
    
    print("    }")

def main():
    """Main function"""
    print("🚀 PDF Field Inspector for Section E Template")
    print("=" * 50)
    
    # Check if template exists
    template_path = "Section E template.pdf"
    if not os.path.exists(template_path):
        print(f"❌ Template not found: {template_path}")
        print("💡 Make sure the 'Section E template.pdf' file is in the current directory")
        return
    
    print(f"✅ Found template: {template_path}")
    file_size = os.path.getsize(template_path)
    print(f"📦 File size: {file_size:,} bytes")
    
    # Try both libraries
    fields_pdfrw = inspect_with_pdfrw()
    inspect_with_pypdf2()
    
    # Generate mapping suggestions
    create_sample_mapping()
    
    if fields_pdfrw:
        generate_updated_mapping_code(fields_pdfrw)
    
    print("\n💡 Instructions:")
    print("1. Copy the actual field names from the output above")
    print("2. Update the create_field_mapping() method in src/generators/pdf_form_filler.py")
    print("3. Map each PDF field to the correct data path")
    print("4. Test with: python3 src/generators/pdf_form_filler.py --list")

if __name__ == "__main__":
    main() 