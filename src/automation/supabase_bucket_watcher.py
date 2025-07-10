#!/usr/bin/env python3
"""
Supabase Bucket Resume Watcher

This script monitors the Supabase bucket "msmm-resumes" for new uploaded files and automatically:
1. Marks existing files as "seen" without processing them (avoids processing old files)
2. Only processes files uploaded AFTER the watcher starts running
3. Downloads newly uploaded files to temporary processing folder
4. Runs section_e_parser.py on new files only
5. Loads parsed results into Supabase database
6. Maintains comprehensive logs of processing status
7. Uses timestamp-based detection to distinguish new vs existing files

Key Behavior:
- On startup: All existing files in bucket are marked as "seen" (not processed)
- During monitoring: Only files uploaded after startup are downloaded and processed
- Trigger queue: Allows manual processing of specific files on demand

Requirements:
pip install supabase watchdog

Usage:
python3 supabase_bucket_watcher.py
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set
from dotenv import load_dotenv

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from supabase import create_client
except ImportError:
    print("❌ Supabase client not installed. Run: pip install supabase")
    sys.exit(1)

# Load environment variables
load_dotenv()

class SupabaseBucketWatcher:
    """Monitors Supabase bucket for new resume uploads and processes them automatically
    
    Key Features:
    - Only processes files uploaded AFTER the watcher starts (ignores existing files)
    - Tracks processed files to avoid duplicates
    - Downloads newly uploaded files to temporary processing folder
    - Runs section_e_parser.py on new files only
    - Loads parsed results into Supabase database
    - Maintains comprehensive logs of processing status
    - Supports trigger queue for immediate processing requests
    """
    
    def __init__(self, 
                 bucket_name="msmm-resumes",
                 processed_log="data/processed_bucket_files.json",
                 polling_interval=30):
        """
        Initialize the Supabase bucket watcher
        
        Args:
            bucket_name: Name of the Supabase bucket to monitor
            processed_log: Path to file tracking processed files
            polling_interval: Seconds between bucket checks
        """
        self.bucket_name = bucket_name
        self.polling_interval = polling_interval
        
        # File tracking
        self.processed_log = Path(processed_log)
        self.processed_files = self.load_processed_files()
        self.processing_queue = set()  # Files currently being processed
        
        # Track when watcher started to only process files uploaded after this time
        self.watcher_start_time = datetime.utcnow()
        
        # Initialize trigger queue system
        self.trigger_queue_dir = Path("data/trigger_queue")
        self.trigger_queue_dir.mkdir(exist_ok=True)
        
        # Set up temporary processing directory
        self.temp_dir = Path("temp_processing")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize Supabase client
        self.supabase = self.init_supabase()
        
        # Mark existing files as "seen" without processing them
        self.initialize_existing_files()
        
        print(f"✅ Initialized bucket watcher for: {bucket_name}")
        print(f"📁 Processed files log: {self.processed_log}")
        print(f"📥 Temp processing directory: {self.temp_dir}")
        print(f"🔔 Trigger queue directory: {self.trigger_queue_dir}")
        print(f"⏰ Watcher started at: {self.watcher_start_time.isoformat()}")
    
    def init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                raise Exception("SUPABASE_URL and SUPABASE_KEY environment variables are required")
            
            client = create_client(supabase_url, supabase_key)
            print(f"✅ Connected to Supabase: {supabase_url}")
            return client
            
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            sys.exit(1)
    
    def initialize_existing_files(self):
        """Mark all existing files in bucket as 'seen' without processing them"""
        try:
            print("🔍 Scanning bucket for existing files...")
            bucket_files = self.get_bucket_files()
            existing_count = 0
            
            for file_info in bucket_files:
                filename = file_info['name']
                
                # Skip if already in processed files
                if filename in self.processed_files:
                    continue
                
                # Mark this existing file as "seen" without processing it
                self.processed_files.add(filename)
                existing_count += 1
                print(f"👀 Marked existing file as seen (will not process): {filename}")
            
            if existing_count > 0:
                self.save_processed_files()
                print(f"✅ Marked {existing_count} existing files as seen")
            else:
                print("✅ No new existing files to mark")
                
        except Exception as e:
            print(f"❌ Error initializing existing files: {e}")
    
    def load_processed_files(self) -> Set[str]:
        """Load list of already processed files from bucket"""
        if self.processed_log.exists():
            try:
                with open(self.processed_log, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_files', []))
            except (json.JSONDecodeError, KeyError):
                print("⚠️  Warning: Could not load processed files log, starting fresh")
        return set()
    
    def save_processed_files(self):
        """Save list of processed files with watcher metadata"""
        try:
            data = {
                'processed_files': list(self.processed_files),
                'last_updated': datetime.utcnow().isoformat(),
                'bucket_name': self.bucket_name,
                'watcher_start_time': self.watcher_start_time.isoformat(),
                'note': 'Files marked as processed include both actually processed files and existing files that were ignored'
            }
            with open(self.processed_log, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving processed files log: {e}")
    
    def get_bucket_files(self) -> List[Dict]:
        """Get list of files currently in the Supabase bucket"""
        try:
            response = self.supabase.storage.from_(self.bucket_name).list()
            
            # Supabase returns a list directly or raises exception on error
            if not isinstance(response, list):
                raise Exception(f"Unexpected response type: {type(response)}")
            
            # Filter for supported file types
            supported_extensions = ['.pdf', '.docx', '.doc']
            files = []
            
            for file_info in response:
                filename = file_info.get('name', '')
                if not filename:
                    continue
                    
                file_ext = Path(filename).suffix.lower()
                
                if file_ext in supported_extensions:
                    metadata = file_info.get('metadata', {})
                    file_size = metadata.get('size', 0) if isinstance(metadata, dict) else 0
                    
                    files.append({
                        'name': filename,
                        'size': file_size,
                        'created_at': file_info.get('created_at'),
                        'updated_at': file_info.get('updated_at'),
                        'last_accessed_at': file_info.get('last_accessed_at')
                    })
            
            return files
            
        except Exception as e:
            print(f"❌ Error listing bucket files: {e}")
            return []
    
    def download_file(self, filename: str) -> Path:
        """Download a file from the bucket to temporary processing folder"""
        try:
            # Download file from bucket - returns bytes directly or raises exception
            file_data = self.supabase.storage.from_(self.bucket_name).download(filename)
            
            if not isinstance(file_data, bytes):
                raise Exception(f"Unexpected download response type: {type(file_data)}")
            
            if len(file_data) == 0:
                raise Exception(f"Downloaded file {filename} is empty")
            
            # Save to temporary file
            temp_file_path = self.temp_dir / filename
            
            with open(temp_file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"📥 Downloaded: {filename} ({len(file_data):,} bytes)")
            return temp_file_path
            
        except Exception as e:
            print(f"❌ Error downloading {filename}: {e}")
            raise
    
    def check_for_new_files(self) -> List[str]:
        """Check bucket for files uploaded after the watcher started"""
        try:
            bucket_files = self.get_bucket_files()
            new_files = []
            
            for file_info in bucket_files:
                filename = file_info['name']
                
                # Skip if already processed or currently processing
                if filename in self.processed_files:
                    continue
                    
                if filename in self.processing_queue:
                    continue
                
                # Check if file was uploaded after watcher started
                file_created_at = file_info.get('created_at')
                if file_created_at:
                    try:
                        # Parse the file creation timestamp
                        # Supabase returns timestamps in ISO format
                        if isinstance(file_created_at, str):
                            file_created_time = datetime.fromisoformat(file_created_at.replace('Z', '+00:00'))
                        else:
                            # If it's already a datetime object
                            file_created_time = file_created_at
                        
                        # Convert to UTC for comparison
                        if file_created_time.tzinfo is None:
                            file_created_time = file_created_time.replace(tzinfo=None)
                            watcher_start_utc = self.watcher_start_time.replace(tzinfo=None)
                        else:
                            file_created_time = file_created_time.astimezone().replace(tzinfo=None)
                            watcher_start_utc = self.watcher_start_time.replace(tzinfo=None)
                        
                        # Only process files uploaded AFTER watcher started
                        if file_created_time > watcher_start_utc:
                            new_files.append(filename)
                            print(f"🆕 Detected newly uploaded file: {filename} (uploaded: {file_created_time})")
                        else:
                            # File existed before watcher started, mark as seen without processing
                            print(f"👀 Existing file detected: {filename} (uploaded: {file_created_time}) - marking as seen")
                            self.processed_files.add(filename)
                            self.save_processed_files()
                            
                    except (ValueError, TypeError) as e:
                        print(f"⚠️  Could not parse timestamp for {filename}: {e}")
                        # If we can't parse timestamp, err on the side of caution and don't process
                        print(f"👀 Marking {filename} as seen due to timestamp parsing issue")
                        self.processed_files.add(filename)
                        self.save_processed_files()
                else:
                    print(f"⚠️  No timestamp available for {filename} - marking as seen")
                    self.processed_files.add(filename)
                    self.save_processed_files()
            
            return new_files
            
        except Exception as e:
            print(f"❌ Error checking for new files: {e}")
            return []
    
    def process_file(self, filename: str):
        """
        Process a single file through the complete pipeline
        
        Args:
            filename: Name of file in the bucket to process
        """
        try:
            # Mark file as being processed
            self.processing_queue.add(filename)
            
            print(f"🔄 Processing {filename}...")
            
            # Download file from bucket
            temp_file_path = self.download_file(filename)
            
            # Create timestamped output filename for parsed results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = filename.replace('.pdf', '').replace('.docx', '').replace('.doc', '')
            output_file = f"data/ParsedFiles/auto_bucket_{timestamp}_{safe_filename}.json"
            
            # Ensure ParsedFiles directory exists
            Path(output_file).parent.mkdir(exist_ok=True)
            
            # Build command to run section_e_parser.py with specific file
            cmd = [
                "python3", "src/parsers/section_e_parser.py",
                "--folder", str(temp_file_path.parent),  # Temp folder
                "--output", output_file,                 # Where to save results
                "--file", filename                       # Specific file to process
            ]
            
            # Execute the parser with timeout
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Successfully parsed {filename}")
                
                # Verify the output file was created
                if os.path.exists(output_file):
                    # Load the parsed results into the database
                    self.load_to_database(output_file)
                    
                    # Mark this file as successfully processed
                    self.processed_files.add(filename)
                    self.save_processed_files()
                    
                    print(f"🎉 Completed processing {filename}")
                else:
                    print(f"⚠️  Output file not found: {output_file}")
                    
            else:
                print(f"❌ Error parsing {filename}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout processing {filename} (took longer than 5 minutes)")
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
        finally:
            # Clean up: remove from processing queue and delete temp file
            self.processing_queue.discard(filename)
            
            # Remove temporary file
            try:
                temp_file_path = self.temp_dir / filename
                if temp_file_path.exists():
                    temp_file_path.unlink()
                    print(f"🗑️  Cleaned up temp file: {filename}")
            except Exception as e:
                print(f"⚠️  Could not clean up temp file {filename}: {e}")
    
    def load_to_database(self, json_file: str):
        """Load parsed results into Supabase database"""
        try:
            print(f"📊 Loading results to database: {json_file}")
            
            # Build command to run supabase_loader_simple.py
            cmd = [
                "python3", "src/database/supabase_loader_simple.py",
                "--input", json_file
            ]
            
            # Execute the database loader
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✅ Successfully loaded to database: {json_file}")
            else:
                print(f"❌ Error loading to database: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout loading to database (took longer than 2 minutes)")
        except Exception as e:
            print(f"❌ Error loading to database: {e}")
    
    def check_trigger_queue(self):
        """Check for trigger files requesting immediate processing"""
        try:
            trigger_files = list(self.trigger_queue_dir.glob("*.trigger"))
            
            for trigger_file in trigger_files:
                try:
                    # Read trigger request
                    with open(trigger_file, 'r') as f:
                        trigger_data = json.load(f)
                    
                    filename = trigger_data.get('filename')
                    timestamp = trigger_data.get('timestamp')
                    
                    if not filename:
                        print(f"⚠️ Invalid trigger file (no filename): {trigger_file}")
                        continue
                    
                    print(f"🔔 Processing trigger request for: {filename}")
                    
                    # Process the specific file immediately
                    self.process_immediate(filename)
                    
                    # Remove the trigger file after processing
                    trigger_file.unlink()
                    
                    print(f"✅ Processed trigger for: {filename}")
                    
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    print(f"⚠️ Error processing trigger {trigger_file}: {e}")
                    # Remove malformed trigger files
                    try:
                        trigger_file.unlink()
                    except:
                        pass
                        
        except Exception as e:
            print(f"❌ Error checking trigger queue: {e}")

    def create_trigger_file(self, filename: str):
        """Create a trigger file to request immediate processing"""
        try:
            trigger_data = {
                'filename': filename,
                'timestamp': datetime.utcnow().isoformat(),
                'created_by': 'external_api'
            }
            
            # Use filename hash to avoid conflicts
            import hashlib
            trigger_id = hashlib.md5(filename.encode()).hexdigest()[:8]
            trigger_file = self.trigger_queue_dir / f"trigger_{trigger_id}.trigger"
            
            with open(trigger_file, 'w') as f:
                json.dump(trigger_data, f, indent=2)
            
            print(f"🔔 Created trigger file for: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating trigger file for {filename}: {e}")
            return False
    
    def start_monitoring(self):
        """Start the bucket monitoring loop with trigger queue checking"""
        print(f"🚀 Starting bucket monitoring...")
        print(f"🔄 Checking bucket every {self.polling_interval} seconds")
        print(f"🔔 Checking trigger queue every 5 seconds")
        print("📋 IMPORTANT: Only files uploaded AFTER this moment will be processed")
        print("📋 Existing files in bucket have been marked as 'seen' and will be ignored")
        print("📋 To process existing files, use --scan-existing flag or trigger queue")
        print("⌨️  Press Ctrl+C to stop\n")
        
        # Track last trigger check time to check more frequently
        last_trigger_check = time.time()
        trigger_check_interval = 5  # Check triggers every 5 seconds
        
        try:
            while True:
                try:
                    current_time = time.time()
                    
                    # Check trigger queue more frequently (every 5 seconds)
                    if current_time - last_trigger_check >= trigger_check_interval:
                        self.check_trigger_queue()
                        last_trigger_check = current_time
                    
                    # Check for new files in bucket at normal interval
                    if current_time % self.polling_interval < trigger_check_interval:
                        new_files = self.check_for_new_files()
                        
                        if new_files:
                            print(f"🆕 Found {len(new_files)} new file(s): {', '.join(new_files)}")
                            
                            # Process each new file in separate threads
                            for filename in new_files:
                                threading.Thread(
                                    target=self.process_file,
                                    args=(filename,),
                                    daemon=True
                                ).start()
                        else:
                            # Only print status every few minutes to avoid spam
                            current_dt = datetime.now()
                            if current_dt.minute % 5 == 0 and current_dt.second < trigger_check_interval:
                                print(f"📝 Status: {len(self.processed_files)} processed, {len(self.processing_queue)} processing")
                    
                    # Sleep for shorter interval to check triggers more frequently
                    time.sleep(trigger_check_interval)
                    
                except KeyboardInterrupt:
                    raise  # Re-raise to exit gracefully
                except Exception as e:
                    print(f"❌ Error in monitoring loop: {e}")
                    print(f"⏳ Waiting {trigger_check_interval} seconds before retry...")
                    time.sleep(trigger_check_interval)
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopping bucket monitoring...")
            print("⏳ Waiting for ongoing processing to complete...")
            
            # Wait for any ongoing processing to complete
            while self.processing_queue:
                print(f"📊 Still processing: {len(self.processing_queue)} files")
                time.sleep(5)
            
            print("✅ All processing completed. Goodbye!")
    
    def process_immediate(self, filename: str):
        """Process a specific file immediately (for webhook/trigger use)"""
        print(f"⚡ Immediate processing requested for: {filename}")
        
        if filename in self.processed_files:
            print(f"⏭️  File {filename} already processed")
            return
            
        if filename in self.processing_queue:
            print(f"⏭️  File {filename} currently being processed")
            return
        
        # Process in separate thread
        threading.Thread(
            target=self.process_file,
            args=(filename,),
            daemon=True
        ).start()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Monitor Supabase bucket for new resume uploads and process them automatically. "
                   "By default, only processes files uploaded AFTER the watcher starts (ignores existing files)."
    )
    parser.add_argument("--bucket", default="msmm-resumes",
                       help="Supabase bucket name to monitor")
    parser.add_argument("--interval", type=int, default=30,
                       help="Polling interval in seconds")
    parser.add_argument("--process-file", 
                       help="Process a specific file immediately and exit")
    parser.add_argument("--scan-existing", action="store_true",
                       help="Process all existing files in bucket that haven't been processed yet. "
                            "Use this if you want to process files that were uploaded before the watcher started.")
    
    args = parser.parse_args()
    
    try:
        # Initialize the watcher
        watcher = SupabaseBucketWatcher(
            bucket_name=args.bucket,
            polling_interval=args.interval
        )
        
        if args.process_file:
            # Process specific file and exit
            watcher.process_immediate(args.process_file)
            print("✅ Immediate processing initiated")
            
        elif args.scan_existing:
            # Process all existing files in bucket
            print("🔍 Scanning bucket for existing files...")
            new_files = watcher.check_for_new_files()
            
            if new_files:
                print(f"📝 Found {len(new_files)} unprocessed files")
                for filename in new_files:
                    watcher.process_immediate(filename)
                print("✅ Processing initiated for all existing files")
            else:
                print("✅ All files in bucket have been processed")
                
        else:
            # Start continuous monitoring
            watcher.start_monitoring()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def trigger_immediate_processing(filename: str) -> bool:
    """
    Helper function to trigger immediate processing of a specific file.
    Can be imported and used by external scripts (like the web server).
    
    Args:
        filename: Name of the file in the bucket to process
        
    Returns:
        bool: True if trigger was created successfully, False otherwise
    """
    try:
        # Create trigger queue directory if it doesn't exist
        trigger_queue_dir = Path("data/trigger_queue")
        trigger_queue_dir.mkdir(exist_ok=True)
        
        trigger_data = {
            'filename': filename,
            'timestamp': datetime.utcnow().isoformat(),
            'created_by': 'external_api'
        }
        
        # Use filename hash to avoid conflicts
        import hashlib
        trigger_id = hashlib.md5(filename.encode()).hexdigest()[:8]
        trigger_file = trigger_queue_dir / f"trigger_{trigger_id}.trigger"
        
        with open(trigger_file, 'w') as f:
            json.dump(trigger_data, f, indent=2)
        
        print(f"🔔 Created trigger file for: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating trigger file for {filename}: {e}")
        return False


if __name__ == "__main__":
    main() 