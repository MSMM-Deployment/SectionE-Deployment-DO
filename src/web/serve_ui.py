#!/usr/bin/env python3
"""
Simple Python web server for Section E Resume Database UI
Reads environment variables from .env and serves the HTML with credentials injected
"""

import os
import sys
import re
import http.server
import socketserver
import webbrowser
from urllib.parse import urlparse
from dotenv import load_dotenv
import uuid
from datetime import datetime
import warnings

# Suppress the pkg_resources deprecation warning that might cause issues
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")

# Add project root to Python path for src module imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Import template downloader
from utils.supabase_template_downloader import SupabaseTemplateDownloader

class UIHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that injects environment variables into HTML"""
    
    def __init__(self, *args, **kwargs):
        # Initialize template downloader
        self.template_downloader = SupabaseTemplateDownloader()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            self.serve_html_with_env()
        elif self.path == '/login.html':
            self.serve_login_page()
        elif self.path == '/signup.html':
            self.serve_signup_page()
        elif self.path == '/api/config':
            self.serve_config_api()
        elif self.path == '/api/employees':
            self.serve_employees_api()
        elif self.path == '/api/all-projects':
            self.serve_all_projects_api()
        elif self.path.startswith('/api/employee/'):
            employee_name = self.path.split('/api/employee/')[1]
            self.serve_employee_detail_api(employee_name)
        elif self.path.startswith('/api/generate-pdf/'):
            employee_name = self.path.split('/api/generate-pdf/')[1]
            self.serve_pdf_generation_api(employee_name)
        elif self.path == '/api/templates':
            self.serve_templates_api()
        elif self.path.startswith('/api/template-preview/'):
            template_id = self.path.split('/api/template-preview/')[1]
            self.serve_template_preview_api(template_id)
        elif self.path.startswith('/api/employee-qualifications/'):
            employee_id = self.path.split('/api/employee-qualifications/')[1]
            self.serve_employee_qualifications_api(employee_id)
        elif self.path == '/api/employees-for-merge':
            self.serve_employees_for_merge_api()
        elif self.path == '/api/potential-duplicates':
            self.serve_potential_duplicates_api()
        elif self.path.startswith('/api/merge-preview/'):
            # Expects format: /api/merge-preview/primary_id/secondary_id
            path_parts = self.path.split('/api/merge-preview/')[1].split('/')
            if len(path_parts) == 2:
                self.serve_merge_preview_api(path_parts[0], path_parts[1])
            else:
                self.send_error(400, "Invalid merge preview URL format")
        elif self.path == '/api/teams-for-merge':
            self.serve_teams_for_merge_api()
        elif self.path == '/api/potential-duplicate-teams':
            self.serve_potential_duplicate_teams_api()
        elif self.path.startswith('/api/team-merge-preview/'):
            # Expects format: /api/team-merge-preview/primary_id/secondary_id
            path_parts = self.path.split('/api/team-merge-preview/')[1].split('/')
            if len(path_parts) == 2:
                self.serve_team_merge_preview_api(path_parts[0], path_parts[1])
            else:
                self.send_error(400, "Invalid team merge preview URL format")
        elif self.path == '/api/roles-for-merge':
            self.serve_roles_for_merge_api()
        elif self.path == '/api/potential-duplicate-roles':
            self.serve_potential_duplicate_roles_api()
        elif self.path.startswith('/api/role-merge-preview/'):
            # Expects format: /api/role-merge-preview/primary_role/secondary_role (URL encoded)
            path_parts = self.path.split('/api/role-merge-preview/')[1].split('/')
            if len(path_parts) == 2:
                from urllib.parse import unquote
                primary_role = unquote(path_parts[0])
                secondary_role = unquote(path_parts[1])
                self.serve_role_merge_preview_api(primary_role, secondary_role)
            else:
                self.send_error(400, "Invalid role merge preview URL format")
        elif self.path.startswith('/api/delete-employee-preview/'):
            # Expects format: /api/delete-employee-preview/employee_id
            employee_id = self.path.split('/api/delete-employee-preview/')[1]
            self.serve_delete_employee_preview_api(employee_id)
        elif self.path == '/health':
            self.serve_health_check()
        else:
            # Serve static files normally
            super().do_GET()

    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/generate-custom-pdf':
            self.serve_custom_pdf_generation_api()
        elif self.path == '/api/generate-custom-pdf-with-template':
            self.serve_custom_pdf_with_template_api()
        elif self.path == '/api/generate-custom-docx-with-template':
            self.serve_custom_docx_with_template_api()
        elif self.path == '/api/analyze-solicitation':
            self.serve_solicitation_analysis_api()
        elif self.path == '/api/set-primary-qualification':
            self.serve_set_primary_qualification_api()
        elif self.path == '/api/merge-employees':
            self.serve_merge_employees_api()
        elif self.path == '/api/merge-teams':
            self.serve_merge_teams_api()
        elif self.path == '/api/merge-roles':
            self.serve_merge_roles_api()
        elif self.path == '/api/split-compound-roles':
            self.serve_split_compound_roles_api()
        elif self.path == '/api/normalize-roles':
            self.serve_normalize_roles_api()
        elif self.path == '/api/execute-split-roles':
            self.serve_execute_split_roles_api()
        elif self.path == '/api/delete-employee':
            self.serve_delete_employee_api()
        elif self.path == '/api/delete-project':
            self.serve_delete_project_api()
        elif self.path == '/api/trigger-processing':
            self.serve_trigger_processing_api()
        elif self.path == '/api/upload-template':
            self.serve_upload_template_api()
        elif self.path == '/api/ai-rewrite':
            self.serve_ai_rewrite_api()
        else:
            self.send_error(404, "Not Found")
    
    def serve_html_with_env(self):
        """
        Serve index.html with environment variables injected
        
        This method dynamically injects Supabase credentials from .env file
        into the HTML template, allowing the frontend to connect to the database
        without exposing credentials in the source code.
        """
        try:
            # Read the HTML file from disk
            # Use path relative to current working directory (project root)
            html_file_path = os.path.join(os.path.dirname(__file__), 'index.html')
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Get environment variables from .env file
            # Use fallback values if not found (for demo/development mode)
            supabase_url = os.getenv('SUPABASE_URL', 'YOUR_SUPABASE_URL_HERE')
            supabase_key = os.getenv('SUPABASE_KEY', 'YOUR_SUPABASE_ANON_KEY_HERE')
            
            # Replace placeholder values in HTML with actual credentials
            # This allows the frontend JavaScript to connect to Supabase
            html_content = html_content.replace(
                "const SUPABASE_URL = 'YOUR_SUPABASE_URL_HERE';",
                f"const SUPABASE_URL = '{supabase_url}';"
            )
            
            html_content = html_content.replace(
                "const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY_HERE';",
                f"const SUPABASE_ANON_KEY = '{supabase_key}';"
            )
            
            # Update the configuration message to show actual values
            html_content = html_content.replace(
                "SUPABASE_URL = 'your_supabase_project_url'<br>",
                f"SUPABASE_URL = '{supabase_url}'<br>"
            )
            
            html_content = html_content.replace(
                "SUPABASE_ANON_KEY = 'your_supabase_anon_key'",
                f"SUPABASE_ANON_KEY = '{supabase_key}'"
            )
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
            # Log the status
            if supabase_url != 'YOUR_SUPABASE_URL_HERE' and supabase_key != 'YOUR_SUPABASE_ANON_KEY_HERE':
                print('✅ Environment variables loaded successfully')
                print(f'📊 Supabase URL: {supabase_url}')
                print(f'🔑 Supabase Key: {supabase_key[:20]}...')
            else:
                print('⚠️  Environment variables not found - showing demo mode')
            
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
        except Exception as e:
            print(f"Error serving HTML: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def serve_login_page(self):
        """Serve the login page"""
        try:
            # Read the login HTML file
            login_file_path = os.path.join(os.path.dirname(__file__), 'login.html')
            with open(login_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except FileNotFoundError:
            self.send_error(404, "login.html not found")
        except Exception as e:
            print(f"Error serving login page: {e}")
            self.send_error(500, "Internal Server Error")
    
    def serve_signup_page(self):
        """Serve the signup page"""
        try:
            # Read the signup HTML file
            signup_file_path = os.path.join(os.path.dirname(__file__), 'signup.html')
            with open(signup_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except FileNotFoundError:
            self.send_error(404, "signup.html not found")
        except Exception as e:
            print(f"Error serving signup page: {e}")
            self.send_error(500, "Internal Server Error")
    
    def serve_config_api(self):
        """Serve configuration API endpoint"""
        config = {
            "supabaseConfigured": bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_KEY')),
            "hasUrl": bool(os.getenv('SUPABASE_URL')),
            "hasKey": bool(os.getenv('SUPABASE_KEY'))
        }
        
        response = str(config).replace("'", '"').replace('True', 'true').replace('False', 'false')
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def deduplicate_role_string(self, role_string):
        """
        Clean and deduplicate a comma-separated role string
        
        Args:
            role_string: String like "Civil Engineer, Civil Engineer, Data Engineer"
            
        Returns:
            Cleaned string like "Civil Engineer, Data Engineer"
        """
        if not role_string:
            return role_string
            
        # Split by comma, clean each role, and deduplicate
        roles = []
        for role in role_string.split(','):
            cleaned_role = role.strip()
            if cleaned_role and cleaned_role not in roles:
                roles.append(cleaned_role)
        
        return ', '.join(roles)

    def serve_employees_api(self):
        """
        Serve employees list API endpoint
        
        This endpoint serves the list of all employees from the parsed results JSON file.
        It transforms the raw parser output into a format suitable for the frontend table.
        Used by: Employee list page, search functionality
        """
        try:
            import json
            from urllib.parse import unquote
            
            # Load parsed results from the JSON file created by section_e_parser.py
            with open('data/ParsedFiles/real_parsed_results.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Transform raw parser data into frontend-friendly format
            # Each resume becomes an employee record with flattened structure
            employees = []
            for resume in data.get('resumes', []):
                employee_data = resume.get('data', {})
                
                # Skip resumes without names (parsing errors)
                if employee_data.get('name'):
                    # Create flattened employee object for table display
                    raw_role = employee_data.get('role_in_contract', '')
                    cleaned_role = self.deduplicate_role_string(raw_role)
                    
                    employees.append({
                        'employee_name': employee_data.get('name'),
                        'role_in_contract': cleaned_role,
                        'total_years_experience': employee_data.get('years_experience', {}).get('total'),
                        'firm_name': employee_data.get('firm_name_and_location'),
                        'education': employee_data.get('education'),
                        'professional_qualifications': employee_data.get('current_professional_registration'),
                        'other_professional_qualifications': employee_data.get('other_professional_qualifications'),
                        'filename': resume.get('filename'),
                        'processed_at': resume.get('processed_at')
                    })
            
            response = json.dumps(employees, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error serving employees API: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_employee_detail_api(self, employee_name):
        """Serve individual employee detail API endpoint"""
        try:
            import json
            from urllib.parse import unquote
            
            # Decode URL-encoded name
            employee_name = unquote(employee_name)
            
            # Load parsed results
            # Use path relative to project root
            json_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ParsedFiles', 'real_parsed_results.json')
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Find employee data
            employee_detail = None
            for resume in data.get('resumes', []):
                employee_data = resume.get('data', {})
                if employee_data.get('name') == employee_name:
                    employee_detail = {
                        'employee_name': employee_data.get('name'),
                        'role_in_contract': employee_data.get('role_in_contract'),
                        'total_years_experience': employee_data.get('years_experience', {}).get('total'),
                        'years_with_current_firm': employee_data.get('years_experience', {}).get('with_current_firm'),
                        'firm_name': employee_data.get('firm_name_and_location'),
                        'education': employee_data.get('education'),
                        'professional_qualifications': employee_data.get('current_professional_registration'),
                        'other_professional_qualifications': employee_data.get('other_professional_qualifications'),
                        'relevant_projects': employee_data.get('relevant_projects', []),
                        'filename': resume.get('filename'),
                        'processed_at': resume.get('processed_at')
                    }
                    break
            
            if employee_detail:
                response = json.dumps(employee_detail, indent=2)
                self.send_response(200)
            else:
                response = json.dumps({"error": "Employee not found"})
                self.send_response(404)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error serving employee detail API: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_all_projects_api(self):
        """Serve all projects across all employees from Supabase database"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                # Fallback to local data if Supabase not configured
                try:
                    # Load parsed results from local JSON file
                    json_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ParsedFiles', 'real_parsed_results.json')
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    all_projects = []
                    for resume in data.get('resumes', []):
                        employee_data = resume.get('data', {})
                        employee_name = employee_data.get('name')
                        
                        if employee_name and employee_data.get('relevant_projects'):
                            for project in employee_data.get('relevant_projects', []):
                                all_projects.append({
                                    'project_id': f"local_{len(all_projects)}",
                                    'title_and_location': project.get('title_and_location', ''),
                                    'description_scope': project.get('description', {}).get('scope', ''),
                                    'employee_name': employee_name,
                                    'employee_id': None,
                                    'source': 'local'
                                })
                    
                    response = json.dumps({'projects': all_projects}, indent=2)
                except Exception as e:
                    print(f"Error loading local data: {e}")
                    response = json.dumps({'projects': []})
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
                return
            
            # Connect to Supabase and get all projects with employee info
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            print("🔍 Fetching all projects from Supabase...")
            
            # First try to get all projects directly
            try:
                project_result = supabase.table('projects').select('project_id, title_and_location, description_scope').execute()
                employee_result = supabase.table('employees').select('employee_id, employee_name').execute()
                assignment_result = supabase.table('employee_assignments').select('employee_id, project_id').execute()
                
                print(f"📊 Found {len(project_result.data) if project_result.data else 0} projects")
                print(f"📊 Found {len(employee_result.data) if employee_result.data else 0} employees")
                print(f"📊 Found {len(assignment_result.data) if assignment_result.data else 0} assignments")
                
                # Build lookup maps
                employees_map = {emp['employee_id']: emp['employee_name'] for emp in employee_result.data or []}
                projects_map = {proj['project_id']: proj for proj in project_result.data or []}
                
                all_projects = []
                for assignment in assignment_result.data or []:
                    employee_id = assignment.get('employee_id')
                    project_id = assignment.get('project_id')
                    
                    if employee_id in employees_map and project_id in projects_map:
                        project = projects_map[project_id]
                        employee_name = employees_map[employee_id]
                        
                        all_projects.append({
                            'project_id': project.get('project_id'),
                            'title_and_location': project.get('title_and_location', ''),
                            'description_scope': project.get('description_scope', ''),
                            'employee_name': employee_name,
                            'employee_id': employee_id,
                            'source': 'database'
                        })
                
                print(f"✅ Processed {len(all_projects)} valid projects")
                response = json.dumps({'projects': all_projects}, indent=2)
                
            except Exception as join_error:
                print(f"⚠️ Join query failed, trying simpler approach: {join_error}")
                # Fallback to simple query without joins
                result = supabase.table('employee_assignments').select('*').execute()
            
                print(f"📊 Fallback query result: {len(result.data) if result.data else 0} assignments found")
                
                if result.data:
                    # This is the fallback case - we have assignment data but need to fetch projects/employees separately
                    response = json.dumps({'projects': []})  # For now, return empty for fallback
                else:
                    response = json.dumps({'projects': []})
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error serving all projects API: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_custom_pdf_generation_api(self):
        """Generate and serve PDF from customized resume data received via POST"""
        try:
            import json
            
            # Read the POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            resume_data = json.loads(post_data.decode('utf-8'))
            
            print(f"🔄 Generating custom PDF with {len(resume_data.get('projects', []))} projects")
            
            # Transform frontend resume data to backend format
            employee_data = self.transform_resume_data(resume_data)
            
            # Try to generate PDF with custom data
            try:
                from src.generators.pdf_form_filler import SectionEPDFGenerator
                
                generator = SectionEPDFGenerator()
                pdf_path = generator.create_section_e_pdf(employee_data)
                
                if pdf_path and os.path.exists(pdf_path):
                    # Read the PDF file
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_content = pdf_file.read()
                    
                    # Send PDF response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Disposition', f'attachment; filename="SectionE_{employee_data.get("name", "Unknown").replace(" ", "_")}.pdf"')
                    self.send_header('Content-Length', str(len(pdf_content)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(pdf_content)
                    
                    print(f"✅ Custom PDF served successfully")
                    return
                else:
                    raise Exception("Failed to generate PDF")
                        
            except ImportError:
                print("⚠️ PDF generator dependencies not installed")
                raise Exception("PDF generation dependencies not available")
            except Exception as e:
                print(f"⚠️ PDF generation failed: {e}")
                print("Falling back to simple PDF generation...")
                
                # Fallback: Generate simple PDF
                self.generate_custom_fallback_pdf(employee_data)
                return
                
        except Exception as e:
            print(f"Error generating custom PDF: {e}")
            import json
            error_response = json.dumps({"error": str(e), "message": "Custom PDF generation failed"})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def transform_resume_data(self, resume_data):
        """Transform frontend resume data format to backend format"""
        personal_info = resume_data.get('personalInfo', {})
        projects = resume_data.get('projects', [])
        
        # Transform projects to the expected backend format
        relevant_projects = []
        for project in projects:
            if project.get('title', '').strip():  # Only include projects with titles
                project_data = {
                    'title_and_location': project.get('title', ''),
                    'year_completed': {
                        'professional_services': project.get('professionalServicesYear', '') or project.get('year', ''),
                        'construction': project.get('constructionYear', '') or project.get('year', '')
                    },
                    'description': {
                        'scope': project.get('description', ''),
                        'role': project.get('role', ''),
                        'cost': '',
                        'fee': ''
                    },
                    'performed_with_same_firm': project.get('performedWithSameFirm', False)
                }
                relevant_projects.append(project_data)
                print(f"🔍 Backend transforming project: {project.get('title', '')} - Professional: {project.get('professionalServicesYear', '')} - Construction: {project.get('constructionYear', '')} - Checkbox: {project.get('performedWithSameFirm', False)}")
        
        return {
            'name': personal_info.get('name', ''),
            'role_in_contract': personal_info.get('roleInContract', ''),
            'years_experience': {
                'total': personal_info.get('totalExperience', ''),
                'with_current_firm': personal_info.get('totalExperience', '')  # Use same value as fallback
            },
            'firm_name_and_location': f"{personal_info.get('firmName', '')}, {personal_info.get('location', '')}",
            'education': resume_data.get('education', ''),
            'current_professional_registration': resume_data.get('registration', ''),
            'other_professional_qualifications': resume_data.get('qualifications', ''),
            'relevant_projects': relevant_projects
        }
    
    def generate_custom_fallback_pdf(self, employee_data):
        """Generate a simple PDF when template filling fails with custom data"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io
            
            # Create PDF in memory
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            # Title
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, height - 50, "STANDARD FORM 330 - SECTION E")
            
            # Employee information
            y_position = height - 100
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "EMPLOYEE INFORMATION")
            
            y_position -= 30
            p.setFont("Helvetica", 10)
            
            fields = [
                ("Name:", employee_data.get('name', '')),
                ("Role in Contract:", employee_data.get('role_in_contract', '')),
                ("Total Experience:", employee_data.get('years_experience', {}).get('total', '')),
                ("Current Firm Experience:", employee_data.get('years_experience', {}).get('with_current_firm', '')),
                ("Firm:", employee_data.get('firm_name_and_location', '')),
                ("Education:", employee_data.get('education', '')),
                ("Registration:", employee_data.get('current_professional_registration', '')),
                ("Other Qualifications:", employee_data.get('other_professional_qualifications', ''))
            ]
            
            for label, value in fields:
                if y_position < 100:  # Start new page if needed
                    p.showPage()
                    y_position = height - 50
                
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y_position, label)
                p.setFont("Helvetica", 10)
                p.drawString(200, y_position, str(value)[:80])  # Truncate long text
                y_position -= 20
            
            # Projects section - use the FILTERED projects from frontend
            projects = employee_data.get('relevant_projects', [])
            if projects:
                y_position -= 20
                if y_position < 100:
                    p.showPage()
                    y_position = height - 50
                
                p.setFont("Helvetica-Bold", 12)
                p.drawString(50, y_position, f"RELEVANT PROJECTS ({len(projects)} selected)")
                y_position -= 30
                
                for i, project in enumerate(projects, 1):
                    if y_position < 150:
                        p.showPage()
                        y_position = height - 50
                    
                    p.setFont("Helvetica-Bold", 10)
                    p.drawString(50, y_position, f"Project {i}:")
                    y_position -= 15
                    
                    p.setFont("Helvetica", 9)
                    title = project.get('title_and_location', '')
                    p.drawString(70, y_position, f"Title: {title[:60]}")
                    y_position -= 15
                    
                    year_info = project.get('year_completed', {})
                    if year_info:
                        prof_year = year_info.get('professional_services', '')
                        year_text = f"Year: {prof_year}"
                        p.drawString(70, y_position, year_text)
                        y_position -= 15
                    
                    description = project.get('description', {})
                    if description.get('scope'):
                        desc_text = description['scope'][:100] + ('...' if len(description['scope']) > 100 else '')
                        p.drawString(70, y_position, f"Description: {desc_text}")
                        y_position -= 15
                    
                    if description.get('role'):
                        p.drawString(70, y_position, f"Role: {description['role'][:60]}")
                        y_position -= 15
                    
                    # Add checkbox information
                    performed_with_same_firm = project.get('performed_with_same_firm', False)
                    checkbox_symbol = "☑" if performed_with_same_firm else "☐"
                    p.drawString(70, y_position, f"{checkbox_symbol} Performed with same firm")
                    y_position -= 15
                    
                    y_position -= 10
            
            p.save()
            
            # Get PDF content
            pdf_content = buffer.getvalue()
            buffer.close()
            
            # Send PDF response
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="SectionE_{employee_data.get("name", "Unknown").replace(" ", "_")}.pdf"')
            self.send_header('Content-Length', str(len(pdf_content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(pdf_content)
            
            print(f"✅ Custom fallback PDF generated successfully")
            
        except Exception as e:
            print(f"Error in custom fallback PDF generation: {e}")
            import json
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_solicitation_analysis_api(self):
        """Analyze uploaded solicitation PDF and extract keywords for project matching"""
        try:
            import json
            import tempfile
            import os
            import re
            from src.parsers.enhanced_text_extractor import EnhancedTextExtractor
            from openai import OpenAI
            
            # Check for OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise Exception("OpenAI API key not configured. Please set OPENAI_API_KEY in .env file.")
            
            # Parse multipart form data manually (since cgi module is deprecated)
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                raise Exception("Expected multipart/form-data")
            
            # Extract boundary from content type
            boundary_match = re.search(r'boundary=([^;]+)', content_type)
            if not boundary_match:
                raise Exception("No boundary found in multipart data")
            
            boundary = boundary_match.group(1).strip('"')
            
            # Read the multipart data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                raise Exception("No file data received")
            
            multipart_data = self.rfile.read(content_length)
            
            # Parse multipart data to extract file
            boundary_bytes = f'--{boundary}'.encode()
            parts = multipart_data.split(boundary_bytes)
            
            file_data = None
            filename = None
            
            for part in parts:
                if b'Content-Disposition: form-data' in part and b'filename=' in part:
                    # Extract filename
                    header_end = part.find(b'\r\n\r\n')
                    if header_end == -1:
                        continue
                    
                    headers = part[:header_end].decode('utf-8', errors='ignore')
                    filename_match = re.search(r'filename="([^"]*)"', headers)
                    if filename_match:
                        filename = filename_match.group(1)
                    
                    # Extract file data (after double CRLF)
                    file_data = part[header_end + 4:]
                    # Remove trailing CRLF if present
                    if file_data.endswith(b'\r\n'):
                        file_data = file_data[:-2]
                    break
            
            if not file_data or not filename:
                raise Exception("No PDF file found in upload")
            
            # Validate file type
            if not filename.lower().endswith('.pdf'):
                raise Exception("Only PDF files are supported")
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
            
            try:
                # Extract text from PDF
                print(f"🔍 Analyzing solicitation PDF: {filename}")
                extractor = EnhancedTextExtractor()
                text, method_used = extractor.extract_text_with_fallback(temp_file_path)
                
                if not text:
                    raise Exception("Failed to extract text from PDF")
                
                print(f"✓ Extracted {len(text)} characters using {method_used}")
                
                # Handle large documents by chunking text
                max_chars = 50000  # Conservative limit (~12-15K tokens)
                if len(text) > max_chars:
                    print(f"⚠️ Large document detected ({len(text)} chars). Chunking for analysis...")
                    # Take the first portion and try to find a good break point
                    chunk = text[:max_chars]
                    # Try to break at a paragraph or sentence
                    last_paragraph = chunk.rfind('\n\n')
                    last_sentence = chunk.rfind('. ')
                    if last_paragraph > max_chars * 0.8:  # If paragraph break is in last 20%
                        text = chunk[:last_paragraph]
                    elif last_sentence > max_chars * 0.8:  # If sentence break is in last 20%
                        text = chunk[:last_sentence + 1]
                    else:
                        text = chunk  # Use full chunk if no good break point
                    print(f"✓ Using first {len(text)} characters for analysis")
                
                # Analyze with OpenAI to extract keywords
                client = OpenAI(api_key=api_key)
                
                analysis_prompt = """
                You are an expert at analyzing government solicitation documents for construction and engineering projects.
                
                Extract key information from this solicitation document and return it as a JSON object with the following structure:
                
                {
                  "keywords": [
                    {
                      "category": "location",
                      "text": "specific location or geographic area"
                    },
                    {
                      "category": "role", 
                      "text": "specific role or position required"
                    },
                    {
                      "category": "technology",
                      "text": "specific technology, software, or methodology"
                    },
                    {
                      "category": "industry",
                      "text": "industry sector or type of work"
                    },
                    {
                      "category": "skill",
                      "text": "specific skill or expertise required"
                    },
                    {
                      "category": "certification",
                      "text": "certification or license requirement"
                    }
                  ]
                }
                
                Focus on extracting:
                - Project locations (cities, states, regions)
                - Required roles/positions (Engineer, Project Manager, etc.)
                - Technical skills and technologies
                - Industry types (transportation, water, environmental, etc.)
                - Required certifications or licenses
                - Specific methodologies or approaches
                
                Extract 10-15 of the most relevant keywords that would be useful for matching against project descriptions.
                Each keyword should be specific and actionable for project matching.
                
                Return only the JSON object, no additional text.
                """
                
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": analysis_prompt},
                        {"role": "user", "content": text}
                    ],
                    temperature=0,
                    max_tokens=1500  # Reduced to leave more room for input tokens
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise Exception("Empty response from OpenAI")
                
                # Parse the JSON response
                analysis_result = json.loads(content)
                
                # Validate the response structure
                if 'keywords' not in analysis_result:
                    raise Exception("Invalid response format from AI analysis")
                
                keywords = analysis_result['keywords']
                if not isinstance(keywords, list) or len(keywords) == 0:
                    raise Exception("No keywords extracted from document")
                
                print(f"✓ Extracted {len(keywords)} keywords from solicitation")
                
                # Return the analysis result
                result = {
                    "success": True,
                    "filename": filename,
                    "text_length": len(text),
                    "extraction_method": method_used,
                    "keywords": keywords
                }
                
                response_json = json.dumps(result, indent=2)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_json.encode('utf-8'))
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            error_response = json.dumps({
                "error": "Failed to parse AI response", 
                "details": str(e)
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error analyzing solicitation: {e}")
            
            # Provide specific error messages for common issues
            error_message = str(e)
            if "rate_limit_exceeded" in error_message or "Request too large" in error_message:
                error_response = json.dumps({
                    "error": "Document too large for analysis", 
                    "message": "The uploaded PDF is too large. Please try with a smaller document (under 50 pages) or a more focused solicitation section.",
                    "suggestion": "Consider uploading just the technical requirements or scope of work sections."
                })
            elif "Invalid API key" in error_message or "Incorrect API key" in error_message:
                error_response = json.dumps({
                    "error": "OpenAI API configuration issue", 
                    "message": "Please check your OpenAI API key configuration in the .env file."
                })
            else:
                error_response = json.dumps({
                    "error": str(e), 
                    "message": "Solicitation analysis failed"
                })
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_pdf_generation_api(self, employee_name):
        """Generate and serve PDF for an employee"""
        try:
            import json
            from urllib.parse import unquote
            
            # Decode URL-encoded name
            employee_name = unquote(employee_name)
            
            # Try to import and use the PDF generator
            try:
                from src.generators.pdf_form_filler import SectionEPDFGenerator
                
                # Use the updated SectionEPDFGenerator (it handles both Supabase and JSON fallback internally)
                generator = SectionEPDFGenerator()
                pdf_path = generator.generate_resume_by_name(employee_name)
                
                if pdf_path and os.path.exists(pdf_path):
                    # Read the PDF file
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_content = pdf_file.read()
                    
                    # Send PDF response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Disposition', f'attachment; filename="SectionE_{employee_name.replace(" ", "_")}.pdf"')
                    self.send_header('Content-Length', str(len(pdf_content)))
                    self.end_headers()
                    self.wfile.write(pdf_content)
                    
                    print(f"✅ PDF served successfully for: {employee_name}")
                    return
                else:
                    raise Exception("Failed to generate PDF")
                        
            except ImportError:
                print("⚠️ PDF generator dependencies not installed")
                raise Exception("PDF generation dependencies not available")
            except Exception as e:
                print(f"⚠️ Database PDF generation failed: {e}")
                print("Falling back to JSON-based PDF generation...")
                
                # Fallback: Use JSON file for PDF generation
                self.generate_pdf_from_json(employee_name)
                return
                
        except Exception as e:
            print(f"Error generating PDF: {e}")
            error_response = json.dumps({"error": str(e), "message": "PDF generation failed"})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def generate_pdf_from_json(self, employee_name):
        """Generate PDF from JSON data as fallback"""
        try:
            import json
            from urllib.parse import unquote
            
            # Load parsed results
            # Use path relative to project root
            json_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ParsedFiles', 'real_parsed_results.json')
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Find employee data
            employee_data = None
            for resume in data.get('resumes', []):
                resume_data = resume.get('data', {})
                if resume_data.get('name') == employee_name:
                    employee_data = resume_data
                    break
            
            if not employee_data:
                raise Exception(f"Employee '{employee_name}' not found in parsed data")
            
            # Try to use reportlab to create a simple PDF
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                import io
                
                # Create PDF in memory
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                
                # Title
                p.setFont("Helvetica-Bold", 16)
                p.drawString(50, height - 50, "STANDARD FORM 330 - SECTION E")
                
                # Employee information
                y_position = height - 100
                p.setFont("Helvetica-Bold", 12)
                p.drawString(50, y_position, "EMPLOYEE INFORMATION")
                
                y_position -= 30
                p.setFont("Helvetica", 10)
                
                fields = [
                    ("Name:", employee_data.get('name', '')),
                    ("Role in Contract:", employee_data.get('role_in_contract', '')),
                    ("Total Experience:", employee_data.get('years_experience', {}).get('total', '')),
                    ("Current Firm Experience:", employee_data.get('years_experience', {}).get('with_current_firm', '')),
                    ("Firm:", employee_data.get('firm_name_and_location', '')),
                    ("Education:", employee_data.get('education', '')),
                    ("Registration:", employee_data.get('current_professional_registration', '')),
                    ("Other Qualifications:", employee_data.get('other_professional_qualifications', ''))
                ]
                
                for label, value in fields:
                    if y_position < 100:  # Start new page if needed
                        p.showPage()
                        y_position = height - 50
                    
                    p.setFont("Helvetica-Bold", 10)
                    p.drawString(50, y_position, label)
                    p.setFont("Helvetica", 10)
                    p.drawString(200, y_position, str(value)[:80])  # Truncate long text
                    y_position -= 20
                
                # Projects section
                projects = employee_data.get('relevant_projects', [])
                if projects:
                    y_position -= 20
                    if y_position < 100:
                        p.showPage()
                        y_position = height - 50
                    
                    p.setFont("Helvetica-Bold", 12)
                    p.drawString(50, y_position, "RELEVANT PROJECTS")
                    y_position -= 30
                    
                    for i, project in enumerate(projects[:5], 1):
                        if y_position < 150:
                            p.showPage()
                            y_position = height - 50
                        
                        p.setFont("Helvetica-Bold", 10)
                        p.drawString(50, y_position, f"Project {i}:")
                        y_position -= 15
                        
                        p.setFont("Helvetica", 9)
                        title = project.get('title_and_location', '')
                        p.drawString(70, y_position, f"Title: {title[:60]}")
                        y_position -= 15
                        
                        year_info = project.get('year_completed', {})
                        if year_info:
                            prof_year = year_info.get('professional_services', '')
                            const_year = year_info.get('construction', '')
                            year_text = f"Prof: {prof_year}, Const: {const_year}"
                            p.drawString(70, y_position, f"Years: {year_text}")
                            y_position -= 15
                        
                        y_position -= 10
                
                p.save()
                
                # Get PDF content
                pdf_content = buffer.getvalue()
                buffer.close()
                
                # Send PDF response
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', f'attachment; filename="SectionE_{employee_name.replace(" ", "_")}.pdf"')
                self.send_header('Content-Length', str(len(pdf_content)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(pdf_content)
                
                print(f"✅ Fallback PDF generated successfully for: {employee_name}")
                
            except ImportError:
                # If reportlab is not available, return a simple text response
                response_text = f"PDF generation not available. Employee data for {employee_name} found but PDF libraries not installed."
                self.send_response(503)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_text.encode('utf-8'))
                
        except Exception as e:
            print(f"Error in fallback PDF generation: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_templates_api(self):
        """Serve available templates list API endpoint"""
        try:
            import json
            
            # Load templates metadata
            templates_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'templates.json')
            with open(templates_file_path, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            response = json.dumps(templates_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error serving templates API: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_template_preview_api(self, template_id):
        """Serve template preview (first page as image)"""
        try:
            import json
            from urllib.parse import unquote
            
            # Decode URL-encoded template ID
            template_id = unquote(template_id)
            
            # Load templates metadata to find the file
            templates_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'templates.json')
            with open(templates_file_path, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            template_info = None
            for template in templates_data['templates']:
                if template['id'] == template_id:
                    template_info = template
                    break
            
            if not template_info:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = json.dumps({"error": "Template not found"})
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Try to generate preview using pdf2image
            try:
                from pdf2image import convert_from_path
                import io
                
                # Get template path (local or download from Supabase)
                template_path = self.template_downloader.get_template_path(template_info['filename'])
                if not template_path:
                    raise Exception(f"Template not found: {template_info['filename']}")
                
                # Convert first page to image
                images = convert_from_path(template_path, first_page=1, last_page=1, dpi=150)
                
                if images:
                    # Convert to PNG bytes
                    img_buffer = io.BytesIO()
                    images[0].save(img_buffer, format='PNG')
                    img_bytes = img_buffer.getvalue()
                    
                    # Send image response
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Content-Length', str(len(img_bytes)))
                    self.end_headers()
                    self.wfile.write(img_bytes)
                    return
                
            except ImportError:
                # pdf2image not available, return placeholder
                pass
            except Exception as e:
                print(f"Error generating preview: {e}")
            
            # Fallback: return template info as JSON
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({
                "template": template_info,
                "preview_available": False,
                "message": "Preview generation not available - install pdf2image for previews"
            }, indent=2)
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error serving template preview: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_custom_pdf_with_template_api(self):
        """Generate custom PDF with selected template"""
        try:
            import json
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            request_data = json.loads(post_data)
            
            # Extract template selection and employee data
            template_id = request_data.get('templateId', 'default')
            employee_data = self.transform_resume_data(request_data)
            
            # Load template metadata
            templates_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'templates.json')
            with open(templates_file_path, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            # Find selected template
            template_info = None
            for template in templates_data['templates']:
                if template['id'] == template_id:
                    template_info = template
                    break
            
            if not template_info:
                # Default to first template if not found
                template_info = templates_data['templates'][0]
            
            # Get template path (local or download from Supabase)
            template_path = self.template_downloader.get_template_path(template_info['filename'])
            if not template_path:
                raise Exception(f"Template not found: {template_info['filename']}")
            
            # Check if it's a DOCX template (either traditional or Jinja)
            if template_info.get('type') in ['docx', 'jinja_docx']:
                # Use DOCX generator
                self.generate_docx_with_template(employee_data, template_info)
                return
            
            # Try to generate PDF with selected template
            try:
                from src.generators.pdf_form_filler import SectionEPDFGenerator
                
                # Create a custom generator with the selected template
                generator = SectionEPDFGenerator()
                generator.template_path = template_path  # Override the template path
                
                pdf_path = generator.create_section_e_pdf(employee_data)
                
                if pdf_path and os.path.exists(pdf_path):
                    # Read the PDF file
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_content = pdf_file.read()
                    
                    # Send PDF response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Disposition', f'attachment; filename="SectionE_{employee_data.get("name", "Unknown").replace(" ", "_")}_{template_info["name"].replace(" ", "_")}.pdf"')
                    self.send_header('Content-Length', str(len(pdf_content)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(pdf_content)
                    
                    print(f"✅ Custom PDF with template '{template_info['name']}' served successfully")
                    return
                else:
                    raise Exception("Failed to generate PDF with template")
                        
            except ImportError:
                print("⚠️ PDF generator dependencies not installed")
                raise Exception("PDF generation dependencies not available")
            except Exception as e:
                print(f"⚠️ Template PDF generation failed: {e}")
                print("Falling back to simple PDF generation...")
                
                # Fallback: Generate simple PDF
                self.generate_custom_fallback_pdf(employee_data)
                return
                
        except Exception as e:
            print(f"Error generating PDF with template: {e}")
            import json
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_custom_docx_with_template_api(self):
        """Generate custom DOCX with selected template"""
        try:
            import json
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            request_data = json.loads(post_data)
            
            # Extract template selection and employee data
            template_id = request_data.get('templateId', 'docx_template')
            employee_data = self.transform_resume_data(request_data)
            
            # Load template metadata
            templates_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'templates.json')
            with open(templates_file_path, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            # Find selected template
            template_info = None
            for template in templates_data['templates']:
                if template['id'] == template_id:
                    template_info = template
                    break
            
            # Default to DOCX template if not found
            if not template_info or template_info.get('type') not in ['docx', 'jinja_docx']:
                for template in templates_data['templates']:
                    if template.get('type') in ['docx', 'jinja_docx']:
                        template_info = template
                        break
            
            if not template_info:
                raise Exception("No DOCX template found")
            
            self.generate_docx_with_template(employee_data, template_info)
                
        except Exception as e:
            print(f"Error generating DOCX with template: {e}")
            import json
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def generate_docx_with_template(self, employee_data, template_info):
        """Generate DOCX using the appropriate template generator based on template type"""
        try:
            # Get template path (local or download from Supabase)
            template_path = self.template_downloader.get_template_path(template_info['filename'])
            if not template_path:
                raise Exception(f"Template not found: {template_info['filename']}")
            
            # Check template type and use appropriate generator
            if template_info.get('type') == 'jinja_docx':
                # Use Jinja DOCX generator for templates with {{ variable }} syntax
                from src.generators.jinja_docx_generator import JinjaDOCXSectionEGenerator
                generator = JinjaDOCXSectionEGenerator(template_path)
                docx_path = generator.generate_section_e_docx(employee_data)
            else:
                # Use traditional cell-mapping DOCX generator
                from src.generators.docx_section_e_generator import DOCXSectionEGenerator
                generator = DOCXSectionEGenerator(template_path)
                docx_path = generator.generate_section_e_docx(employee_data)
            
            if docx_path and os.path.exists(docx_path):
                # Read the DOCX file
                with open(docx_path, 'rb') as docx_file:
                    docx_content = docx_file.read()
                
                # Send DOCX response
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                self.send_header('Content-Disposition', f'attachment; filename="SectionE_{employee_data.get("name", "Unknown").replace(" ", "_")}_{template_info["name"].replace(" ", "_")}.docx"')
                self.send_header('Content-Length', str(len(docx_content)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(docx_content)
                
                template_type = "Jinja" if template_info.get('type') == 'jinja_docx' else "Cell-mapping"
                print(f"✅ Custom DOCX ({template_type}) with template '{template_info['name']}' served successfully")
                return
            else:
                raise Exception("Failed to generate DOCX with template")
                
        except ImportError as e:
            print(f"⚠️ DOCX generator dependencies not installed: {e}")
            # Provide a more helpful error message
            if 'docxtpl' in str(e) or 'jinja' in str(e).lower():
                raise Exception("Jinja DOCX generation dependencies not available. Please run: pip install docxtpl")
            elif 'docx' in str(e):
                raise Exception("DOCX generation dependencies not available. Please run: pip install python-docx")
            else:
                raise Exception("DOCX generation dependencies not available")
        except Exception as e:
            print(f"⚠️ DOCX generation failed: {e}")
            raise

    def serve_employee_qualifications_api(self, employee_id):
        """Serve all professional qualifications for an employee"""
        try:
            import json
            from urllib.parse import unquote
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Decode URL-encoded ID
            employee_id = unquote(employee_id)
            
            # Try to use Supabase
            try:
                from supabase import create_client
                
                supabase_url = os.getenv('SUPABASE_URL')
                supabase_key = os.getenv('SUPABASE_KEY')
                
                if supabase_url and supabase_key:
                    supabase = create_client(supabase_url, supabase_key)
                    
                    # Use the SQL function to get qualifications
                    result = supabase.rpc('get_employee_qualifications', {'p_employee_id': employee_id}).execute()
                    
                    if result.data:
                        qualifications = result.data
                    else:
                        qualifications = []
                    
                    response = json.dumps({
                        'employee_id': employee_id,
                        'qualifications': qualifications
                    }, default=str, indent=2)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(response.encode('utf-8'))
                    return
                else:
                    raise Exception("Supabase credentials not found")
                    
            except Exception as e:
                print(f"Supabase error, falling back to JSON: {e}")
                # Fallback to empty result for now (JSON doesn't have qualifications structure)
                response = json.dumps({
                    'employee_id': employee_id,
                    'qualifications': [],
                    'message': 'Qualifications only available with Supabase backend'
                }, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
                
        except Exception as e:
            print(f"Error serving employee qualifications API: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_set_primary_qualification_api(self):
        """Set primary qualification for an employee"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Read POST data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            request_data = json.loads(post_data)
            
            employee_id = request_data.get('employee_id')
            qualification_id = request_data.get('qualification_id')
            
            if not employee_id or not qualification_id:
                raise ValueError("Both employee_id and qualification_id are required")
            
            # Try to use Supabase
            try:
                from supabase import create_client
                
                supabase_url = os.getenv('SUPABASE_URL')
                supabase_key = os.getenv('SUPABASE_KEY')
                
                if supabase_url and supabase_key:
                    supabase = create_client(supabase_url, supabase_key)
                    
                    # Use the SQL function to set primary qualification
                    result = supabase.rpc('set_primary_qualification', {
                        'p_employee_id': employee_id,
                        'p_qualification_id': qualification_id
                    }).execute()
                    
                    if result.data:
                        response = json.dumps({
                            'success': True,
                            'message': 'Primary qualification updated successfully'
                        }, indent=2)
                        self.send_response(200)
                    else:
                        response = json.dumps({
                            'success': False,
                            'message': 'Failed to update primary qualification'
                        }, indent=2)
                        self.send_response(400)
                else:
                    raise Exception("Supabase credentials not found")
                    
            except Exception as e:
                print(f"Supabase error: {e}")
                response = json.dumps({
                    'success': False,
                    'error': str(e),
                    'message': 'Primary qualification setting only available with Supabase backend'
                }, indent=2)
                self.send_response(500)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
                
        except Exception as e:
            print(f"Error setting primary qualification: {e}")
            error_response = json.dumps({
                'success': False,
                'error': str(e)
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_employees_for_merge_api(self):
        """Serve employees list from Supabase database for merge functionality"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                # Return empty list if Supabase not configured
                response = json.dumps({
                    "employees": [],
                    "message": "Supabase not configured - merge feature requires database connection"
                })
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
                return
            
            # Connect to Supabase and get employees
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Get all employees from the database with role aggregation
            result = supabase.table('employee_profiles').select('employee_id, employee_name, role_in_contract, total_years_experience, education, source_filename').order('employee_name').execute()
            
            employees = result.data if result.data else []
            
            # Clean up roles in each employee record
            for employee in employees:
                if employee.get('role_in_contract'):
                    employee['role_in_contract'] = self.deduplicate_role_string(employee['role_in_contract'])
            
            response = json.dumps({
                "employees": employees,
                "count": len(employees)
            }, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error loading employees for merge: {e}")
            error_response = json.dumps({
                "error": str(e),
                "employees": []
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_potential_duplicates_api(self):
        """Serve API endpoint to find potential duplicate employees"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                # Return empty list if Supabase not configured
                response = json.dumps({
                    "duplicates": [],
                    "message": "Supabase not configured - merge feature requires database connection"
                })
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
                return
            
            # Connect to Supabase and find potential duplicates
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to find potential duplicates
            print(f"🔍 Calling find_potential_duplicate_employees function...")
            result = supabase.rpc('find_potential_duplicate_employees', {
                'p_similarity_threshold': 0.7
            }).execute()
            
            print(f"📊 Raw duplicate search result: {result}")
            duplicates = result.data if result.data else []
            print(f"🎯 Found {len(duplicates)} potential duplicates")
            
            response = json.dumps({
                "duplicates": duplicates,
                "count": len(duplicates)
            }, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error finding potential duplicates: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "error": f"Server error while finding duplicates: {str(e)}",
                "duplicates": []
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_merge_preview_api(self, primary_id, secondary_id):
        """Serve API endpoint to preview employee merge"""
        try:
            import json
            from urllib.parse import unquote
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Decode URL-encoded IDs
            primary_id = unquote(primary_id)
            secondary_id = unquote(secondary_id)
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - merge preview requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and get merge preview
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to get merge preview
            result = supabase.rpc('get_merge_preview', {
                'p_primary_employee_id': primary_id,
                'p_secondary_employee_id': secondary_id
            }).execute()
            
            if result.data and 'error' in result.data:
                error_response = json.dumps({"error": result.data['error']})
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            preview_data = result.data if result.data else {}
            
            response = json.dumps(preview_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error getting merge preview: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_merge_employees_api(self):
        """Serve API endpoint to merge two employees"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - merge operation requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            primary_id = data.get('primary_employee_id')
            secondary_id = data.get('secondary_employee_id')
            merge_options = data.get('merge_options', {})
            
            print(f"🔄 Merge request received:")
            print(f"   Primary ID: {primary_id}")
            print(f"   Secondary ID: {secondary_id}")
            print(f"   Options: {merge_options}")
            
            if not primary_id or not secondary_id:
                error_response = json.dumps({
                    "success": False,
                    "error": "Both primary_employee_id and secondary_employee_id are required"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and perform merge
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to merge employees
            print(f"🔗 Calling merge_employees function...")
            result = supabase.rpc('merge_employees', {
                'p_primary_employee_id': primary_id,
                'p_secondary_employee_id': secondary_id,
                'p_merge_options': json.dumps(merge_options)
            }).execute()
            
            print(f"📊 Raw Supabase result: {result}")
            
            merge_result = result.data if result.data else {}
            print(f"🎯 Processed merge result: {merge_result}")
            
            if merge_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully merged employees: {merge_result.get('secondary_employee_name')} → {merge_result.get('primary_employee_name')}")
            else:
                self.send_response(400)
                error_msg = merge_result.get('error', 'Unknown database error')
                print(f"❌ Failed to merge employees: {error_msg}")
                # Ensure we always return a proper error structure
                if not isinstance(merge_result, dict) or not merge_result.get('error'):
                    merge_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(merge_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error merging employees: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_teams_for_merge_api(self):
        """Serve API endpoint to get teams list for merge functionality"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - teams merge requires database connection",
                    "teams": []
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Get all teams from the database
            result = supabase.table('teams').select('team_id, firm_name, location, created_at').execute()
            
            teams = result.data if result.data else []
            
            response = json.dumps({
                "teams": teams,
                "message": f"Found {len(teams)} teams" if teams else "No teams found in database"
            }, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error loading teams for merge: {e}")
            error_response = json.dumps({
                "error": str(e),
                "teams": []
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_potential_duplicate_teams_api(self):
        """Serve API endpoint to find potential duplicate teams"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - duplicate detection requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to find potential duplicates
            result = supabase.rpc('find_potential_duplicate_teams', {
                'p_similarity_threshold': 0.7
            }).execute()
            
            duplicates = result.data if result.data else []
            
            response = json.dumps({
                "duplicates": duplicates,
                "count": len(duplicates)
            }, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error finding duplicate teams: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_team_merge_preview_api(self, primary_id, secondary_id):
        """Serve API endpoint to preview team merge operation"""
        try:
            import json
            from dotenv import load_dotenv
            from urllib.parse import unquote
            
            # Decode URL-encoded IDs
            primary_id = unquote(primary_id)
            secondary_id = unquote(secondary_id)
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - merge preview requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to get merge preview
            result = supabase.rpc('get_team_merge_preview', {
                'p_primary_team_id': primary_id,
                'p_secondary_team_id': secondary_id
            }).execute()
            
            if result.data and 'error' in result.data:
                error_response = json.dumps({"error": result.data['error']})
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            preview_data = result.data if result.data else {}
            
            response = json.dumps(preview_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error getting team merge preview: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_merge_teams_api(self):
        """Serve API endpoint to merge two teams"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - merge operation requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            primary_id = data.get('primary_team_id')
            secondary_id = data.get('secondary_team_id')
            merge_options = data.get('merge_options', {})
            
            print(f"🔄 Team merge request received:")
            print(f"   Primary ID: {primary_id}")
            print(f"   Secondary ID: {secondary_id}")
            print(f"   Options: {merge_options}")
            
            if not primary_id or not secondary_id:
                error_response = json.dumps({
                    "success": False,
                    "error": "Both primary_team_id and secondary_team_id are required"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and perform merge
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to merge teams
            print(f"🔗 Calling merge_teams function...")
            result = supabase.rpc('merge_teams', {
                'p_primary_team_id': primary_id,
                'p_secondary_team_id': secondary_id,
                'p_merge_options': json.dumps(merge_options)
            }).execute()
            
            print(f"📊 Raw Supabase result: {result}")
            
            merge_result = result.data if result.data else {}
            print(f"🎯 Processed merge result: {merge_result}")
            
            if merge_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully merged teams: {merge_result.get('secondary_team_name')} → {merge_result.get('primary_team_name')}")
            else:
                self.send_response(400)
                error_msg = merge_result.get('error', 'Unknown database error')
                print(f"❌ Failed to merge teams: {error_msg}")
                # Ensure we always return a proper error structure
                if not isinstance(merge_result, dict) or not merge_result.get('error'):
                    merge_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(merge_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error merging teams: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_roles_for_merge_api(self):
        """Serve API endpoint to get all roles for manual merge selection"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - role operations require database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to get roles for merge
            result = supabase.rpc('get_roles_for_merge').execute()
            
            roles_data = result.data if result.data else []
            
            response = json.dumps(roles_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error getting roles for merge: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_potential_duplicate_roles_api(self):
        """Serve API endpoint to get potential duplicate roles"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - role operations require database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to find potential duplicates
            result = supabase.rpc('find_potential_duplicate_roles', {
                'p_similarity_threshold': 0.7
            }).execute()
            
            duplicates_data = result.data if result.data else []
            
            response = json.dumps(duplicates_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error getting potential duplicate roles: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_role_merge_preview_api(self, primary_role, secondary_role):
        """Serve API endpoint to preview role merge operation"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - role operations require database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to get role merge preview
            result = supabase.rpc('get_role_merge_preview', {
                'p_primary_role': primary_role,
                'p_secondary_role': secondary_role
            }).execute()
            
            if result.data and 'error' in result.data:
                error_response = json.dumps({"error": result.data['error']})
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            preview_data = result.data if result.data else {}
            
            response = json.dumps(preview_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error getting role merge preview: {e}")
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_merge_roles_api(self):
        """Serve API endpoint to merge two roles"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - role merge operation requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            primary_role = data.get('primary_role')
            secondary_role = data.get('secondary_role')
            merge_options = data.get('merge_options', {})
            
            print(f"🔄 Role merge request received:")
            print(f"   Primary Role: {primary_role}")
            print(f"   Secondary Role: {secondary_role}")
            print(f"   Options: {merge_options}")
            
            if not primary_role or not secondary_role:
                error_response = json.dumps({
                    "success": False,
                    "error": "Both primary_role and secondary_role are required"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and perform merge
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to merge roles
            print(f"🔗 Calling merge_roles function...")
            result = supabase.rpc('merge_roles', {
                'p_primary_role': primary_role,
                'p_secondary_role': secondary_role,
                'p_merge_options': json.dumps(merge_options)
            }).execute()
            
            print(f"📊 Raw Supabase result: {result}")
            
            merge_result = result.data if result.data else {}
            print(f"🎯 Processed merge result: {merge_result}")
            
            if merge_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully merged roles: {merge_result.get('secondary_role')} → {merge_result.get('final_role')}")
            else:
                self.send_response(400)
                error_msg = merge_result.get('error', 'Unknown database error')
                print(f"❌ Failed to merge roles: {error_msg}")
                # Ensure we always return a proper error structure
                if not isinstance(merge_result, dict) or not merge_result.get('error'):
                    merge_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(merge_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error merging roles: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_split_compound_roles_api(self):
        """Serve API endpoint to split compound roles"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - role operations require database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            compound_role = data.get('compound_role')
            employee_id = data.get('employee_id')  # Optional: can be null to affect all employees
            
            print(f"🔄 Role split request received:")
            print(f"   Compound Role: {compound_role}")
            print(f"   Employee ID: {employee_id or 'All employees'}")
            
            if not compound_role:
                error_response = json.dumps({
                    "success": False,
                    "error": "compound_role is required"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and perform split
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to split compound roles
            print(f"🔗 Calling split_compound_roles function...")
            result = supabase.rpc('split_compound_roles', {
                'p_compound_role': compound_role,
                'p_employee_id': employee_id
            }).execute()
            
            print(f"📊 Raw Supabase result: {result}")
            
            split_result = result.data if result.data else {}
            print(f"🎯 Processed split result: {split_result}")
            
            if split_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully split role: {split_result.get('original_role')} → {split_result.get('new_role_string')}")
            else:
                self.send_response(400)
                error_msg = split_result.get('error', 'Unknown database error')
                print(f"❌ Failed to split role: {error_msg}")
                # Ensure we always return a proper error structure
                if not isinstance(split_result, dict) or not split_result.get('error'):
                    split_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(split_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error splitting compound role: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_normalize_roles_api(self):
        """Serve API endpoint to normalize all roles"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - role operations require database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and perform normalization
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to normalize all roles
            print(f"🔗 Calling normalize_all_roles function...")
            result = supabase.rpc('normalize_all_roles').execute()
            
            print(f"📊 Raw Supabase result: {result}")
            
            normalize_result = result.data if result.data else {}
            print(f"🎯 Processed normalization result: {normalize_result}")
            
            if normalize_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully normalized roles: {normalize_result.get('employees_updated')} employees updated, {normalize_result.get('duplicates_removed')} duplicates removed")
            else:
                self.send_response(400)
                error_msg = normalize_result.get('error', 'Unknown database error')
                print(f"❌ Failed to normalize roles: {error_msg}")
                # Ensure we always return a proper error structure
                if not isinstance(normalize_result, dict) or not normalize_result.get('error'):
                    normalize_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(normalize_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error normalizing roles: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_execute_split_roles_api(self):
        """Execute the split_roles.py script and return its output"""
        try:
            import subprocess
            import json
            
            print("🚀 Executing split_roles.py script...")
            
            # Execute the split_roles.py script with --apply flag
            split_roles_path = os.path.join(os.path.dirname(__file__), '..', '..', 'utils', 'split_roles.py')
            result = subprocess.run(
                ['python3', split_roles_path, '--apply'],
                capture_output=True,
                text=True,
                cwd='.',  # Run in current directory
                timeout=300  # 5 minute timeout
            )
            
            # Prepare response data
            response_data = {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'executed_at': __import__('datetime').datetime.now().isoformat()
            }
            
            print(f"📊 Script execution completed with return code: {result.returncode}")
            if result.stdout:
                print(f"✅ STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"⚠️ STDERR:\n{result.stderr}")
            
            response = json.dumps(response_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except subprocess.TimeoutExpired:
            error_response = json.dumps({
                "success": False,
                "error": "Script execution timed out after 5 minutes",
                "executed_at": __import__('datetime').datetime.now().isoformat()
            })
            self.send_response(408)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error executing split_roles.py: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}",
                "executed_at": __import__('datetime').datetime.now().isoformat()
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_delete_employee_preview_api(self, employee_id):
        """Serve API endpoint to preview employee deletion"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - delete operation requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            print(f"🔍 Getting delete preview for employee: {employee_id}")
            
            # Connect to Supabase and get delete preview
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to get delete preview
            result = supabase.rpc('get_employee_delete_preview', {
                'p_employee_id': employee_id
            }).execute()
            
            print(f"📊 Raw Supabase result: {result}")
            
            preview_result = result.data if result.data else {}
            print(f"🎯 Processed preview result: {preview_result}")
            
            if preview_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully retrieved delete preview for employee {employee_id}")
            else:
                self.send_response(400)
                error_msg = preview_result.get('error', 'Unknown database error')
                print(f"❌ Failed to get delete preview: {error_msg}")
                if not isinstance(preview_result, dict) or not preview_result.get('error'):
                    preview_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(preview_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error getting delete preview: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_delete_employee_api(self):
        """Serve API endpoint to delete an employee"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - delete operation requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            employee_id = data.get('employee_id')
            
            print(f"🗑️ Delete request received for employee: {employee_id}")
            
            if not employee_id:
                error_response = json.dumps({
                    "success": False,
                    "error": "employee_id is required"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and perform deletion
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to delete employee
            print(f"🔗 Calling delete_employee_complete function...")
            try:
                result = supabase.rpc('delete_employee_complete', {
                    'p_employee_id': employee_id
                }).execute()
                
                print(f"📊 Raw Supabase result: {result}")
                delete_result = result.data if result.data else {}
                print(f"🎯 Processed delete result: {delete_result}")
                
            except Exception as rpc_error:
                # Handle the common Supabase JSON parsing issue
                error_str = str(rpc_error)
                print(f"🔍 RPC Error details: {error_str}")
                
                # Check if this is the JSON parsing error but operation was successful
                if "JSON could not be generated" in error_str and "success\": true" in error_str:
                    # Extract the actual result from the error details
                    import re
                    match = re.search(r'b\'(\{.*?\})\'', error_str)
                    if match:
                        try:
                            result_json = match.group(1).encode().decode('unicode_escape')
                            delete_result = json.loads(result_json)
                            print(f"✅ Extracted successful result from error: {delete_result}")
                        except:
                            # Fallback: create basic success response
                            delete_result = {
                                'success': True,
                                'message': 'Employee deleted successfully (extracted from error details)'
                            }
                    else:
                        # Fallback: create basic success response
                        delete_result = {
                            'success': True,
                            'message': 'Employee deleted successfully'
                        }
                else:
                    # This is a real error, re-raise it
                    raise rpc_error
            
            if delete_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully deleted employee: {delete_result.get('employee_name')}")
            else:
                self.send_response(400)
                error_msg = delete_result.get('error', 'Unknown database error')
                print(f"❌ Failed to delete employee: {error_msg}")
                if not isinstance(delete_result, dict) or not delete_result.get('error'):
                    delete_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(delete_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error deleting employee: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_delete_project_api(self):
        """Serve API endpoint to delete a project from an employee"""
        try:
            import json
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Check if Supabase is configured
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                error_response = json.dumps({
                    "error": "Supabase not configured - delete operation requires database connection"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            employee_id = data.get('employee_id')
            project_id = data.get('project_id')
            
            print(f"🗑️ Delete project request received:")
            print(f"   Employee ID: {employee_id}")
            print(f"   Project ID: {project_id}")
            
            if not employee_id or not project_id:
                error_response = json.dumps({
                    "success": False,
                    "error": "Both employee_id and project_id are required"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Connect to Supabase and perform deletion
            from supabase import create_client
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Call the SQL function to delete project from employee
            print(f"🔗 Calling delete_employee_project function...")
            try:
                result = supabase.rpc('delete_employee_project', {
                    'p_employee_id': employee_id,
                    'p_project_id': project_id
                }).execute()
                
                print(f"📊 Raw Supabase result: {result}")
                delete_result = result.data if result.data else {}
                print(f"🎯 Processed delete result: {delete_result}")
                
            except Exception as rpc_error:
                # Handle the common Supabase JSON parsing issue
                error_str = str(rpc_error)
                print(f"🔍 RPC Error details: {error_str}")
                
                # Check if this is the JSON parsing error but operation was successful
                if "JSON could not be generated" in error_str and "success\": true" in error_str:
                    # Extract the actual result from the error details
                    import re
                    match = re.search(r'b\'(\{.*?\})\'', error_str)
                    if match:
                        try:
                            result_json = match.group(1).encode().decode('unicode_escape')
                            delete_result = json.loads(result_json)
                            print(f"✅ Extracted successful result from error: {delete_result}")
                        except:
                            # Fallback: create basic success response
                            delete_result = {
                                'success': True,
                                'message': 'Project deleted successfully (extracted from error details)'
                            }
                    else:
                        # Fallback: create basic success response
                        delete_result = {
                            'success': True,
                            'message': 'Project deleted successfully'
                        }
                else:
                    # This is a real error, re-raise it
                    raise rpc_error
            
            if delete_result.get('success'):
                self.send_response(200)
                print(f"✅ Successfully removed project {delete_result.get('project_title')} from employee {delete_result.get('employee_name')}")
            else:
                self.send_response(400)
                error_msg = delete_result.get('error', 'Unknown database error')
                print(f"❌ Failed to delete project: {error_msg}")
                if not isinstance(delete_result, dict) or not delete_result.get('error'):
                    delete_result = {
                        'success': False,
                        'error': f"Database operation failed: {error_msg}"
                    }
            
            response = json.dumps(delete_result, indent=2)
            
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            import traceback
            print(f"💥 Error deleting project: {e}")
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_trigger_processing_api(self):
        """Serve API endpoint to trigger immediate processing of uploaded files"""
        try:
            import json
            
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            filename = data.get('filename')
            
            if not filename:
                error_response = json.dumps({
                    "success": False,
                    "error": "filename is required"
                })
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            print(f"🔥 Immediate processing trigger received for: {filename}")
            
            # Try to trigger immediate processing using the bucket watcher's trigger system
            try:
                from src.automation.supabase_bucket_watcher import trigger_immediate_processing
                
                success = trigger_immediate_processing(filename)
                
                if success:
                    response = json.dumps({
                        "success": True,
                        "message": f"Successfully triggered immediate processing for {filename}",
                        "filename": filename
                    })
                    status_code = 200
                else:
                    response = json.dumps({
                        "success": False,
                        "error": f"Failed to create trigger for {filename}",
                        "filename": filename
                    })
                    status_code = 500
                    
            except ImportError:
                print("⚠️ Bucket watcher not available - trigger system not loaded")
                response = json.dumps({
                    "success": False,
                    "error": "Bucket watcher trigger system not available",
                    "note": "Make sure the automation module is properly installed"
                })
                status_code = 503
                
            except Exception as e:
                print(f"❌ Error triggering processing: {e}")
                response = json.dumps({
                    "success": False,
                    "error": f"Error creating trigger: {str(e)}",
                    "filename": filename
                })
                status_code = 500
            
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Error in trigger processing API: {e}")
            
            error_response = json.dumps({
                "success": False,
                "error": f"Server error: {str(e)}"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def serve_health_check(self):
        """Serve health check endpoint"""
        from datetime import datetime
        
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "env": "development"
        }
        
        response = str(health).replace("'", '"')
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def serve_upload_template_api(self):
        """Handle template upload and update templates.json"""
        try:
            import json
            import uuid
            from datetime import datetime
            
            print("🔍 Upload template API called")
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            print(f"📝 Content length: {content_length}")
            
            if content_length == 0:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = json.dumps({"error": "No content in request"})
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            print("📥 Reading request data...")
            post_data = self.rfile.read(content_length).decode('utf-8')
            print(f"📤 Received data: {post_data[:100]}...")  # First 100 chars
            
            print("🔧 Parsing JSON...")
            template_data = json.loads(post_data)
            print(f"✅ Parsed JSON: {template_data}")
            
            # Validate required fields
            required_fields = ['name', 'filename', 'type']
            for field in required_fields:
                if not template_data.get(field):
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    error_response = json.dumps({"error": f"Missing required field: {field}"})
                    self.wfile.write(error_response.encode('utf-8'))
                    return
            
            # Load existing templates
            templates_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'templates.json')
            print(f"📁 Loading templates from: {templates_file_path}")
            
            try:
                with open(templates_file_path, 'r', encoding='utf-8') as f:
                    templates_config = json.load(f)
            except FileNotFoundError:
                # Create templates.json if it doesn't exist
                templates_config = {"templates": []}
            
            # Generate unique ID for the template
            template_id = f"uploaded_{uuid.uuid4().hex[:8]}"
            print(f"🆔 Generated template ID: {template_id}")
            
            # Create new template entry
            new_template = {
                "id": template_id,
                "name": template_data['name'],
                "description": template_data.get('description', ''),
                "filename": template_data['filename'],
                "preview_image": None,
                "is_default": False,
                "type": template_data['type'],
                "uploaded_at": datetime.now().isoformat(),
                "original_filename": template_data.get('originalFilename', template_data['filename']),
                "file_size": template_data.get('size', 0)
            }
            
            # Add to templates list
            templates_config['templates'].append(new_template)
            print(f"📋 Added template to config. Total templates: {len(templates_config['templates'])}")
            
            # Save updated templates.json
            print("💾 Saving templates.json...")
            with open(templates_file_path, 'w', encoding='utf-8') as f:
                json.dump(templates_config, f, indent=2, ensure_ascii=False)
            
            # Respond with success
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            success_response = json.dumps({
                "success": True,
                "template_id": template_id,
                "message": f"Template '{template_data['name']}' uploaded successfully",
                "template": new_template
            }, indent=2)
            
            self.wfile.write(success_response.encode('utf-8'))
            print("✅ Response sent successfully")
            
            print(f"🎉 Template '{template_data['name']}' uploaded and registered successfully")
            print(f"📄 Template ID: {template_id}")
            print(f"📁 File: {template_data['filename']}")
            print(f"🏷️  Type: {template_data['type']}")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = json.dumps({"error": "Invalid JSON data"})
            self.wfile.write(error_response.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Error in upload template API: {e}")
            import traceback
            traceback.print_exc()
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = json.dumps({"error": str(e)})
            self.wfile.write(error_response.encode('utf-8'))
    
    def serve_ai_rewrite_api(self):
        """Serve AI rewrite API endpoint using OpenAI"""
        try:
            import json
            import openai
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Get OpenAI API key
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = json.dumps({
                    "error": "OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file."
                })
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Set up OpenAI client
            client = openai.OpenAI(api_key=openai_api_key)
            
            # Read POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            original_scope = request_data.get('original_scope', '')
            keywords = request_data.get('keywords', '')
            
            if not original_scope:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = json.dumps({"error": "Original scope is required"})
                self.wfile.write(error_response.encode('utf-8'))
                return
            
            # Create the prompt for OpenAI
            prompt = f"""Rewrite the following civil engineering project scope while incorporating the provided keywords. Maintain the structure, tone, and technical nature suitable for a professional civil engineering proposal. Provide 3 alternative rewritten versions. Keep the scope realistic and context-aware.

Original Scope:
{original_scope}

Keywords:
{keywords}

Please provide exactly 3 different rewritten versions, each maintaining the professional tone and technical accuracy of civil engineering work. Each version should incorporate the provided keywords naturally while preserving the essential project details."""
            
            print(f"🔄 Generating AI rewrites for scope with keywords: {keywords}")
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional civil engineering technical writer who specializes in creating project scope descriptions for government proposals and Section E resumes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            # Parse the response to extract the 3 versions
            full_response = response.choices[0].message.content
            
            if not full_response:
                full_response = original_scope  # Fallback to original
            
            # Try to split the response into 3 versions
            # Look for common patterns like "Version 1:", "1.", etc.
            import re
            
            # Split by version indicators
            version_patterns = [
                r'Version\s*\d+:?',
                r'\d+\.',
                r'Option\s*\d+:?',
                r'Alternative\s*\d+:?'
            ]
            
            versions = []
            for pattern in version_patterns:
                splits = re.split(pattern, full_response, flags=re.IGNORECASE)
                if len(splits) > 3:  # Should have at least 4 parts (before first version + 3 versions)
                    versions = [v.strip() for v in splits[1:4] if v.strip()]  # Take first 3 versions
                    break
            
            # If splitting by patterns didn't work, try paragraph splitting
            if len(versions) < 3:
                paragraphs = [p.strip() for p in full_response.split('\n\n') if p.strip()]
                if len(paragraphs) >= 3:
                    versions = paragraphs[-3:]  # Take last 3 substantial paragraphs
            
            # Final fallback: split by double newlines and take substantial ones
            if len(versions) < 3:
                parts = [p.strip() for p in full_response.split('\n') if len(p.strip()) > 50]
                versions = parts[:3] if len(parts) >= 3 else [full_response]
            
            # Ensure we have exactly 3 versions, pad if necessary
            while len(versions) < 3:
                if versions:
                    # Create slight variations of the last version
                    last_version = versions[-1]
                    versions.append(f"Alternative: {last_version}")
                else:
                    versions.append(original_scope)  # Fallback to original
            
            # Take only first 3 versions
            versions = versions[:3]
            
            print(f"✅ Generated {len(versions)} rewrite versions")
            
            # Return the rewritten versions
            response_data = {
                "success": True,
                "rewritten_versions": versions,
                "original_scope": original_scope,
                "keywords": keywords
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, indent=2).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in AI rewrite API: {e}")
            import traceback
            traceback.print_exc()
            
            error_response = json.dumps({
                "error": str(e),
                "message": "Failed to generate AI rewrites"
            })
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        if self.path not in ['/favicon.ico']:  # Suppress favicon requests
            return super().log_message(format, *args)


def main():
    """Start the web server"""
    PORT = int(os.getenv('PORT', 8000))
    
    # Create server
    with socketserver.TCPServer(("", PORT), UIHandler) as httpd:
        print('\n🚀 Section E Resume Database Server (Python)')
        print('=============================================')
        print(f'📍 Server running at: http://localhost:{PORT}')
        print(f'📁 Serving from: {os.getcwd()}')
        
        # Check environment setup
        if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_KEY'):
            print('✅ Environment variables detected')
            print('🔗 Database connection will be enabled')
        else:
            print('⚠️  No .env file detected - demo mode will be available')
            print('💡 Make sure .env file exists with SUPABASE_URL and SUPABASE_KEY')
        
        print(f'\n🌐 Open your browser and go to: http://localhost:{PORT}')
        print('=============================================\n')
        
        # Try to open browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}')
            print('🎉 Browser should open automatically!')
        except:
            print('💡 Please open your browser manually')
        
        print('\n⌨️  Press Ctrl+C to stop the server\n')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n🛑 Server shutting down gracefully...')
            httpd.shutdown()


if __name__ == '__main__':
    main() 