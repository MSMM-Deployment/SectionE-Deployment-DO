import json
import os

def handler(event, context):
    """
    Simple API endpoint to provide frontend configuration
    Returns environment variables that frontend needs
    """
    
    try:
        # Get environment variables
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        # Determine if we're in demo mode
        is_configured = bool(supabase_url and supabase_key and 
                           not supabase_url.startswith('{{') and 
                           not supabase_key.startswith('{{'))
        
        response_data = {
            'supabaseConfigured': is_configured,
            'supabaseUrl': supabase_url if is_configured else '',
            'supabaseKey': supabase_key if is_configured else '',
            'demoMode': not is_configured
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'supabaseConfigured': False,
                'demoMode': True
            })
        } 