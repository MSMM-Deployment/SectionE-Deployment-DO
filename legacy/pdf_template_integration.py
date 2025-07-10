#!/usr/bin/env python3
"""
PDF Template Integration for Section E Forms

This script fills Section E PDF form templates with parsed employee data using pdfrw.
It maps JSON data fields to PDF form fields and generates individual filled forms for each employee.
"""

import json
import os
import sys
from pathlib import Path
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName, PdfObject


class SectionEPDFIntegrator:
    """Main class for integrating parsed employee data into Section E PDF templates."""
    
    def __init__(self, template_path, output_dir="OutputFiles/PDFs"):
        """
        Initialize the PDF integrator.
        
        Args:
            template_path (str): Path to the PDF template file
            output_dir (str): Directory to save filled PDF forms
        """
        self.template_path = template_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Field mapping from PDF form fields to JSON data paths
        # Note: Some fields are plain text, others are Unicode-encoded
        self.field_map_template = {
            # Plain text fields
            "Name12[0]": "name",
            "RoleinContract[0]": "role_in_contract", 
            "TotalYears[0]": "years_experience.total",
            # Unicode encoded fields (decoded from Unicode)
            "TotalYearsCurrentFirm[0]": "years_experience.with_current_firm",
            "FirmName[0]": "firm_name_and_location",
            "Education[0]": "education", 
            "CurrentProRegistration[0]": "current_professional_registration",
            "Qualifications[0]": "other_professional_qualifications"
        }
        
        # Project field patterns (will be generated dynamically)
        self.project_field_suffixes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        
    def decode_unicode_field_name(self, field_name):
        """
        Decode Unicode field names from PDF forms.
        
        Args:
            field_name (str): Raw field name from PDF
            
        Returns:
            str: Decoded field name
        """
        try:
            # Remove parentheses if present
            clean_name = field_name.strip('()')
            
            # Check if it's a Unicode string with BOM
            if clean_name.startswith('þÿ'):
                # Remove BOM and decode UTF-16
                unicode_bytes = clean_name[2:]  # Remove 'þÿ'
                # Convert the escaped Unicode to actual bytes
                try:
                    byte_string = unicode_bytes.encode('latin1')  # Convert to bytes
                    decoded = byte_string.decode('utf-16be', errors='ignore')  # Decode UTF-16
                    return decoded
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # If encoding fails, try to extract the field name manually
                    # Look for patterns like [0] to identify field boundaries
                    if '[0]' in clean_name:
                        # Extract everything before [0] and add [0] back
                        base_name = clean_name.split('[0]')[0]
                        # Try to extract readable characters
                        readable_chars = []
                        i = 2  # Skip 'þÿ'
                        while i < len(base_name) and i < 100:  # Safety limit
                            if base_name[i:i+2] == '\\x':
                                # Skip escape sequences
                                i += 4
                            elif base_name[i].isalnum():
                                readable_chars.append(base_name[i])
                                i += 1
                            else:
                                i += 1
                        if readable_chars:
                            return ''.join(readable_chars) + '[0]'
                    return clean_name
            else:
                return clean_name
        except Exception:
            return field_name.strip('()')
    
    def get_nested_value(self, data, key_path):
        """
        Get value from nested dictionary using dot notation.
        
        Args:
            data (dict): The data dictionary
            key_path (str): Dot-separated path to the value
            
        Returns:
            str: The value or empty string if not found
        """
        if not key_path or not isinstance(data, dict):
            return ""
            
        keys = key_path.split('.')
        current_data = data
        
        for key in keys:
            if isinstance(current_data, dict):
                current_data = current_data.get(key)
            else:
                return ""
                
        return str(current_data) if current_data is not None else ""
    
    def analyze_pdf_fields(self):
        """
        Analyze the PDF template to identify form fields.
        
        Returns:
            list: List of form field names found in the PDF
        """
        try:
            pdf = PdfReader(self.template_path)
            field_names = []
            
            for page in pdf.pages:
                if '/Annots' in page:
                    annotations = page['/Annots']
                    if annotations is not None:
                        try:
                            for annotation in annotations:
                                if (annotation.get('/Subtype') == '/Widget' and 
                                    annotation.get('/T')):
                                    field_name = str(annotation['/T'])[1:-1]  # Remove parentheses
                                    field_names.append(field_name)
                        except (TypeError, AttributeError):
                            continue
            
            return sorted(set(field_names))
            
        except Exception as e:
            print(f"Error analyzing PDF fields: {e}")
            return []
    
    def generate_project_field_map(self, num_projects):
        """
        Generate field mapping for project entries.
        
        Args:
            num_projects (int): Number of projects to map
            
        Returns:
            dict: Mapping of PDF fields to project data paths
        """
        project_map = {}
        
        for i, suffix in enumerate(self.project_field_suffixes[:num_projects]):
            base_index = f"relevant_projects.{i}"
            project_map.update({
                f"TitleandLocation{suffix}[0]": f"{base_index}.title_and_location",
                f"BriefDescription{suffix}[0]": f"{base_index}.description.scope",
                f"YearCompleted{suffix}[0]": f"{base_index}.year_completed.professional_services",
                f"ConstructionCost{suffix}[0]": f"{base_index}.description.cost",
                f"ProfessionalFee{suffix}[0]": f"{base_index}.description.fee",
                f"Role{suffix}[0]": f"{base_index}.description.role"
            })
            
        return project_map
    
    def clean_text_for_pdf(self, text):
        """
        Clean text for PDF form field insertion.
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text suitable for PDF forms
        """
        if not text:
            return ""
            
        # Basic text cleaning
        text = str(text).strip()
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Replace problematic Unicode characters
        text = text.replace('–', '-')  # En-dash to hyphen
        text = text.replace('—', '-')  # Em-dash to hyphen
        text = text.replace(''', "'")  # Smart quote to regular quote
        text = text.replace(''', "'")  # Smart quote to regular quote
        text = text.replace('"', '"')  # Smart quote to regular quote
        text = text.replace('"', '"')  # Smart quote to regular quote
        
        # Remove or replace other non-ASCII characters
        try:
            # Try to encode as latin-1 to check compatibility
            text.encode('latin-1')
        except UnicodeEncodeError:
            # If it fails, replace non-ASCII characters
            text = text.encode('ascii', errors='ignore').decode('ascii')
        
        # Truncate if too long (PDF forms have character limits)
        if len(text) > 500:
            text = text[:497] + "..."
            
        return text
    
    def fill_pdf_template(self, resume_data, output_path):
        """
        Fill PDF template with employee resume data.
        
        Args:
            resume_data (dict): Employee resume data
            output_path (str): Path to save the filled PDF
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read the template
            pdf = PdfReader(self.template_path)
            
            # Prepare field mapping including projects
            num_projects = len(resume_data.get('relevant_projects', []))
            project_field_map = self.generate_project_field_map(num_projects)
            complete_field_map = {**self.field_map_template, **project_field_map}
            
            # Fill form fields
            filled_fields = 0
            
            for page in pdf.pages:
                if '/Annots' in page:
                    annotations = page['/Annots']
                    if annotations is not None:
                        try:
                            for annotation in annotations:
                                if (annotation.get('/Subtype') == '/Widget' and 
                                    annotation.get('/T')):
                                    raw_field_name = str(annotation['/T'])
                                    field_name = self.decode_unicode_field_name(raw_field_name)
                                    
                                    if field_name in complete_field_map:
                                        value = self.get_nested_value(
                                            resume_data, 
                                            complete_field_map[field_name]
                                        )
                                        cleaned_value = self.clean_text_for_pdf(value)
                                        
                                        if cleaned_value:
                                            # Set the field value
                                            annotation.update(PdfDict(V=PdfObject(f"({cleaned_value})")))
                                            filled_fields += 1
                        except (TypeError, AttributeError, Exception):
                            continue
            
            # Write the filled PDF
            PdfWriter(output_path, trailer=pdf).write()
            print(f"✓ Successfully filled {filled_fields} fields in PDF: {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error filling PDF template: {e}")
            return False
    
    def create_clean_filename(self, name, role=""):
        """
        Create a clean filename from employee name and role.
        
        Args:
            name (str): Employee name
            role (str): Employee role (optional)
            
        Returns:
            str: Clean filename
        """
        # Remove common suffixes and clean the name
        clean_name = name.replace(", PE", "").replace(", LEED AP", "").replace(", PMP", "").replace(", CFM", "").replace(", MBA", "")
        clean_name = ''.join(c for c in clean_name if c.isalnum() or c in (' ', '-', '_'))
        clean_name = '_'.join(clean_name.split())
        
        if role:
            clean_role = ''.join(c for c in role if c.isalnum() or c in (' ', '-', '_'))
            clean_role = '_'.join(clean_role.split())
            return f"SectionE_{clean_name}_{clean_role}.pdf"
        else:
            return f"SectionE_{clean_name}.pdf"
    
    def process_all_employees(self, parsed_data_path):
        """
        Process all employees from parsed JSON data and generate filled PDFs.
        
        Args:
            parsed_data_path (str): Path to the parsed JSON data file
            
        Returns:
            dict: Processing results summary
        """
        try:
            # Load parsed data
            with open(parsed_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            employees = data.get('resumes', [])
            if not employees:
                return {
                    'success': False,
                    'message': 'No employee data found in JSON file',
                    'processed': 0,
                    'failed': 0,
                    'files': []
                }
            
            results = {
                'success': True,
                'processed': 0,
                'failed': 0,
                'files': [],
                'errors': []
            }
            
            print(f"Processing {len(employees)} employees...")
            print(f"Template: {self.template_path}")
            print(f"Output directory: {self.output_dir}")
            
            # Process each employee
            for i, employee in enumerate(employees, 1):
                employee_data = employee.get('data', {})
                employee_name = employee_data.get('name', f'Employee_{i}')
                employee_role = employee_data.get('role_in_contract', '')
                
                print(f"\n[{i}/{len(employees)}] Processing: {employee_name}")
                
                try:
                    # Create output filename
                    filename = self.create_clean_filename(employee_name, employee_role)
                    output_path = self.output_dir / filename
                    
                    # Fill the PDF template
                    success = self.fill_pdf_template(employee_data, str(output_path))
                    
                    if success:
                        results['processed'] += 1
                        results['files'].append(str(output_path))
                        print(f"   ✓ Generated: {filename}")
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Failed to process {employee_name}")
                        
                except Exception as e:
                    results['failed'] += 1
                    error_msg = f"Error processing {employee_name}: {str(e)}"
                    results['errors'].append(error_msg)
                    print(f"   ✗ {error_msg}")
            
            # Generate summary
            print(f"\n{'='*60}")
            print("PROCESSING SUMMARY")
            print(f"{'='*60}")
            print(f"Total employees: {len(employees)}")
            print(f"Successfully processed: {results['processed']}")
            print(f"Failed: {results['failed']}")
            print(f"Output directory: {self.output_dir}")
            
            if results['errors']:
                print(f"\nErrors encountered:")
                for error in results['errors']:
                    print(f"  - {error}")
            
            # Save processing results
            results_file = self.output_dir / "pdf_processing_results.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"\nDetailed results saved to: {results_file}")
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing employees: {str(e)}',
                'processed': 0,
                'failed': 0,
                'files': [],
                'errors': [str(e)]
            }


def main():
    """Main function to run the PDF template integration."""
    # Configuration
    template_path = "Section E template.pdf"
    parsed_data_path = "ParsedFiles/real_parsed_results.json"
    output_dir = "OutputFiles/PDFs"
    
    # Check if template exists
    if not os.path.exists(template_path):
        print(f"Error: Template file not found: {template_path}")
        return
    
    # Check if parsed data exists
    if not os.path.exists(parsed_data_path):
        print(f"Error: Parsed data file not found: {parsed_data_path}")
        return
    
    # Create integrator
    integrator = SectionEPDFIntegrator(template_path, output_dir)
    
    # Analyze PDF fields (optional - for debugging)
    print("Analyzing PDF form fields...")
    pdf_fields = integrator.analyze_pdf_fields()
    if pdf_fields:
        print(f"Found {len(pdf_fields)} form fields in the PDF template")
        print("Sample fields:", pdf_fields[:10])
    else:
        print("Warning: No form fields found in PDF template")
    
    # Process all employees
    results = integrator.process_all_employees(parsed_data_path)
    
    if results['success'] and results['processed'] > 0:
        print(f"\n🎉 Successfully generated {results['processed']} Section E PDF forms!")
    else:
        print("\n❌ PDF generation completed with issues. Check the error messages above.")


if __name__ == "__main__":
    main() 