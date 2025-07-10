import os
import json
import sys
from pathlib import Path

# Add project root to Python path for imports
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

def error_response(message, status_code=500, details=None):
    """Create an error JSON response"""
    error_data = {"error": message}
    if details:
        error_data["details"] = details
        
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_headers()
        },
        'body': json.dumps(error_data)
    }

def parse_request_body(event):
    """Parse JSON body from the event"""
    try:
        if event.get('body'):
            return json.loads(event['body'])
        return {}
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in request body")

def get_env_variable(key, default=None):
    """Get environment variable with fallback"""
    return os.getenv(key, default)

def check_supabase_config():
    """Check if Supabase is properly configured"""
    supabase_url = get_env_variable('SUPABASE_URL')
    supabase_key = get_env_variable('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        return False, "Supabase not configured - please set SUPABASE_URL and SUPABASE_KEY environment variables"
    
    return True, None

def create_supabase_client():
    """Create and return Supabase client"""
    is_configured, error_msg = check_supabase_config()
    if not is_configured:
        raise Exception(error_msg)
    
    try:
        from supabase import create_client
        supabase_url = get_env_variable('SUPABASE_URL')
        supabase_key = get_env_variable('SUPABASE_KEY')
        
        # Ensure we have valid strings (already checked in check_supabase_config)
        if not supabase_url or not supabase_key:
            raise Exception("Missing Supabase configuration")
            
        return create_client(supabase_url, supabase_key)
    except ImportError:
        raise Exception("Supabase client library not installed")

def handle_options_request():
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': ''
    } 