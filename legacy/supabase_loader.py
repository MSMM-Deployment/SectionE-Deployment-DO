#!/usr/bin/env python3
"""
Supabase Data Loader for Section E Parser Results

This script takes the JSON output from section_e_parser.py and loads it into a Supabase database
using the OLAP schema. It handles all the relationships and data normalization.

Requirements:
- SUPABASE_URL and SUPABASE_KEY environment variables
- pip install supabase

Usage:
python supabase_loader.py --input results.json
"""

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("Missing required package. Please install: pip install supabase")
    exit(1)


class SupabaseLoader:
    """Loads parsed resume data into Supabase database"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize Supabase client
        
        Args:
            supabase_url (str): Supabase project URL
            supabase_key (str): Supabase anon/service key
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def insert_team(self, firm_name: str, location: str = None) -> Optional[str]:
        """
        Insert or get team record
        
        Args:
            firm_name (str): Firm name
            location (str): Firm location
            
        Returns:
            Optional[str]: Team ID or None if failed
        """
        try:
            # Check if team already exists
            existing = self.supabase.table('teams').select('team_id').eq('firm_name', firm_name)
            if location:
                existing = existing.eq('location', location)
            
            result = existing.execute()
            
            if result.data:
                return result.data[0]['team_id']
            
            # Insert new team
            team_data = {'firm_name': firm_name}
            if location:
                team_data['location'] = location
                
            result = self.supabase.table('teams').insert(team_data).execute()
            
            if result.data:
                return result.data[0]['team_id']
                
        except Exception as e:
            print(f"Error inserting team {firm_name}: {e}")
            
        return None
    
    def insert_role_description(self, role_in_contract: str = None, other_qualifications: str = None) -> Optional[str]:
        """
        Insert or get role description record
        
        Args:
            role_in_contract (str): Role in contract
            other_qualifications (str): Other professional qualifications
            
        Returns:
            Optional[str]: Role description ID or None if failed
        """
        try:
            # Check if role description already exists
            existing = self.supabase.table('roles_descriptions').select('role_desc_id')
            
            role_filter = role_in_contract if role_in_contract else ''
            qual_filter = other_qualifications if other_qualifications else ''
            
            # Use a combined filter approach
            result = existing.execute()
            
            # Check existing records manually since Supabase doesn't handle NULL comparisons well
            for record in result.data:
                existing_role = record.get('role_in_contract') or ''
                existing_qual = record.get('other_professional_qualifications') or ''
                
                if existing_role == role_filter and existing_qual == qual_filter:
                    return record['role_desc_id']
            
            # Insert new role description if neither field is provided, skip
            if not role_in_contract and not other_qualifications:
                return None
                
            role_data = {}
            if role_in_contract:
                role_data['role_in_contract'] = role_in_contract
            if other_qualifications:
                role_data['other_professional_qualifications'] = other_qualifications
                
            result = self.supabase.table('roles_descriptions').insert(role_data).execute()
            
            if result.data:
                return result.data[0]['role_desc_id']
                
        except Exception as e:
            print(f"Error inserting role description: {e}")
            
        return None
    
    def insert_employee(self, employee_data: Dict[str, Any], team_id: str = None, source_filename: str = None) -> Optional[str]:
        """
        Insert employee record
        
        Args:
            employee_data (Dict): Employee data from parser
            team_id (str): Team ID
            source_filename (str): Source PDF filename
            
        Returns:
            Optional[str]: Employee ID or None if failed
        """
        try:
            # Prepare employee data
            emp_data = {
                'employee_name': employee_data.get('name', ''),
                'education': employee_data.get('education', ''),
                'current_professional_registration': employee_data.get('current_professional_registration', ''),
                'source_filename': source_filename,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Add team reference
            if team_id:
                emp_data['team_id'] = team_id
            
            # Handle years of experience
            years_exp = employee_data.get('years_experience', {})
            if isinstance(years_exp, dict):
                total_exp = years_exp.get('total', '')
                firm_exp = years_exp.get('with_current_firm', '')
                
                # Convert to integers if possible
                try:
                    if total_exp and str(total_exp).strip():
                        emp_data['total_years_experience'] = int(float(str(total_exp).strip()))
                except (ValueError, TypeError):
                    pass
                    
                try:
                    if firm_exp and str(firm_exp).strip():
                        emp_data['current_firm_years_experience'] = int(float(str(firm_exp).strip()))
                except (ValueError, TypeError):
                    pass
            
            # Insert employee
            result = self.supabase.table('employees').insert(emp_data).execute()
            
            if result.data:
                return result.data[0]['employee_id']
                
        except Exception as e:
            print(f"Error inserting employee {employee_data.get('name', 'Unknown')}: {e}")
            
        return None
    
    def insert_project(self, project_data: Dict[str, Any]) -> Optional[str]:
        """
        Insert project record
        
        Args:
            project_data (Dict): Project data from parser
            
        Returns:
            Optional[str]: Project ID or None if failed
        """
        try:
            # Prepare project data
            proj_data = {
                'title_and_location': project_data.get('title_and_location', '')
            }
            
            # Handle year completed
            year_completed = project_data.get('year_completed', {})
            if isinstance(year_completed, dict):
                prof_year = year_completed.get('professional_services', '')
                const_year = year_completed.get('construction', '')
                
                # Convert to integers if possible
                try:
                    if prof_year and str(prof_year).strip():
                        proj_data['professional_services_year'] = int(str(prof_year).strip())
                except (ValueError, TypeError):
                    pass
                    
                try:
                    if const_year and str(const_year).strip():
                        proj_data['construction_year'] = int(str(const_year).strip())
                except (ValueError, TypeError):
                    pass
            
            # Handle description - check for new nested structure
            description = project_data.get('description', '')
            if isinstance(description, dict):
                # New structure with scope, cost, fee, role
                proj_data['description_scope'] = description.get('scope', '')
                proj_data['description_cost'] = description.get('cost', '')
                proj_data['description_fee'] = description.get('fee', '')
                proj_data['description_role'] = description.get('role', '')
            elif isinstance(description, str):
                # Old structure - put everything in scope
                proj_data['description_scope'] = description
            
            # Insert project
            result = self.supabase.table('projects').insert(proj_data).execute()
            
            if result.data:
                return result.data[0]['project_id']
                
        except Exception as e:
            print(f"Error inserting project {project_data.get('title_and_location', 'Unknown')}: {e}")
            
        return None
    
    def link_employee_to_role(self, employee_id: str, role_desc_id: str) -> bool:
        """
        Link employee to role description
        
        Args:
            employee_id (str): Employee ID
            role_desc_id (str): Role description ID
            
        Returns:
            bool: Success status
        """
        try:
            link_data = {
                'employee_id': employee_id,
                'role_desc_id': role_desc_id,
                'is_current': True
            }
            
            result = self.supabase.table('employee_roles').insert(link_data).execute()
            return bool(result.data)
            
        except Exception as e:
            print(f"Error linking employee to role: {e}")
            return False
    
    def link_employee_to_project(self, employee_id: str, project_id: str, project_order: int = 1) -> bool:
        """
        Link employee to project
        
        Args:
            employee_id (str): Employee ID
            project_id (str): Project ID
            project_order (int): Order of project in resume
            
        Returns:
            bool: Success status
        """
        try:
            link_data = {
                'employee_id': employee_id,
                'project_id': project_id,
                'project_order': project_order
            }
            
            result = self.supabase.table('employee_projects').insert(link_data).execute()
            return bool(result.data)
            
        except Exception as e:
            print(f"Error linking employee to project: {e}")
            return False
    
    def load_resume_data(self, resume_record: Dict[str, Any]) -> bool:
        """
        Load a complete resume record into the database
        
        Args:
            resume_record (Dict): Single resume record from parser output
            
        Returns:
            bool: Success status
        """
        try:
            filename = resume_record.get('filename', 'unknown.pdf')
            data = resume_record.get('data', {})
            
            print(f"Loading data for {filename}...")
            
            # 1. Insert team/firm
            team_id = None
            firm_info = data.get('firm_name_and_location', '')
            if firm_info:
                # Try to split firm name and location
                firm_name = firm_info
                location = None
                
                # Simple heuristic to separate name and location
                if ',' in firm_info:
                    parts = firm_info.split(',')
                    if len(parts) >= 2:
                        firm_name = parts[0].strip()
                        location = ','.join(parts[1:]).strip()
                
                team_id = self.insert_team(firm_name, location)
            
            # 2. Insert role description
            role_desc_id = None
            role_in_contract = data.get('role_in_contract', '')
            other_qualifications = data.get('other_professional_qualifications', '')
            
            if role_in_contract or other_qualifications:
                role_desc_id = self.insert_role_description(role_in_contract, other_qualifications)
            
            # 3. Insert employee
            employee_id = self.insert_employee(data, team_id, filename)
            if not employee_id:
                print(f"Failed to insert employee for {filename}")
                return False
            
            # 4. Link employee to role
            if role_desc_id:
                self.link_employee_to_role(employee_id, role_desc_id)
            
            # 5. Insert projects and link to employee
            projects = data.get('relevant_projects', [])
            if isinstance(projects, list):
                for i, project in enumerate(projects, 1):
                    if isinstance(project, dict) and project.get('title_and_location'):
                        project_id = self.insert_project(project)
                        if project_id:
                            self.link_employee_to_project(employee_id, project_id, i)
            
            print(f"✅ Successfully loaded {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading resume {resume_record.get('filename', 'unknown')}: {e}")
            return False
    
    def load_json_file(self, json_file_path: str) -> Dict[str, int]:
        """
        Load entire JSON file from parser output
        
        Args:
            json_file_path (str): Path to JSON file from parser
            
        Returns:
            Dict[str, int]: Statistics of loaded records
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            resumes = data.get('resumes', [])
            
            stats = {
                'total': len(resumes),
                'successful': 0,
                'failed': 0,
                'skipped': 0
            }
            
            print(f"Starting to load {stats['total']} resume records...")
            
            for resume in resumes:
                # Skip records that had errors during parsing
                if 'error' in resume:
                    print(f"Skipping {resume.get('filename', 'unknown')} due to parsing error: {resume['error']}")
                    stats['skipped'] += 1
                    continue
                
                # Load the resume data
                if self.load_resume_data(resume):
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1
            
            return stats
            
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return {'total': 0, 'successful': 0, 'failed': 0, 'skipped': 0}


def main():
    """Main function"""
    load_dotenv()
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description="Load Section E parser results into Supabase database"
    )
    parser.add_argument("--input", required=True, help="Input JSON file from parser")
    parser.add_argument("--supabase-url", help="Supabase URL (overrides environment variable)")
    parser.add_argument("--supabase-key", help="Supabase key (overrides environment variable)")
    
    args = parser.parse_args()
    
    # Get Supabase credentials
    supabase_url = args.supabase_url or os.getenv("SUPABASE_URL")
    supabase_key = args.supabase_key or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found.")
        print("Set SUPABASE_URL and SUPABASE_KEY environment variables or use command line options.")
        return
    
    # Initialize loader
    try:
        loader = SupabaseLoader(supabase_url, supabase_key)
        
        # Load data
        stats = loader.load_json_file(args.input)
        
        # Print results
        print(f"\n{'='*50}")
        print("LOADING COMPLETE")
        print(f"{'='*50}")
        print(f"Total records: {stats['total']}")
        print(f"Successfully loaded: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Skipped (parsing errors): {stats['skipped']}")
        
        if stats['successful'] > 0:
            print(f"\n🎉 Successfully loaded {stats['successful']} resume records into Supabase!")
            print("\nYou can now query your data using the analytical views:")
            print("- employee_profiles")
            print("- project_details") 
            print("- team_analytics")
        else:
            print("\n⚠️ No records were successfully loaded. Please check your data and try again.")
        
    except Exception as e:
        print(f"Error initializing Supabase connection: {e}")
        print("Please check your credentials and network connection.")


if __name__ == "__main__":
    main() 