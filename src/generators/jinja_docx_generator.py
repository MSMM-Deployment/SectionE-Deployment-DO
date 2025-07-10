#!/usr/bin/env python3
"""
Jinja DOCX Section E Generator

This script generates Section E resumes using Jinja-templated Word (.docx) files.
Supports {{ employee.name }} style template variables with case insensitivity.
Handles multiple projects (projectA, projectB, etc. up to projectE).
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from docxtpl import DocxTemplate
from jinja2 import Environment

# Add project root to Python path for utils imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils.supabase_template_downloader import SupabaseTemplateDownloader


class JinjaDOCXSectionEGenerator:
    """Generate Section E resumes using Jinja-templated DOCX files"""
    
    def __init__(self, template_path: str = "templates/JinjaTemplate.docx"):
        """
        Initialize the Jinja DOCX generator
        
        Args:
            template_path (str): Path to the Jinja DOCX template file (local path or filename)
        """
        self.template_path = template_path
        self.output_dir = Path("OutputFiles/DOCX")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize template downloader for cloud templates
        self.template_downloader = SupabaseTemplateDownloader()
    
    def normalize_template_variables(self, doc_content: str) -> str:
        """
        Normalize template variables to handle case insensitivity.
        Converts all Jinja variables to lowercase for consistent processing.
        
        Args:
            doc_content (str): Document content with Jinja variables
            
        Returns:
            str: Document content with normalized variables
        """
        # Pattern to find Jinja variables like {{ EMPLOYEE.NAME }} or {{ Employee.Name }}
        jinja_pattern = r'\{\{\s*([^}]+)\s*\}\}'
        
        def normalize_variable(match):
            variable = match.group(1).strip()
            # Convert to lowercase for consistency
            normalized = variable.lower()
            return f"{{{{ {normalized} }}}}"
        
        return re.sub(jinja_pattern, normalize_variable, doc_content)
    
    def prepare_template_data(self, employee_data: Dict) -> Dict:
        """
        Prepare template data for Jinja rendering based on employee data.
        Maps the current data structure to the expected template variables.
        
        Args:
            employee_data (Dict): Employee data dictionary
            
        Returns:
            Dict: Template data for Jinja rendering
        """
        # Extract basic employee information
        employee = {
            'name': employee_data.get('name', ''),
            'role_in_contract': employee_data.get('role_in_contract', ''),
            'years_experience': {
                'total': str(employee_data.get('years_experience', {}).get('total', '')),
                'with_current_firm': str(employee_data.get('years_experience', {}).get('with_current_firm', ''))
            },
            'firm_name_and_location': employee_data.get('firm_name_and_location', ''),
            'education': employee_data.get('education', ''),
            'current_professional_registration': employee_data.get('current_professional_registration', ''),
            'other_professional_qualifications': employee_data.get('other_professional_qualifications', '')
        }
        
        # Process projects - map to projectA, projectB, etc.
        projects = employee_data.get('relevant_projects', [])
        project_letters = ['A', 'B', 'C', 'D', 'E']  # Support up to 5 projects
        
        template_data = {'employee': employee}
        
        # Prepare project data for both individual access (projectA) and list access (projects)
        project_list = []
        
        # Map each project to projectA, projectB, etc.
        for i, project in enumerate(projects[:5]):  # Limit to 5 projects (A-E)
            project_key = f'project{project_letters[i]}'
            
            # Extract project data with safe fallbacks
            # Check if the data already has title_and_location (new format) or needs to be constructed (old format)
            if 'title_and_location' in project:
                # New format: already has combined title_and_location
                title_location = project.get('title_and_location', '')
            else:
                # Old format: construct from separate title and location fields
                title_location = project.get('title', '') + (f" - {project.get('location', '')}" if project.get('location') else '')
            
            project_data = {
                'title_and_location': title_location,
                'year_completed': {
                    'professional_services': str(project.get('year_completed', {}).get('professional_services', '')),
                    'construction': str(project.get('year_completed', {}).get('construction', ''))
                },
                'description': {
                    'scope': project.get('description', {}).get('scope', ''),
                    'cost': project.get('description', {}).get('cost', ''),
                    'fee': project.get('description', {}).get('fee', ''),
                    'role': project.get('description', {}).get('role', '')
                }
            }
            
            template_data[project_key] = project_data
            project_list.append(project_data)
        
        # Create empty projects for unused slots
        for i in range(len(projects), 5):
            project_key = f'project{project_letters[i]}'
            empty_project = {
                'title_and_location': '',
                'year_completed': {
                    'professional_services': '',
                    'construction': ''
                },
                'description': {
                    'scope': '',
                    'cost': '',
                    'fee': '',
                    'role': ''
                }
            }
            template_data[project_key] = empty_project
        
        # Add projects as a list for templates that use loops
        template_data['projects'] = project_list  # type: ignore
        
        # Add backward compatibility: if template uses {{ project }} in a loop context,
        # provide the first project as {{ project }} for simple templates
        if project_list:
            template_data['project'] = project_list[0]
        else:
            template_data['project'] = {
                'title_and_location': '',
                'year_completed': {
                    'professional_services': '',
                    'construction': ''
                },
                'description': {
                    'scope': '',
                    'cost': '',
                    'fee': '',
                    'role': ''
                }
            }
        
        return template_data
    
    def generate_section_e_docx(self, employee_data: Dict, output_filename: Optional[str] = None) -> str:
        """
        Generate Section E DOCX using Jinja template
        
        Args:
            employee_data (Dict): Employee data dictionary
            output_filename (Optional[str]): Custom output filename
            
        Returns:
            str: Path to generated DOCX file
        """
        # Get template path (check local first, then download from Supabase if needed)
        if os.path.exists(self.template_path):
            # Use local template
            actual_template_path = self.template_path
            print(f"📄 Using local template: {actual_template_path}")
        else:
            # Try to get template using downloader (for Supabase cloud templates)
            template_filename = os.path.basename(self.template_path)
            actual_template_path = self.template_downloader.get_template_path(template_filename)
            if not actual_template_path:
                raise FileNotFoundError(f"Jinja template not found locally or in cloud: {self.template_path}")
        
        # Generate output filename
        if not output_filename:
            safe_name = "".join(c for c in employee_data.get('name', 'Unknown') if c.isalnum() or c in (' ', '-', '_')).strip()
            output_filename = f"SectionE_Jinja_{safe_name.replace(' ', '_')}.docx"
        
        output_path = self.output_dir / output_filename
        
        try:
            # Load the Jinja template
            print(f"📄 Loading Jinja template: {actual_template_path}")
            doc = DocxTemplate(actual_template_path)
            
            # Prepare template data
            template_data = self.prepare_template_data(employee_data)
            
            print(f"📝 Rendering template for: {employee_data.get('name', 'Unknown')}")
            print(f"🔧 Template data includes {len([k for k in template_data.keys() if k.startswith('project')])} project entries")
            
            # Debug: Print project data
            print("🔍 DEBUG: Project data being passed to template:")
            for key in ['projectA', 'projectB', 'projectC', 'projectD', 'projectE']:
                if key in template_data:
                    project = template_data[key]
                    print(f"   {key}: {project.get('title_and_location', 'NO TITLE')}")
                    if project.get('title_and_location'):
                        print(f"      Year: {project.get('year_completed', {}).get('professional_services', 'N/A')}")
                        print(f"      Scope: {project.get('description', {}).get('scope', 'N/A')[:50]}...")
            
            # Debug: Print source project data
            print("🔍 DEBUG: Source project data:")
            source_projects = employee_data.get('relevant_projects', [])
            for i, proj in enumerate(source_projects[:3]):
                print(f"   Project {i+1}: {proj.get('title', 'NO TITLE')} - {proj.get('location', 'NO LOCATION')}")
                print(f"      Full data: {proj}")
            
            # Render the template with the data
            doc.render(template_data)
            
            # Save the document
            doc.save(str(output_path))
            print(f"✅ Jinja DOCX generated successfully: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Error generating Jinja DOCX: {e}")
            raise
    
    def process_json_file(self, json_path: str) -> List[str]:
        """
        Process all employees from a JSON file
        
        Args:
            json_path (str): Path to JSON file with employee data
            
        Returns:
            List[str]: List of generated file paths
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        employees = data.get('resumes', [])
        if not employees:
            raise ValueError("No employee data found in JSON file")
        
        generated_files = []
        print(f"🚀 Processing {len(employees)} employees with Jinja template...")
        
        for i, employee in enumerate(employees, 1):
            try:
                employee_data = employee.get('data', employee)  # Handle both formats
                name = employee_data.get('name', f'Employee_{i}')
                print(f"\n📝 Processing {i}/{len(employees)}: {name}")
                
                output_path = self.generate_section_e_docx(employee_data)
                generated_files.append(output_path)
                
            except Exception as e:
                print(f"❌ Failed to process employee {i}: {e}")
        
        return generated_files


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate Section E resumes using Jinja DOCX templates"
    )
    parser.add_argument("--template", default="templates/JinjaTemplate.docx",
                       help="Path to Jinja DOCX template file")
    parser.add_argument("--data", help="Path to JSON file with employee data")
    parser.add_argument("--employee", help="Generate for specific employee name")
    parser.add_argument("--output", help="Output filename (for single employee)")
    
    args = parser.parse_args()
    
    try:
        generator = JinjaDOCXSectionEGenerator(args.template)
        
        if args.data:
            # Process JSON file
            generated_files = generator.process_json_file(args.data)
            print(f"\n🎉 Successfully generated {len(generated_files)} Jinja DOCX files!")
            print("📁 Output directory:", generator.output_dir)
            
        elif args.employee:
            # Generate for specific employee (would need integration with database)
            print("❌ Employee-specific generation not yet implemented")
            print("💡 Use --data flag with JSON file instead")
            
        else:
            print("❌ Please specify --data (JSON file) or --employee (name)")
            print("💡 Example: python3 jinja_docx_generator.py --data ParsedFiles/results.json")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 