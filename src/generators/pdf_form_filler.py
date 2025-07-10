#!/usr/bin/env python3
"""
PDF Form Filler for Section E Resumes

This script connects to Supabase to fetch employee data and generates
fillable PDF forms using the Section E template.

Usage:
python pdf_form_filler.py --employee_id <id>
python pdf_form_filler.py --employee_name "John Doe"
"""

import os
import io
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
    from PyPDF2 import PdfReader, PdfWriter
    from pdfrw import PdfReader as PdfrwReader, PdfWriter as PdfrwWriter, PdfDict
    import pdfrw
except ImportError as e:
    print(f"Missing required packages. Please install: pip install supabase PyPDF2 pdfrw")
    print(f"Error: {e}")
    exit(1)

# Load environment variables
load_dotenv()


class SectionEPDFGenerator:
    """Generate Section E PDF forms with Supabase data"""
    
    def __init__(self):
        """Initialize the PDF generator with optional Supabase connection"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # Initialize Supabase only if credentials are available
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self.use_supabase = True
            print("✅ Supabase connection initialized")
        else:
            self.supabase = None
            self.use_supabase = False
            print("⚠️ No Supabase credentials found. Will use JSON fallback.")
        
        # Use project root relative paths for Netlify compatibility
        project_root = Path(__file__).parent.parent.parent
        self.template_path = str(project_root / "templates" / "Section E template.pdf")
        self.output_dir = project_root / "OutputFiles" / "PDFs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = str(project_root / "data" / "ParsedFiles" / "real_parsed_results.json")
    
    def fetch_employee_by_id(self, employee_id: str) -> Optional[Dict]:
        """Fetch employee data by ID from Supabase or JSON fallback"""
        if self.use_supabase and self.supabase:
            try:
                # Fetch employee basic info
                employee_result = self.supabase.table('employees').select('*').eq('employee_id', employee_id).execute()
                
                if not employee_result.data:
                    print(f"No employee found with ID: {employee_id}")
                    return None
                
                employee = employee_result.data[0]
                
                # Fetch assignments and projects
                assignments_result = self.supabase.table('employee_assignments').select(
                    '*, teams(firm_name, location), projects(*)'
                ).eq('employee_id', employee_id).execute()
                
                return {
                    'employee': employee,
                    'assignments': assignments_result.data or []
                }
            except Exception as e:
                print(f"Error fetching employee {employee_id}: {e}")
                return None
        else:
            # Fallback to JSON
            return self.fetch_employee_from_json_by_id(employee_id)
    
    def fetch_employee_from_json_by_id(self, employee_id: str) -> Optional[Dict]:
        """Fetch employee data from JSON file by ID (fallback method)"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for resume in data.get('resumes', []):
                resume_data = resume.get('data', {})
                # For JSON, we'll match by name since we don't have employee_id
                # This is a limitation of the fallback approach
                print(f"JSON fallback doesn't support ID lookup. Use name-based lookup instead.")
                return None
                
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return None
    
    def fetch_employee_from_json_by_name(self, employee_name: str) -> Optional[Dict]:
        """Fetch employee data from JSON file by name (fallback method)"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for resume in data.get('resumes', []):
                resume_data = resume.get('data', {})
                json_name = resume_data.get('name', '').lower()
                # Allow partial matching - if the search name is contained in the JSON name
                if employee_name.lower() in json_name or json_name in employee_name.lower():
                    return {'employee_data': resume_data}
            
            print(f"Employee '{employee_name}' not found in JSON data")
            return None
                
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return None
    
    def fetch_employee_by_name(self, employee_name: str) -> Optional[Dict]:
        """Fetch employee data by name from Supabase or JSON fallback"""
        if self.use_supabase and self.supabase:
            try:
                # Search for employee by name (case-insensitive)
                employee_result = self.supabase.table('employees').select('*').ilike('employee_name', f'%{employee_name}%').execute()
                
                if not employee_result.data:
                    print(f"No employee found with name containing: {employee_name}")
                    return None
                
                if len(employee_result.data) > 1:
                    print(f"Multiple employees found. Using first match:")
                    for emp in employee_result.data:
                        print(f"  - {emp.get('employee_name')} (ID: {emp.get('employee_id')})")
                
                employee = employee_result.data[0]
                employee_id = employee['employee_id']
                
                # Fetch assignments and projects
                assignments_result = self.supabase.table('employee_assignments').select(
                    '*, teams(firm_name, location), projects(*)'
                ).eq('employee_id', employee_id).execute()
                
                return {
                    'employee': employee,
                    'assignments': assignments_result.data or []
                }
            except Exception as e:
                print(f"Error fetching employee {employee_name}: {e}")
                return None
        else:
            # Fallback to JSON
            return self.fetch_employee_from_json_by_name(employee_name)
    
    def format_employee_data(self, data: Dict) -> Dict:
        """Format employee data for PDF generation"""
        # Check if this is JSON data format or Supabase format
        if 'employee_data' in data:
            # This is JSON format
            return self.format_json_employee_data(data['employee_data'])
        
        # This is Supabase format
        employee = data['employee']
        assignments = data['assignments']
        
        # Get firm information from assignments
        firm_info = ""
        role_in_contract = ""
        if assignments:
            # Use the most recent assignment
            latest_assignment = max(assignments, key=lambda x: x.get('created_at', ''))
            if latest_assignment and latest_assignment.get('teams'):
                firm_name = latest_assignment['teams'].get('firm_name', '')
                location = latest_assignment['teams'].get('location', '')
                firm_info = f"{firm_name} - {location}" if location else firm_name
            if latest_assignment:
                role_in_contract = latest_assignment.get('role_in_contract', '')
        
        # Extract other professional qualifications from assignments
        other_qualifications = ""
        if assignments:
            # Get all unique qualifications from assignments and combine them
            qualifications = []
            for assignment in assignments:
                qual = assignment.get('other_professional_qualifications', '')
                if qual and qual.strip() and qual.strip() not in qualifications:
                    qualifications.append(qual.strip())
            other_qualifications = '; '.join(qualifications)

        # Format projects
        projects = []
        for assignment in assignments:
            if assignment.get('projects'):
                project = assignment['projects']
                projects.append({
                    'title_and_location': project.get('project_title', ''),
                    'year_completed': {
                        'professional_services': project.get('professional_services_year', ''),
                        'construction': project.get('construction_year', '')
                    },
                    'description': {
                        'scope': project.get('project_description', ''),
                        'cost': project.get('project_cost', ''),
                        'role': assignment.get('role_in_contract', '')
                    }
                })
        
        return {
            'name': employee.get('employee_name', ''),
            'role_in_contract': role_in_contract,
            'years_experience': {
                'total': str(employee.get('total_years_experience', '')),
                'with_current_firm': str(employee.get('current_firm_years_experience', ''))
            },
            'firm_name_and_location': firm_info,
            'education': employee.get('education', ''),
            'current_professional_registration': employee.get('current_professional_registration', ''),
            'other_professional_qualifications': other_qualifications,
            'relevant_projects': projects
        }
    
    def format_json_employee_data(self, employee_data: Dict) -> Dict:
        """Format JSON employee data for PDF generation"""
        # The JSON data is already in the correct format mostly
        return {
            'name': employee_data.get('name', ''),
            'role_in_contract': employee_data.get('role_in_contract', ''),
            'years_experience': employee_data.get('years_experience', {}),
            'firm_name_and_location': employee_data.get('firm_name_and_location', ''),
            'education': employee_data.get('education', ''),
            'current_professional_registration': employee_data.get('current_professional_registration', ''),
            'other_professional_qualifications': employee_data.get('other_professional_qualifications', ''),
            'relevant_projects': employee_data.get('relevant_projects', [])
        }
    
    def inspect_pdf_fields(self) -> List[str]:
        """Inspect the fillable fields in the PDF template"""
        try:
            if not os.path.exists(self.template_path):
                print(f"❌ Template not found: {self.template_path}")
                return []
            
            # Use PyPDF2 for better field detection
            from PyPDF2 import PdfReader
            
            with open(self.template_path, 'rb') as file:
                reader = PdfReader(file)
                
                # Get form fields
                fields = []
                if hasattr(reader, 'get_fields'):
                    pdf_fields = reader.get_fields()
                    if pdf_fields:
                        fields = list(pdf_fields.keys())
                
                print(f"📋 Found {len(fields)} fillable fields in template:")
                for field in sorted(fields):
                    print(f"  - {field}")
                
                return fields
            
        except Exception as e:
            print(f"❌ Error inspecting PDF fields: {e}")
            return []
    
    def create_field_mapping(self) -> Dict[str, str]:
        """Create mapping between PDF fields and our data structure"""
        return {
            # Employee basic information - mapped to actual PDF field names
            'Name12[0]': 'name',
            'RoleinContract[0]': 'role_in_contract',
            'TotalYears[0]': 'years_experience.total',
            'TotalYearsCurrentFirm[0]': 'years_experience.with_current_firm',
            'FirmName[0]': 'firm_name_and_location',
            'Education[0]': 'education',
            'CurrentProRegistration[0]': 'current_professional_registration',
            'Qualifications[0]': 'other_professional_qualifications',
            
            # Project fields - mapped to actual PDF field names
            # Project A
            'TitleandLocationA[0]': 'projects.0.title_and_location',
            'DateofProfessionalServices[0]': 'projects.0.year_completed.professional_services',
            'DateofConstruction[0]': 'projects.0.year_completed.construction',
            'BriefDescriptionA[0]': 'projects.0.description.scope',
            
            # Project B
            'TitleandLocationB[0]': 'projects.1.title_and_location',
            'DateofProfessionalServices[1]': 'projects.1.year_completed.professional_services',
            'DateofConstruction[1]': 'projects.1.year_completed.construction',
            'BriefDescriptionB[0]': 'projects.1.description.scope',
            
            # Project C
            'TitleandLocationC[0]': 'projects.2.title_and_location',
            'DateofProfessionalServices[2]': 'projects.2.year_completed.professional_services',
            'DateofConstruction[2]': 'projects.2.year_completed.construction',
            'BriefDescriptionC[0]': 'projects.2.description.scope',
            
            # Project D
            'TitleandLocationD[0]': 'projects.3.title_and_location',
            'DateofProfessionalServices[3]': 'projects.3.year_completed.professional_services',
            'DateofConstruction[3]': 'projects.3.year_completed.construction',
            'BriefDescriptionD[0]': 'projects.3.description.scope',
            
            # Project E
            'TitleandLocationE[0]': 'projects.4.title_and_location',
            'DateofProfessionalServices[4]': 'projects.4.year_completed.professional_services',
            'DateofConstruction[4]': 'projects.4.year_completed.construction',
            'BriefDescriptionE[0]': 'projects.4.description.scope',
            
            # Project checkboxes for "performed with same firm" - corrected field names
            'CheckBoxA[0]': 'projects.0.performed_with_same_firm',
            'CheckBoxB[0]': 'projects.1.performed_with_same_firm',
            'CheckBoxC[0]': 'projects.2.performed_with_same_firm',
            'CheckBoxD[0]': 'projects.3.performed_with_same_firm',
            'CheckBoxE[0]': 'projects.4.performed_with_same_firm',
        }
    
    def get_raw_nested_value(self, data: Dict, path: str):
        """Get raw value from nested dictionary using dot notation without conversion"""
        try:
            keys = path.split('.')
            value = data
            
            for key in keys:
                if key.isdigit():
                    # Handle array index
                    index = int(key)
                    if isinstance(value, list) and index < len(value):
                        value = value[index]
                    else:
                        return None
                else:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return None
            
            return value
            
        except Exception:
            return None
    
    def get_nested_value(self, data: Dict, path: str) -> str:
        """Get value from nested dictionary using dot notation"""
        try:
            keys = path.split('.')
            value = data
            
            for key in keys:
                if key.isdigit():
                    # Handle array index
                    index = int(key)
                    if isinstance(value, list) and index < len(value):
                        value = value[index]
                    else:
                        return ""
                else:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return ""
            
            # Handle boolean values for checkboxes
            if isinstance(value, bool):
                # For PDF checkboxes, return "/On" when checked, "/Off" when unchecked
                return "/On" if value else "/Off"
            
            return str(value) if value else ""
            
        except Exception:
            return ""
    
    def update_checkbox_fields_pdfrw(self, pdf_path: str, checkbox_fields: Dict[str, str]):
        """Update checkbox fields using pdfrw for better compatibility"""
        try:
            import pdfrw
            from pdfrw import PdfReader as PdfrwReader, PdfWriter as PdfrwWriter
            
            # Read the PDF with pdfrw
            template = PdfrwReader(pdf_path)
            
            # Find and update checkbox fields
            for page in template.pages:
                if page.Annots:
                    for annot in page.Annots:
                        if annot.T and annot.T[1:-1] in checkbox_fields:  # Remove parentheses from field name
                            field_name = annot.T[1:-1]
                            field_value = checkbox_fields[field_name]
                            
                            print(f"🔧 Updating checkbox field: {field_name} = {field_value}")
                            
                            # Set the value and appearance state
                            if field_value == '/On':
                                annot.update(pdfrw.PdfDict(V=pdfrw.PdfName.On, AS=pdfrw.PdfName.On))
                            else:
                                annot.update(pdfrw.PdfDict(V=pdfrw.PdfName.Off, AS=pdfrw.PdfName.Off))
            
            # Write the updated PDF
            PdfrwWriter(pdf_path, trailer=template).write()
            print(f"✅ Updated checkboxes using pdfrw")
            
        except Exception as e:
            print(f"❌ Error updating checkboxes with pdfrw: {e}")
    
    def create_section_e_pdf(self, employee_data: Dict, output_filename: Optional[str] = None) -> str:
        """Fill the Section E PDF template with employee data"""
        if not output_filename:
            safe_name = "".join(c for c in employee_data['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_filename = f"SectionE_{safe_name.replace(' ', '_')}.pdf"
        
        output_path = self.output_dir / output_filename
        
        try:
            # Check if template exists
            if not os.path.exists(self.template_path):
                raise Exception(f"Template not found: {self.template_path}")
            
            # Use PyPDF2 for better field handling
            from PyPDF2 import PdfReader, PdfWriter
            
            # Read the PDF template
            with open(self.template_path, 'rb') as template_file:
                reader = PdfReader(template_file)
                writer = PdfWriter()
                
                # Get field mapping
                field_mapping = self.create_field_mapping()
                
                # Prepare the data with projects array
                form_data = employee_data.copy()
                projects = employee_data.get('relevant_projects', [])
                form_data['projects'] = projects
                
                # Get all form fields
                form_fields = {}
                if hasattr(reader, 'get_fields'):
                    pdf_fields = reader.get_fields()
                    if pdf_fields:
                        form_fields = pdf_fields
                
                # Prepare field values to fill
                field_values = {}
                filled_count = 0
                
                print(f"🔍 Processing {len(field_mapping)} field mappings...")
                print(f"🔍 Projects data: {form_data.get('projects', [])}")
                
                for pdf_field_name, data_path in field_mapping.items():
                    if pdf_field_name in form_fields:
                        # Get the raw value first to check if it's a boolean
                        raw_value = self.get_raw_nested_value(form_data, data_path)
                        value = self.get_nested_value(form_data, data_path)
                        
                        # For checkboxes, we want to include both checked (True) and unchecked (False) values
                        # For other fields, we only include non-empty values
                        is_checkbox = 'checkbox' in pdf_field_name.lower() or data_path.endswith('performed_with_same_firm')
                        should_include = value or (is_checkbox and isinstance(raw_value, bool))
                        
                        if should_include:
                            field_values[pdf_field_name] = str(value)
                            filled_count += 1
                            if is_checkbox:
                                print(f"✓ 📋 CHECKBOX: '{pdf_field_name}' = {value} (raw: {raw_value})")
                            else:
                                print(f"✓ Mapping '{pdf_field_name}' to: {str(value)[:50]}...")
                        else:
                            if is_checkbox:
                                print(f"⚠️ 📋 CHECKBOX MISSING: '{pdf_field_name}' - path: '{data_path}'")
                            else:
                                print(f"⚠️ No value found for path '{data_path}' in field '{pdf_field_name}'")
                    else:
                        print(f"⚠️ PDF field '{pdf_field_name}' not found in template")
                
                # Clone pages and fill fields
                for page_num, page in enumerate(reader.pages):
                    # Clone the page
                    new_page = writer.add_page(page)
                
                                # Update form fields if we have values to fill
                if field_values:
                    # Try different checkbox values for better compatibility
                    checkbox_test_values = {}
                    other_fields = {}
                    
                    for field_name, field_value in field_values.items():
                        if field_name.lower().startswith('checkbox'):
                            # Try standard checkbox values
                            if field_value == '/On':
                                checkbox_test_values[field_name] = '1'  # Try '1' for checked
                            else:
                                checkbox_test_values[field_name] = '0'  # '0' for unchecked
                            print(f"🔧 Converting checkbox {field_name}: {field_value} → {checkbox_test_values[field_name]}")
                        else:
                            other_fields[field_name] = field_value
                    
                    # Combine all fields with converted checkbox values
                    all_fields = {**other_fields, **checkbox_test_values}
                    writer.update_page_form_field_values(writer.pages[0], all_fields)
                
                # Write the filled PDF
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                print(f"✅ PDF generated successfully: {output_path}")
                print(f"📊 Filled {filled_count} fields")
                
                return str(output_path)
            
        except Exception as e:
            print(f"❌ Error creating PDF with PyPDF2: {e}")
            # Fallback to simple text-based approach if template filling fails
            return self.create_simple_pdf_fallback(employee_data, output_filename)
    
    def create_simple_pdf_fallback(self, employee_data: Dict, output_filename: str) -> str:
        """Create a simple PDF when template filling fails"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            output_path = self.output_dir / output_filename
            
            # Create simple PDF with basic information
            c = canvas.Canvas(str(output_path), pagesize=letter)
            width, height = letter
            
            # Title
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "STANDARD FORM 330 - SECTION E")
            
            # Employee info
            y = height - 100
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "EMPLOYEE INFORMATION")
            
            y -= 30
            c.setFont("Helvetica", 10)
            
            # Basic fields
            fields = [
                ("Name:", employee_data.get('name', '')),
                ("Role:", employee_data.get('role_in_contract', '')),
                ("Experience:", f"{employee_data.get('years_experience', {}).get('total', '')} years total"),
                ("Firm:", employee_data.get('firm_name_and_location', '')),
                ("Education:", employee_data.get('education', '')),
            ]
            
            for label, value in fields:
                c.drawString(50, y, f"{label} {value}")
                y -= 20
            
            c.save()
            print(f"✅ Fallback PDF created: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Fallback PDF creation failed: {e}")
            raise
    
    def generate_resume_by_id(self, employee_id: str) -> Optional[str]:
        """Generate Section E resume for employee by ID"""
        print(f"🔍 Fetching employee data for ID: {employee_id}")
        
        data = self.fetch_employee_by_id(employee_id)
        if not data:
            return None
        
        employee_data = self.format_employee_data(data)
        
        print(f"📄 Generating Section E PDF for: {employee_data['name']}")
        return self.create_section_e_pdf(employee_data)
    
    def generate_resume_by_name(self, employee_name: str) -> Optional[str]:
        """Generate Section E resume for employee by name"""
        print(f"🔍 Searching for employee: {employee_name}")
        
        data = self.fetch_employee_by_name(employee_name)
        if not data:
            return None
        
        employee_data = self.format_employee_data(data)
        
        print(f"📄 Generating Section E PDF for: {employee_data['name']}")
        return self.create_section_e_pdf(employee_data)
    
    def list_employees(self) -> List[Dict]:
        """List all employees in the database"""
        try:
            result = self.supabase.table('employees').select('employee_id, employee_name, total_years_experience').execute()
            return result.data or []
        except Exception as e:
            print(f"Error listing employees: {e}")
            return []
    
    def inspect_pdf_fields_from_file(self, template_path: str) -> List[str]:
        """Inspect PDF form fields from a specific template file"""
        try:
            from PyPDF2 import PdfReader
            
            if not os.path.exists(template_path):
                print(f"❌ Template not found: {template_path}")
                return []
            
            print(f"🔍 Inspecting PDF template: {template_path}")
            
            with open(template_path, 'rb') as file:
                reader = PdfReader(file)
                
                fields = reader.get_fields() if hasattr(reader, 'get_fields') else None
                if not fields:
                    print("❌ No form fields found in this PDF")
                    return []
                
                field_names = []
                
                print(f"\n📋 Found {len(fields)} form fields:")
                print("=" * 60)
                
                for field_name, field_obj in fields.items():
                    field_type = "Unknown"
                    field_value = "None"
                    
                    try:
                        # Try to get field type and value
                        if hasattr(field_obj, 'field_type'):
                            field_type = field_obj.field_type
                        elif hasattr(field_obj, '/FT'):
                            field_type = str(field_obj['/FT'])
                        
                        if hasattr(field_obj, 'value'):
                            field_value = field_obj.value
                        elif hasattr(field_obj, '/V'):
                            field_value = str(field_obj['/V'])
                            
                    except Exception as e:
                        pass
                    
                    # Check if it's a checkbox
                    is_checkbox = 'checkbox' in field_name.lower() or field_type == '/Btn'
                    checkbox_marker = "📋 [CHECKBOX]" if is_checkbox else ""
                    
                    print(f"{checkbox_marker} {field_name}")
                    print(f"    Type: {field_type}")
                    print(f"    Value: {field_value}")
                    print("-" * 40)
                    
                    field_names.append(field_name)
                
                return field_names
                
        except Exception as e:
            print(f"❌ Error inspecting PDF: {e}")
            return []


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate Section E PDF resumes from Supabase data')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--employee_id', help='Employee ID to generate resume for')
    group.add_argument('--employee_name', help='Employee name to search for and generate resume')
    group.add_argument('--list', action='store_true', help='List all employees')
    group.add_argument('--inspect', action='store_true', help='Inspect PDF template fields')
    
    args = parser.parse_args()
    
    try:
        if args.inspect:
            # Don't need Supabase connection for inspection
            print("🔍 Inspecting PDF template fields...")
            template_path = "Section E template.pdf"
            if not os.path.exists(template_path):
                print(f"❌ Template not found: {template_path}")
                return
            
            # Create a minimal generator instance just for inspection
            class InspectorOnly:
                def __init__(self):
                    self.template_path = template_path
                def inspect_pdf_fields(self):
                    return SectionEPDFGenerator.inspect_pdf_fields(self)
            
            inspector = InspectorOnly()
            fields = inspector.inspect_pdf_fields()
            
            if fields:
                print(f"\n💡 Next steps:")
                print("1. Update the create_field_mapping() method with actual field names")
                print("2. Test PDF generation with: python pdf_form_filler.py --employee_name 'Employee Name'")
            
            return
        
        generator = SectionEPDFGenerator()
        
        if args.list:
            employees = generator.list_employees()
            if employees:
                print(f"\n📋 Found {len(employees)} employees:")
                for emp in employees:
                    exp = emp.get('total_years_experience', 'N/A')
                    print(f"  - {emp['employee_name']} (ID: {emp['employee_id']}, Experience: {exp} years)")
            else:
                print("No employees found in database.")
        
        elif args.employee_id:
            pdf_path = generator.generate_resume_by_id(args.employee_id)
            if pdf_path:
                print(f"✅ Resume generated: {pdf_path}")
            else:
                print("❌ Failed to generate resume")
        
        elif args.employee_name:
            pdf_path = generator.generate_resume_by_name(args.employee_name)
            if pdf_path:
                print(f"✅ Resume generated: {pdf_path}")
            else:
                print("❌ Failed to generate resume")
                
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main() 