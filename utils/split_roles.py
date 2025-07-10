#!/usr/bin/env python3
"""
Role Separator Cleaner for Supabase

This script normalizes role separators in the employee_assignments table
by replacing '/' and '&' characters with commas for consistent formatting.

Usage:
    python clean_role_separators.py

Requirements:
    - supabase-py
    - python-dotenv
    - .env file with SUPABASE_URL and SUPABASE_KEY
"""

import os
import re
from dotenv import load_dotenv
from supabase import create_client, Client


def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Missing Supabase credentials. Please ensure SUPABASE_URL and "
            "SUPABASE_KEY are set in your .env file"
        )
    
    return supabase_url, supabase_key


def create_supabase_client() -> Client:
    """Create and return a Supabase client"""
    supabase_url, supabase_key = load_environment()
    return create_client(supabase_url, supabase_key)


def normalize_role_string(role_string: str) -> str:
    """
    Normalize a role string by replacing separators and cleaning up formatting
    
    Args:
        role_string: The original role string
        
    Returns:
        Cleaned role string with normalized separators
    """
    if not role_string:
        return role_string
    
    # Replace various separators with commas
    # Handle common patterns: '/', '&', ' & ', ' / '
    normalized = role_string
    
    # Replace '&' and variations
    normalized = re.sub(r'\s*&\s*', ', ', normalized)
    
    # Replace '/' and variations  
    normalized = re.sub(r'\s*/\s*', ', ', normalized)
    
    # Clean up multiple commas and spaces
    normalized = re.sub(r',\s*,+', ', ', normalized)  # Multiple commas
    normalized = re.sub(r'\s+,\s*', ', ', normalized)  # Spaces before commas
    normalized = re.sub(r',\s+', ', ', normalized)     # Multiple spaces after commas
    
    # Remove leading/trailing commas and spaces
    normalized = normalized.strip().strip(',').strip()
    
    # Ensure single space after each comma
    normalized = re.sub(r',\s*', ', ', normalized)
    
    return normalized


def get_records_to_update(supabase: Client):
    """
    Get all employee_assignments records that need role_in_contract updates
    
    Args:
        supabase: Supabase client instance
        
    Returns:
        List of records that contain '/' or '&' in role_in_contract
    """
    try:
        # Query for records that contain '/' or '&' in role_in_contract
        response = supabase.table('employee_assignments').select(
            'assignment_id, employee_id, role_in_contract'
        ).or_(
            'role_in_contract.like.%/%,role_in_contract.like.%&%'
        ).execute()
        
        return response.data
    except Exception as e:
        print(f"Error fetching records: {e}")
        return []


def update_role_separators(supabase: Client, dry_run: bool = True):
    """
    Update role separators in employee_assignments table
    
    Args:
        supabase: Supabase client instance
        dry_run: If True, only show what would be changed without updating
    """
    print("🔍 Fetching records with '/' or '&' in role_in_contract...")
    
    records = get_records_to_update(supabase)
    
    if not records:
        print("✅ No records found with '/' or '&' separators. All roles are already normalized!")
        return
    
    print(f"📋 Found {len(records)} records to process")
    
    updates_made = 0
    errors = 0
    
    for i, record in enumerate(records, 1):
        assignment_id = record['assignment_id']
        employee_id = record['employee_id']
        original_role = record['role_in_contract']
        
        if not original_role:
            continue
            
        normalized_role = normalize_role_string(original_role)
        
        # Skip if no change needed
        if original_role == normalized_role:
            continue
        
        print(f"\n{i:3d}. Assignment ID: {assignment_id}")
        print(f"     Employee ID: {employee_id}")
        print(f"     Original:  '{original_role}'")
        print(f"     Normalized: '{normalized_role}'")
        
        if dry_run:
            print("     👀 DRY RUN - No changes made")
            updates_made += 1
        else:
            try:
                # Update the record
                response = supabase.table('employee_assignments').update({
                    'role_in_contract': normalized_role
                }).eq('assignment_id', assignment_id).execute()
                
                if response.data:
                    print("     ✅ Updated successfully")
                    updates_made += 1
                else:
                    print("     ❌ Update failed - no data returned")
                    errors += 1
                    
            except Exception as e:
                print(f"     ❌ Update failed: {e}")
                errors += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"   Records processed: {len(records)}")
    print(f"   Updates {'planned' if dry_run else 'made'}: {updates_made}")
    if not dry_run:
        print(f"   Errors: {errors}")
    
    if dry_run:
        print(f"\n⚠️  This was a DRY RUN. No changes were made to the database.")
        print(f"   To apply these changes, run the script with --apply flag")
    else:
        print(f"\n✅ Role separator cleanup completed!")


def main():
    """Main function"""
    import sys
    
    # Check command line arguments
    dry_run = '--apply' not in sys.argv
    
    if dry_run:
        print("🧪 Running in DRY RUN mode (no changes will be made)")
        print("   Use '--apply' flag to actually make changes\n")
    else:
        print("🚀 Running in APPLY mode (changes will be made to database)\n")
    
    try:
        # Create Supabase client
        print("🔗 Connecting to Supabase...")
        supabase = create_supabase_client()
        print("✅ Connected successfully")
        
        # Update role separators
        update_role_separators(supabase, dry_run=dry_run)
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("   Please check your .env file")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 