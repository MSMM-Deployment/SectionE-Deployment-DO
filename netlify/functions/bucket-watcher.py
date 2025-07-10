import os
import json
import sys
from pathlib import Path
from datetime import datetime

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
    """
    Bucket watcher function - checks for new files and processes them
    Can be triggered by Netlify scheduled functions or manual API calls
    """
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': ''
        }
    
    try:
        # Check if Supabase is configured
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            return error_response("Supabase not configured", 400)
        
        # Import and initialize the bucket watcher
        from src.automation.supabase_bucket_watcher import SupabaseBucketWatcher
        
        # Create watcher instance
        watcher = SupabaseBucketWatcher(
            bucket_name="msmm-resumes",
            polling_interval=30
        )
        
        # Check for new files and process them (single check, not continuous monitoring)
        new_files = watcher.check_for_new_files()
        processed_files = []
        
        if new_files:
            for filename in new_files:
                try:
                    watcher.process_file(filename)
                    processed_files.append(filename)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
        
        return success_response({
            "status": "success",
            "message": "Bucket check completed",
            "new_files_found": len(new_files),
            "processed_files": processed_files,
            "timestamp": datetime.now().isoformat()
        })
        
    except ImportError as e:
        return error_response(f"Failed to import bucket watcher: {str(e)}", 500)
    except Exception as e:
        return error_response(f"Bucket watcher error: {str(e)}", 500) 