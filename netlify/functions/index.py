import json
import os
from pathlib import Path

def handler(event, context):
    """
    Netlify function to serve index.html with environment variables injected
    This is a fallback for when build-time injection doesn't work
    """
    
    try:
        # Get environment variables
        supabase_url = os.environ.get('SUPABASE_URL', '{{SUPABASE_URL}}')
        supabase_key = os.environ.get('SUPABASE_KEY', '{{SUPABASE_KEY}}')
        
        # Read the HTML template from source
        html_file_path = Path(__file__).parent.parent.parent / "src" / "web" / "index.html"
        
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Inject environment variables
        html_content = html_content.replace('{{SUPABASE_URL}}', supabase_url)
        html_content = html_content.replace('{{SUPABASE_KEY}}', supabase_key)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'public, max-age=300'  # Cache for 5 minutes
            },
            'body': html_content
        }
        
    except Exception as e:
        # Fallback to static file if function fails
        return {
            'statusCode': 302,
            'headers': {
                'Location': '/index.html'
            }
        } 