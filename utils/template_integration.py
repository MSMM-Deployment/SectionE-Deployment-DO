#!/usr/bin/env python3
"""
Template Integration Script

This script provides integration utilities for working with Section E templates
and connecting parsed data with external systems.

Features:
- Template validation and field mapping
- Data format conversion utilities
- Integration helpers for various output formats
- Batch processing capabilities

Usage:
python template_integration.py [options]

Requirements:
- Section E template files
- Parsed resume data
- Valid environment configuration

Template Integration System for Standard Form 330 Section E

This script takes the parsed JSON data from section_e_parser.py and integrates it
with the HTML template to generate properly formatted Section E documents.

Usage:
python template_integration.py --data ParsedFiles/real_parsed_results.json --template SampleE-converted.html --output OutputFiles
"""

import os
import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup


class SectionETemplateIntegrator:
    """Integrates parsed resume data with HTML template"""
    
    def __init__(self, template_path: str):
        """
        Initialize with HTML template
        
        Args:
            template_path (str): Path to HTML template file
        """
        self.template_path = template_path
        self.template_content = self._load_template()
        
    def _load_template(self) -> str:
        """Load the HTML template content"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to load template: {e}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and format text for HTML insertion"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', str(text).strip())
        
        # Handle special characters
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return text
    
    def _format_project_description(self, project: dict) -> str:
        """Format project description with proper structure"""
        description_parts = []
        
        if project.get('description', {}).get('scope'):
            scope = self._clean_text(project['description']['scope'])
            if scope and scope not in ['', 'Brief scope, size, cost, etc.']:
                description_parts.append(f"<strong>Scope:</strong> {scope}")
        
        cost = project.get('description', {}).get('cost', '')
        fee = project.get('description', {}).get('fee', '')
        role = project.get('description', {}).get('role', '')
        
        if cost:
            description_parts.append(f"<strong>Cost:</strong> {self._clean_text(cost)}")
        if fee:
            description_parts.append(f"<strong>Fee:</strong> {self._clean_text(fee)}")
        if role:
            description_parts.append(f"<strong>Role:</strong> {self._clean_text(role)}")
        
        return "<br/>".join(description_parts)
    
    def _format_projects_table(self, projects: list) -> str:
        """Generate HTML table for projects"""
        if not projects:
            return ""
        
        table_rows = []
        
        for project in projects:
            title = self._clean_text(project.get('title_and_location', ''))
            
            # Format completion years
            year_completed = project.get('year_completed', {})
            prof_services = year_completed.get('professional_services', '')
            construction = year_completed.get('construction', '')
            
            years = []
            if prof_services:
                years.append(f"Prof. Services: {prof_services}")
            if construction:
                years.append(f"Construction: {construction}")
            
            year_text = " | ".join(years) if years else ""
            
            # Format description
            description = self._format_project_description(project)
            
            row = f"""
            <tr>
                <td style="border: 1px solid #000; padding: 4px; vertical-align: top;">
                    <strong>{title}</strong>
                    {f'<br/><em>{year_text}</em>' if year_text else ''}
                </td>
                <td style="border: 1px solid #000; padding: 4px; vertical-align: top;">
                    {description}
                </td>
            </tr>
            """
            table_rows.append(row)
        
        table_html = f"""
        <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="border: 1px solid #000; padding: 6px; width: 40%;">Project Title & Location</th>
                    <th style="border: 1px solid #000; padding: 6px; width: 60%;">Description</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        """
        
        return table_html
    
    def generate_section_e(self, employee_data: dict) -> str:
        """
        Generate Section E HTML for a specific employee
        
        Args:
            employee_data (dict): Employee data from parsed JSON
            
        Returns:
            str: HTML content for the employee's Section E
        """
        # Parse the template with BeautifulSoup for easier manipulation
        soup = BeautifulSoup(self.template_content, 'html.parser')
        
        # Extract employee information
        data = employee_data.get('data', {})
        name = self._clean_text(data.get('name', ''))
        role = self._clean_text(data.get('role_in_contract', ''))
        
        # Experience information
        experience = data.get('years_experience', {})
        total_exp = self._clean_text(experience.get('total', ''))
        current_firm_exp = self._clean_text(experience.get('with_current_firm', ''))
        
        # Other information
        firm_location = self._clean_text(data.get('firm_name_and_location', ''))
        education = self._clean_text(data.get('education', ''))
        registration = self._clean_text(data.get('current_professional_registration', ''))
        qualifications = self._clean_text(data.get('other_professional_qualifications', ''))
        
        # Projects
        projects = data.get('relevant_projects', [])
        projects_html = self._format_projects_table(projects)
        
        # Create the content structure
        content_html = f"""
        <div style="max-width: 800px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">
                STANDARD FORM 330 - SECTION E
            </h1>
            
            <h2 style="color: #2c3e50; margin-top: 30px;">EMPLOYEE INFORMATION</h2>
            
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr>
                    <td style="border: 1px solid #000; padding: 8px; background-color: #f8f9fa; font-weight: bold; width: 200px;">
                        Name:
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        {name}
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 8px; background-color: #f8f9fa; font-weight: bold;">
                        Role in Contract:
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        {role}
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 8px; background-color: #f8f9fa; font-weight: bold;">
                        Years of Experience:
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        Total: {total_exp} years | With Current Firm: {current_firm_exp} years
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 8px; background-color: #f8f9fa; font-weight: bold;">
                        Firm Name & Location:
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        {firm_location}
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 8px; background-color: #f8f9fa; font-weight: bold;">
                        Education:
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        {education}
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 8px; background-color: #f8f9fa; font-weight: bold;">
                        Professional Registration:
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        {registration}
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 8px; background-color: #f8f9fa; font-weight: bold; vertical-align: top;">
                        Other Qualifications:
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        {qualifications}
                    </td>
                </tr>
            </table>
            
            <h2 style="color: #2c3e50; margin-top: 30px;">RELEVANT PROJECTS</h2>
            {projects_html}
            
            <div style="margin-top: 40px; text-align: center; color: #666; font-size: 12px;">
                Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </div>
        </div>
        """
        
        # Create a complete HTML document
        complete_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Section E - {name}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    background-color: #ffffff;
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                }}
                .page-break {{
                    page-break-after: always;
                }}
                @media print {{
                    body {{
                        margin: 0;
                        padding: 15px;
                    }}
                    .page-break {{
                        page-break-after: always;
                    }}
                }}
            </style>
        </head>
        <body>
            {content_html}
        </body>
        </html>
        """
        
        return complete_html
    
    def process_all_employees(self, parsed_data: dict, output_dir: str) -> dict:
        """
        Process all employees and generate individual Section E documents
        
        Args:
            parsed_data (dict): Complete parsed data from JSON file
            output_dir (str): Output directory for generated files
            
        Returns:
            dict: Processing results summary
        """
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        results = {
            "processed_count": 0,
            "successful": [],
            "failed": [],
            "output_directory": str(output_path),
            "generated_at": datetime.now().isoformat()
        }
        
        resumes = parsed_data.get('resumes', [])
        
        for employee_data in resumes:
            try:
                filename = employee_data.get('filename', 'unknown')
                
                # Generate Section E content
                section_e_html = self.generate_section_e(employee_data)
                
                # Create output filename
                data = employee_data.get('data', {})
                name = data.get('name', '').strip()
                
                # Clean name for filename
                clean_name = re.sub(r'[^a-zA-Z0-9\s\-]', '', name)
                clean_name = re.sub(r'\s+', '_', clean_name)
                
                if not clean_name:
                    clean_name = Path(filename).stem
                
                output_filename = f"SectionE_{clean_name}.html"
                output_file_path = output_path / output_filename
                
                # Write the HTML file
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(section_e_html)
                
                results["successful"].append({
                    "source_file": filename,
                    "employee_name": name,
                    "output_file": str(output_file_path),
                    "size_bytes": len(section_e_html)
                })
                
                results["processed_count"] += 1
                print(f"✓ Generated Section E for {name} -> {output_filename}")
                
            except Exception as e:
                error_info = {
                    "source_file": employee_data.get('filename', 'unknown'),
                    "error": str(e)
                }
                results["failed"].append(error_info)
                print(f"✗ Failed to process {error_info['source_file']}: {e}")
        
        return results


def main():
    """Main function to integrate templates with parsed data"""
    parser = argparse.ArgumentParser(
        description="Integrate parsed Section E data with HTML template"
    )
    parser.add_argument("--data", required=True, help="Path to parsed JSON data file")
    parser.add_argument("--template", required=True, help="Path to HTML template file")
    parser.add_argument("--output", required=True, help="Output directory for generated files")
    args = parser.parse_args()
    
    try:
        # Load parsed data
        print(f"Loading parsed data from {args.data}...")
        with open(args.data, 'r', encoding='utf-8') as f:
            parsed_data = json.load(f)
        
        # Initialize template integrator
        print(f"Loading template from {args.template}...")
        integrator = SectionETemplateIntegrator(args.template)
        
        # Process all employees
        print(f"Generating Section E documents to {args.output}...")
        results = integrator.process_all_employees(parsed_data, args.output)
        
        # Save processing results
        results_file = Path(args.output) / "processing_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total employees processed: {results['processed_count']}")
        print(f"Successful: {len(results['successful'])}")
        print(f"Failed: {len(results['failed'])}")
        print(f"Output directory: {results['output_directory']}")
        print(f"Results saved to: {results_file}")
        
        if results['failed']:
            print(f"\nFailed files:")
            for failed in results['failed']:
                print(f"  - {failed['source_file']}: {failed['error']}")
        
        if results['successful']:
            print(f"\nGenerated files:")
            for success in results['successful']:
                print(f"  - {success['output_file']} ({success['employee_name']})")
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 