#!/usr/bin/env python3
"""
Automatic Resume Parser Watcher

This script monitors the Sample-SectionE folder for new PDF files and automatically:
1. Runs section_e_parser.py on new files only
2. Loads parsed results into Supabase database
3. Maintains a log of processed files

Requirements:
pip install watchdog

Usage:
python3 auto_parser_watcher.py
"""

import os
import json
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

class ResumeParserHandler(FileSystemEventHandler):
    """File system event handler for automatic resume parsing"""
    
    def __init__(self, watch_folder="data/Sample-SectionE", processed_log="processed_files.json"):
        self.watch_folder = Path(watch_folder)
        self.processed_log = Path(processed_log)
        self.processed_files = self.load_processed_files()
        self.processing_queue = set()  # Track files currently being processed
        
        # Ensure watch folder exists
        self.watch_folder.mkdir(exist_ok=True)
        
        print(f"📁 Monitoring folder: {self.watch_folder.absolute()}")
        print(f"📝 Processed files log: {self.processed_log.absolute()}")
        print(f"✅ Already processed: {len(self.processed_files)} files")
    
    def load_processed_files(self):
        """Load list of already processed files"""
        if self.processed_log.exists():
            try:
                with open(self.processed_log, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_files', []))
            except (json.JSONDecodeError, KeyError):
                print("⚠️  Warning: Could not load processed files log, starting fresh")
        return set()
    
    def save_processed_files(self):
        """Save list of processed files"""
        try:
            data = {
                'processed_files': list(self.processed_files),
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.processed_log, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving processed files log: {e}")
    
    def is_pdf_file(self, file_path):
        """Check if file is a PDF"""
        return file_path.suffix.lower() == '.pdf'
    
    def is_already_processed(self, filename):
        """Check if file has already been processed"""
        return filename in self.processed_files
    
    def is_currently_processing(self, filename):
        """Check if file is currently being processed"""
        return filename in self.processing_queue
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Only process PDF files
        if not self.is_pdf_file(file_path):
            return
            
        filename = file_path.name
        
        # Skip if already processed or currently processing
        if self.is_already_processed(filename):
            print(f"⏭️  Skipping {filename} (already processed)")
            return
            
        if self.is_currently_processing(filename):
            print(f"⏭️  Skipping {filename} (currently processing)")
            return
        
        print(f"🆕 New PDF detected: {filename}")
        
        # Add small delay to ensure file is fully written
        time.sleep(2)
        
        # Process the file in a separate thread to avoid blocking the watcher
        threading.Thread(
            target=self.process_file,
            args=(file_path,),
            daemon=True
        ).start()
    
    def process_file(self, file_path):
        """
        Process a single PDF file through the complete pipeline
        
        This method handles the full processing workflow:
        1. Marks file as being processed (prevents duplicate processing)
        2. Runs section_e_parser.py on the single file
        3. Loads the parsed results into Supabase database
        4. Updates the processed files log
        5. Cleans up processing state
        
        Args:
            file_path: Path object pointing to the PDF file to process
        """
        filename = file_path.name
        
        try:
            # Prevent concurrent processing of the same file
            self.processing_queue.add(filename)
            
            print(f"🔄 Processing {filename}...")
            
            # Create timestamped output filename for parsed results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"auto_parsed_{timestamp}_{filename.replace('.pdf', '.json')}"
            
            # Build command to run section_e_parser.py with specific file
            # Uses --file parameter to process only this file, not entire folder
            cmd = [
                "python3", "src/parsers/section_e_parser.py",
                "--folder", str(file_path.parent),  # Folder containing the file
                "--output", output_file,            # Where to save results
                "--file", filename                  # Specific file to process
            ]
            
            # Execute the parser with timeout to prevent hanging
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
            # Always clean up: remove from processing queue to allow retry
            self.processing_queue.discard(filename)
    
    def filter_results_for_file(self, output_file, target_filename):
        """Filter parser results to include only the specific file"""
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            # Filter resumes for our specific file
            filtered_resumes = [
                resume for resume in data.get('resumes', [])
                if resume.get('filename') == target_filename
            ]
            
            if filtered_resumes:
                filtered_data = {
                    'resumes': filtered_resumes,
                    'metadata': {
                        'total_files': 1,
                        'successful': 1 if 'error' not in filtered_resumes[0] else 0,
                        'failed': 1 if 'error' in filtered_resumes[0] else 0,
                        'processed_at': datetime.utcnow().isoformat(),
                        'auto_processed': True,
                        'original_file': target_filename
                    }
                }
                
                # Save filtered results
                filtered_filename = f"filtered_{output_file}"
                with open(filtered_filename, 'w') as f:
                    json.dump(filtered_data, f, indent=2)
                
                return filtered_filename
            
        except Exception as e:
            print(f"❌ Error filtering results: {e}")
        
        return None
    
    def load_to_database(self, json_file):
        """Load parsed results into Supabase database"""
        try:
            print(f"📊 Loading {json_file} into database...")
            
            cmd = [
                "python3", "src/database/supabase_loader_simple.py",
                "--input", json_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ Successfully loaded into database")
                print(f"📈 Database output: {result.stdout.strip()}")
            else:
                print(f"❌ Error loading to database: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout loading to database")
        except Exception as e:
            print(f"❌ Error loading to database: {e}")
    
    def scan_existing_files(self):
        """Scan for existing unprocessed files on startup"""
        print(f"🔍 Scanning for existing unprocessed files...")
        
        pdf_files = list(self.watch_folder.glob("*.pdf"))
        unprocessed = [f for f in pdf_files if f.name not in self.processed_files]
        
        if unprocessed:
            print(f"📋 Found {len(unprocessed)} unprocessed files:")
            for file_path in unprocessed:
                print(f"   - {file_path.name}")
            
            response = input(f"\n❓ Process {len(unprocessed)} existing files now? (y/n): ").lower()
            if response == 'y':
                for file_path in unprocessed:
                    print(f"\n🔄 Processing existing file: {file_path.name}")
                    self.process_file(file_path)
                    time.sleep(1)  # Small delay between files
        else:
            print("✅ All existing files have been processed")


def main():
    """Main function to start the file watcher"""
    load_dotenv()
    
    print("🤖 AUTOMATIC RESUME PARSER WATCHER")
    print("=" * 50)
    
    # Check if required environment variables are set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set in environment")
        print("Please add your OpenAI API key to the .env file")
        return
    
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        print("⚠️  Warning: Supabase credentials not set")
        print("Database loading will be skipped")
    
    # Create the event handler and observer
    event_handler = ResumeParserHandler()
    observer = Observer()
    observer.schedule(event_handler, str(event_handler.watch_folder), recursive=False)
    
    # Scan for existing files
    event_handler.scan_existing_files()
    
    # Start watching
    observer.start()
    print(f"\n👀 Started watching {event_handler.watch_folder}...")
    print("📁 Drop new PDF files into the folder to auto-process them")
    print("⌨️  Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping file watcher...")
        observer.stop()
    
    observer.join()
    print("👋 File watcher stopped")


if __name__ == "__main__":
    main() 