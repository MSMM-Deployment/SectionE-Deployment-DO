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
    Scheduled bucket watcher function - automatically runs every 5 minutes
    This is triggered by Netlify's scheduled functions feature
    """
    
    try:
        print(f"🔄 Scheduled bucket check started at {datetime.now().isoformat()}")
        
        # Check if Supabase is configured
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("⚠️  Supabase not configured - skipping bucket check")
            return success_response({
                "status": "skipped",
                "message": "Supabase not configured",
                "timestamp": datetime.now().isoformat()
            })
        
        # Import and initialize the bucket watcher
        from src.automation.supabase_bucket_watcher import SupabaseBucketWatcher
        
        # Create watcher instance
        watcher = SupabaseBucketWatcher(
            bucket_name="msmm-resumes",
            polling_interval=300  # 5 minutes for scheduled runs
        )
        
        # Check for new files and process them
        new_files = watcher.check_for_new_files()
        processed_files = []
        errors = []
        
        if new_files:
            print(f"📁 Found {len(new_files)} new files to process: {new_files}")
            
            for filename in new_files:
                try:
                    print(f"🔄 Processing {filename}...")
                    watcher.process_file(filename)
                    processed_files.append(filename)
                    print(f"✅ Successfully processed {filename}")
                except Exception as e:
                    error_msg = f"Error processing {filename}: {str(e)}"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)
        else:
            print("📝 No new files found in bucket")
        
        # Also check trigger queue for immediate processing requests
        try:
            watcher.check_trigger_queue()
        except Exception as e:
            print(f"⚠️  Error checking trigger queue: {e}")
        
        result = {
            "status": "success",
            "message": "Scheduled bucket check completed",
            "new_files_found": len(new_files),
            "processed_files": processed_files,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Scheduled bucket check completed: {len(processed_files)} processed, {len(errors)} errors")
        
        return success_response(result)
        
    except ImportError as e:
        error_msg = f"Failed to import bucket watcher: {str(e)}"
        print(f"❌ {error_msg}")
        return error_response(error_msg, 500)
    except Exception as e:
        error_msg = f"Scheduled bucket watcher error: {str(e)}"
        print(f"❌ {error_msg}")
        return error_response(error_msg, 500) 