import os
import json

def handler(event, context):
    """Configuration API endpoint - returns Supabase configuration status"""
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': ''
        }
    
    # Only allow GET requests
    if event.get('httpMethod') != 'GET':
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({"error": "Method not allowed"})
        }
    
    try:
        # Get environment variables
        supabase_url = os.getenv('SUPABASE_URL', '')
        supabase_key = os.getenv('SUPABASE_KEY', '')
        
        # Check if environment variables are properly set
        is_configured = bool(supabase_url and supabase_key and 
                           not supabase_url.startswith('{{') and 
                           not supabase_key.startswith('{{'))
        
        # Configuration data to return
        config_data = {
            "supabaseConfigured": is_configured,
            "hasUrl": bool(supabase_url),
            "hasKey": bool(supabase_key),
            "supabaseUrl": "https://clcufcjifbvpbtsczkmx.supabase.co",
            "supabaseKey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNsY3VmY2ppZmJ2cGJ0c2N6a214Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTMxODQyNSwiZXhwIjoyMDY2ODk0NDI1fQ.fQTie6YIgPMl_8bo2W6e6jCjk7tGxWFXdSZZj0RTNa0",
            "demoMode": not is_configured
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(config_data)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({"error": f"Configuration check failed: {str(e)}"})
        } 