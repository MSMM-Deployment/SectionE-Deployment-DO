import json
import os
from pathlib import Path

def handler(event, context):
    """
    Netlify function to serve index.html with environment variables injected
    This is a fallback for when build-time injection doesn't work
    """
    
    try:
        # Get environment variables with debugging
        supabase_url = os.environ.get('SUPABASE_URL', '{{SUPABASE_URL}}')
        supabase_key = os.environ.get('SUPABASE_KEY', '{{SUPABASE_KEY}}')
        
        # Debug environment variables
        print(f"🔍 Function Debug: SUPABASE_URL = {supabase_url[:50]}..." if supabase_url != '{{SUPABASE_URL}}' else "🔍 Function Debug: SUPABASE_URL not found")
        print(f"🔍 Function Debug: SUPABASE_KEY = {supabase_key[:50]}..." if supabase_key != '{{SUPABASE_KEY}}' else "🔍 Function Debug: SUPABASE_KEY not found")
        
        # Try multiple possible file paths
        possible_paths = [
            Path(__file__).parent.parent.parent / "src" / "web" / "index.html",  # Original location
            Path(__file__).parent.parent.parent / "dist" / "index.html",        # Built location  
            Path(__file__).parent.parent / "index.html",                        # Adjacent to functions
            Path("src/web/index.html"),                                         # Relative from project root
            Path("dist/index.html"),                                            # Relative from project root
        ]
        
        html_content = None
        used_path = None
        
        for html_file_path in possible_paths:
            try:
                print(f"🔍 Trying path: {html_file_path}")
                if html_file_path.exists():
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    used_path = html_file_path
                    print(f"✅ Successfully read from: {html_file_path}")
                    break
                else:
                    print(f"❌ Path not found: {html_file_path}")
            except Exception as path_error:
                print(f"❌ Error reading {html_file_path}: {path_error}")
                continue
        
        if not html_content:
            # Return debug information if no file found
            debug_info = f"""
            <html><body>
            <h1>Debug: File Not Found</h1>
            <p>Function working directory: {os.getcwd()}</p>
            <p>Function file location: {__file__}</p>
            <p>SUPABASE_URL: {supabase_url}</p>
            <p>SUPABASE_KEY: {supabase_key[:20]}...</p>
            <p>Tried paths: {[str(p) for p in possible_paths]}</p>
            </body></html>
            """
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html; charset=utf-8'},
                'body': debug_info
            }
        
        # Inject environment variables
        html_content = html_content.replace('{{SUPABASE_URL}}', supabase_url)
        html_content = html_content.replace('{{SUPABASE_KEY}}', supabase_key)
        
        print(f"🔑 Injected environment variables using file: {used_path}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'public, max-age=300'  # Cache for 5 minutes
            },
            'body': html_content
        }
        
    except Exception as e:
        # Return error details for debugging
        print(f"🚨 Function error: {e}")
        debug_error = f"""
        <html><body>
        <h1>Function Error</h1>
        <p>Error: {str(e)}</p>
        <p>Working directory: {os.getcwd()}</p>
        <p>Function location: {__file__}</p>
        <p>Environment variables available: {list(os.environ.keys())[:10]}</p>
        </body></html>
        """
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html; charset=utf-8'},
            'body': debug_error
        } 