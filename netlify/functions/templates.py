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

def handler(event, context):
    """Templates API endpoint - returns list of available templates"""
    
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
        # Load templates metadata
        templates_file_path = project_root / 'templates' / 'templates.json'
        
        if not templates_file_path.exists():
            return error_response("Templates configuration file not found", 404)
        
        with open(templates_file_path, 'r', encoding='utf-8') as f:
            templates_data = json.load(f)
        
        return success_response(templates_data)
        
    except Exception as e:
        return error_response(f"Failed to load templates: {str(e)}") 