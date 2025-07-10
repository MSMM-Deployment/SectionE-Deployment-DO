import os
import json

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
    """Configuration API endpoint - checks Supabase setup"""
    
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
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        is_configured = bool(supabase_url and supabase_key)
        
        config_data = {
            "supabaseConfigured": is_configured,
            "hasUrl": bool(supabase_url),
            "hasKey": bool(supabase_key)
        }
        
        return success_response(config_data)
        
    except Exception as e:
        return error_response(f"Configuration check failed: {str(e)}") 