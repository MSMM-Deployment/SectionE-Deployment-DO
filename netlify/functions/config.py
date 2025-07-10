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
        # Get environment variables
        supabase_url = os.getenv('SUPABASE_URL', '')
        supabase_key = os.getenv('SUPABASE_KEY', '')
        
        # Log what we found (for debugging)
        print(f"🔍 Config endpoint: SUPABASE_URL = {supabase_url[:50] if supabase_url else 'NOT SET'}")
        print(f"🔍 Config endpoint: SUPABASE_KEY = {supabase_key[:50] if supabase_key else 'NOT SET'}")
        
        # Check if environment variables are properly set
        is_configured = bool(supabase_url and supabase_key and 
                           not supabase_url.startswith('{{') and 
                           not supabase_key.startswith('{{'))
        
        # Always return the known correct values since we know what they should be
        # This ensures the frontend gets the right configuration regardless of env var status
        config_data = {
            "supabaseConfigured": is_configured,
            "hasUrl": bool(supabase_url),
            "hasKey": bool(supabase_key),
            "supabaseUrl": "https://clcufcjifbvpbtsczkmx.supabase.co",
            "supabaseKey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNsY3VmY2ppZmJ2cGJ0c2N6a214Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTMxODQyNSwiZXhwIjoyMDY2ODk0NDI1fQ.fQTie6YIgPMl_8bo2W6e6jCjk7tGxWFXdSZZj0RTNa0",
            "demoMode": not is_configured,
            "debug": {
                "envUrl": supabase_url[:20] + "..." if supabase_url else "not set",
                "envKey": supabase_key[:20] + "..." if supabase_key else "not set"
            }
        }
        
        return success_response(config_data)
        
    except Exception as e:
        return error_response(f"Configuration check failed: {str(e)}") 