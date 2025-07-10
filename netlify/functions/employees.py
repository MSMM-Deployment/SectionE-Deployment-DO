import os
import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def get_cors_headers():
    """Standard CORS headers for all API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

def success_response(data, status_code=200):
    """Create a successful JSON response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_headers()
        },
        'body': json.dumps(data)
    }

def error_response(message, status_code=500):
    """Create an error JSON response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_headers()
        },
        'body': json.dumps({"error": message})
    }

def deduplicate_role_string(role_string):
    """Clean and deduplicate a comma-separated role string"""
    if not role_string:
        return role_string
        
    # Split by comma, clean each role, and deduplicate
    roles = []
    for role in role_string.split(','):
        cleaned_role = role.strip()
        if cleaned_role and cleaned_role not in roles:
            roles.append(cleaned_role)
    
    return ', '.join(roles)

def handler(event, context):
    """Employees API endpoint - returns list of all employees"""
    
    # Handle CORS preflight
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': ''
        }
    
    # Only allow GET requests
    if event['httpMethod'] != 'GET':
        return error_response("Method not allowed", 405)
    
    try:
        # Load parsed results from the JSON file
        json_file_path = project_root / 'data' / 'ParsedFiles' / 'real_parsed_results.json'
        
        if not json_file_path.exists():
            return error_response("Parsed results file not found", 404)
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Transform raw parser data into frontend-friendly format
        employees = []
        for idx, resume in enumerate(data.get('resumes', [])):
            if not resume.get('personal_info', {}).get('name'):
                continue
                
            personal_info = resume.get('personal_info', {})
            
            # Get roles from projects and deduplicate
            roles = set()
            for project in resume.get('projects', []):
                if project.get('role'):
                    roles.add(project['role'])
            
            roles_string = ', '.join(sorted(roles)) if roles else ''
            roles_string = deduplicate_role_string(roles_string)
            
            # Get unique teams from projects
            teams = set()
            for project in resume.get('projects', []):
                if project.get('team'):
                    teams.add(project['team'])
            teams_string = ', '.join(sorted(teams)) if teams else ''
            
            employee = {
                'id': idx + 1,
                'name': personal_info.get('name', ''),
                'email': personal_info.get('email', ''),
                'phone': personal_info.get('phone', ''),
                'location': personal_info.get('address', ''),
                'roles': roles_string,
                'teams': teams_string,
                'projects_count': len(resume.get('projects', [])),
                'experience_years': resume.get('experience_summary', {}).get('total_years', 0),
                'education': resume.get('education', [{}])[0].get('degree', '') if resume.get('education') else '',
                'certifications_count': len(resume.get('certifications', [])),
                'skills': ', '.join(resume.get('skills', [])) if resume.get('skills') else '',
                'last_updated': resume.get('metadata', {}).get('parsed_date', '')
            }
            
            employees.append(employee)
        
        return success_response(employees)
        
    except Exception as e:
        return error_response(f"Failed to load employees: {str(e)}") 