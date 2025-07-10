#!/usr/bin/env python3
"""
Simplified Supabase Data Loader for Section E Parser

This script loads parsed resume data into the simplified 4-table Supabase schema:
- teams
- employees  
- projects
- employee_assignments

Usage:
python supabase_loader_simple.py --input results.json
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


class SimpleSupabaseLoader:
    """Simplified loader for 4-table schema"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize Supabase client"""
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def insert_team(self, firm_name: str, location: Optional[str] = None) -> Optional[str]:
        """Insert or get team record"""
        try:
            # Try to find existing team
            query = self.supabase.table('teams').select('team_id').eq('firm_name', firm_name)
            if location:
                query = query.eq('location', location)
            else:
                query = query.is_('location', 'null')
            
            result = query.execute()
            
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
            print(f"Error with team {firm_name}: {e}")
            
        return None
    
    def find_employee_by_name(self, employee_name: str) -> Optional[str]:
        """Find existing employee by name (case-insensitive)"""
        try:
            # Use ilike for case-insensitive search
            result = self.supabase.table('employees').select('employee_id').ilike('employee_name', employee_name).execute()
            
            if result.data:
                return result.data[0]['employee_id']
                
        except Exception as e:
            print(f"Error finding employee {employee_name}: {e}")
            
        return None

    def insert_or_update_employee(self, employee_data: Dict[str, Any], source_filename: Optional[str] = None) -> Optional[str]:
        """
        Insert new employee or update existing one with smart merging
        
        This method implements intelligent employee deduplication and data merging:
        - Checks if employee already exists by name
        - If exists, merges new data with existing data (keeping best information)
        - If new, creates fresh employee record
        
        Args:
            employee_data: Parsed employee data from resume
            source_filename: Original PDF filename for tracking
            
        Returns:
            employee_id if successful, None if failed
        """
        employee_name = employee_data.get('name', '').strip()
        if not employee_name:
            print("Warning: Empty employee name, skipping...")
            return None
            
        # Check if this employee already exists in the database
        existing_id = self.find_employee_by_name(employee_name)
        
        if existing_id:
            print(f"   📝 Found existing employee: {employee_name} - merging data...")
            
            # Smart merge: Update existing employee with new information if it's better
            try:
                update_data = {}
                
                # Track multiple source files for audit trail
                current_result = self.supabase.table('employees').select('source_filename').eq('employee_id', existing_id).execute()
                if current_result.data:
                    current_sources = current_result.data[0].get('source_filename', '')
                    # Only add new filename if it's not already tracked
                    if source_filename and source_filename not in current_sources:
                        if current_sources:
                            update_data['source_filename'] = f"{current_sources}, {source_filename}"
                        else:
                            update_data['source_filename'] = source_filename
                
                # Smart merge: Update education if new one is more detailed
                education = employee_data.get('education', '').strip()
                if education:
                    current_edu_result = self.supabase.table('employees').select('education').eq('employee_id', existing_id).execute()
                    if current_edu_result.data:
                        current_edu = current_edu_result.data[0].get('education', '')
                        # Keep the longer/more detailed education entry
                        if len(education) > len(current_edu):
                            update_data['education'] = education
                
                # Smart merge: Update professional registration if new one is available/better
                registration = employee_data.get('current_professional_registration', '').strip()
                if registration:
                    current_reg_result = self.supabase.table('employees').select('current_professional_registration').eq('employee_id', existing_id).execute()
                    if current_reg_result.data:
                        current_reg = current_reg_result.data[0].get('current_professional_registration', '')
                        # Update if we don't have one or new one is more detailed
                        if not current_reg or len(registration) > len(current_reg):
                            update_data['current_professional_registration'] = registration
                
                # Smart merge: Update experience if new value is higher (more recent resume)
                years_exp = employee_data.get('years_experience', {})
                if isinstance(years_exp, dict):
                    total_exp = years_exp.get('total', '')
                    try:
                        if total_exp and str(total_exp).strip():
                            new_total_exp = int(float(str(total_exp).strip()))
                            current_exp_result = self.supabase.table('employees').select('total_years_experience').eq('employee_id', existing_id).execute()
                            if current_exp_result.data:
                                current_exp = current_exp_result.data[0].get('total_years_experience', 0) or 0
                                # Keep the higher experience value (assumes more recent/accurate)
                                if new_total_exp > int(current_exp):
                                    update_data['total_years_experience'] = str(new_total_exp)
                    except (ValueError, TypeError):
                        # Handle invalid experience values gracefully
                        pass
                
                # Apply updates if any
                if update_data:
                    update_data['processed_at'] = datetime.utcnow().isoformat()
                    self.supabase.table('employees').update(update_data).eq('employee_id', existing_id).execute()
                    print(f"   ✅ Updated employee info: {', '.join(update_data.keys())}")
                
                return existing_id
                
            except Exception as e:
                print(f"Error updating employee {employee_name}: {e}")
                return existing_id  # Return existing ID even if update failed
        
        else:
            # Create new employee
            print(f"   👤 Creating new employee: {employee_name}")
            return self.insert_employee(employee_data, source_filename)

    def insert_employee(self, employee_data: Dict[str, Any], source_filename: Optional[str] = None) -> Optional[str]:
        """Insert new employee record (internal method)"""
        try:
            # Prepare employee data
            emp_data = {
                'employee_name': employee_data.get('name', ''),
                'education': employee_data.get('education', '') or '',
                'current_professional_registration': employee_data.get('current_professional_registration', '') or '',
                'source_filename': source_filename or '',
                'processed_at': datetime.utcnow().isoformat()
            }
            
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
    
    def find_project_by_title(self, title_and_location: str) -> Optional[str]:
        """Find existing project by title and location (case-insensitive)"""
        try:
            result = self.supabase.table('projects').select('project_id').ilike('title_and_location', title_and_location).execute()
            
            if result.data:
                return result.data[0]['project_id']
                
        except Exception as e:
            print(f"Error finding project {title_and_location}: {e}")
            
        return None

    def insert_or_update_project(self, project_data: Dict[str, Any]) -> Optional[str]:
        """Insert new project or return existing one"""
        title_and_location = project_data.get('title_and_location', '').strip()
        if not title_and_location:
            print("Warning: Empty project title, skipping...")
            return None
            
        # Check if project already exists
        existing_id = self.find_project_by_title(title_and_location)
        
        if existing_id:
            print(f"   🏗️  Found existing project: {title_and_location}")
            return existing_id
        else:
            # Create new project
            print(f"   📋 Creating new project: {title_and_location}")
            return self.insert_project(project_data)

    def insert_project(self, project_data: Dict[str, Any]) -> Optional[str]:
        """Insert new project record (internal method)"""
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
            
            # Handle description - check for nested structure
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
    
    def check_assignment_exists(self, employee_id: str, team_id: Optional[str] = None, 
                              project_id: Optional[str] = None, role_in_contract: Optional[str] = None) -> bool:
        """Check if assignment already exists to avoid duplicates"""
        try:
            query = self.supabase.table('employee_assignments').select('assignment_id').eq('employee_id', employee_id)
            
            if team_id:
                query = query.eq('team_id', team_id)
            else:
                query = query.is_('team_id', 'null')
                
            if project_id:
                query = query.eq('project_id', project_id)
            else:
                query = query.is_('project_id', 'null')
                
            if role_in_contract:
                query = query.eq('role_in_contract', role_in_contract)
            else:
                query = query.is_('role_in_contract', 'null')
            
            result = query.execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error checking assignment: {e}")
            return False

    def create_assignment(self, employee_id: str, team_id: Optional[str] = None, project_id: Optional[str] = None, 
                         role_in_contract: Optional[str] = None, other_qualifications: Optional[str] = None, 
                         project_order: int = 1) -> bool:
        """Create assignment linking employee to team/project with role info"""
        
        # Check if this exact assignment already exists
        if self.check_assignment_exists(employee_id, team_id, project_id, role_in_contract):
            print(f"   ⚠️  Assignment already exists, skipping duplicate...")
            return True  # Return True since the assignment exists
        
        try:
            assignment_data = {
                'employee_id': employee_id
            }
            
            if team_id:
                assignment_data['team_id'] = team_id
            if project_id:
                assignment_data['project_id'] = project_id
            if role_in_contract:
                assignment_data['role_in_contract'] = role_in_contract
            if other_qualifications:
                assignment_data['other_professional_qualifications'] = other_qualifications
            if project_id:  # Only set project order if there's a project
                assignment_data['project_order'] = str(project_order)
            
            result = self.supabase.table('employee_assignments').insert(assignment_data).execute()
            if result.data:
                print(f"   ✅ Created new assignment: {role_in_contract or 'No role'}")
            return bool(result.data)
            
        except Exception as e:
            print(f"Error creating assignment: {e}")
            return False

    def insert_professional_qualification(self, employee_id: str, 
                                        current_registration: Optional[str] = None,
                                        other_qualifications: Optional[str] = None,
                                        source_filename: str = 'unknown.pdf',
                                        set_as_primary: bool = False) -> Optional[str]:
        """
        Insert professional qualification entry for an employee
        
        Args:
            employee_id: Employee ID
            current_registration: Professional registration text
            other_qualifications: Other professional qualifications text
            source_filename: Source resume filename
            set_as_primary: Whether to set this as the primary qualification
            
        Returns:
            qualification_id if successful, None if failed
        """
        try:
            # Skip if no qualification data
            if not current_registration and not other_qualifications:
                return None
                
            # Clean up the values
            current_reg = current_registration.strip() if current_registration else None
            other_qual = other_qualifications.strip() if other_qualifications else None
            
            # Skip if both are empty after cleanup
            if not current_reg and not other_qual:
                return None
            
            # Check if this exact qualification already exists for this employee from this source
            existing_check = self.supabase.table('professional_qualifications').select('qualification_id').eq('employee_id', employee_id).eq('source_filename', source_filename)
            
            if current_reg:
                existing_check = existing_check.eq('current_professional_registration', current_reg)
            else:
                existing_check = existing_check.is_('current_professional_registration', 'null')
                
            if other_qual:
                existing_check = existing_check.eq('other_professional_qualifications', other_qual)
            else:
                existing_check = existing_check.is_('other_professional_qualifications', 'null')
            
            existing_result = existing_check.execute()
            
            if existing_result.data:
                print(f"   ⚠️  Professional qualification already exists for {source_filename}, skipping...")
                return existing_result.data[0]['qualification_id']
            
            # If setting as primary, unset other primaries first
            if set_as_primary:
                try:
                    self.supabase.table('professional_qualifications').update({'is_primary': False}).eq('employee_id', employee_id).execute()
                except Exception as e:
                    print(f"Warning: Could not unset primary flags: {e}")
            
            # Insert new qualification
            qual_data = {
                'employee_id': employee_id,
                'source_filename': source_filename,
                'source_type': 'resume',
                'is_primary': set_as_primary
            }
            
            if current_reg:
                qual_data['current_professional_registration'] = current_reg
            if other_qual:
                qual_data['other_professional_qualifications'] = other_qual
                
            result = self.supabase.table('professional_qualifications').insert(qual_data).execute()
            
            if result.data:
                qualification_id = result.data[0]['qualification_id']
                print(f"   ✅ Added professional qualification from {source_filename}")
                return qualification_id
                
        except Exception as e:
            print(f"Error inserting professional qualification: {e}")
            
        return None
    
    def load_resume_data(self, resume_record: Dict[str, Any]) -> bool:
        """Load a complete resume record into the simplified schema"""
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
            
            # 2. Insert or update employee (smart merging)
            employee_id = self.insert_or_update_employee(data, filename)
            if not employee_id:
                print(f"Failed to insert/update employee for {filename}")
                return False
            
            # 3. Store professional qualifications individually
            current_registration = data.get('current_professional_registration', '')
            other_qualifications = data.get('other_professional_qualifications', '')
            
            # Check if this is the first qualification for this employee (set as primary)
            existing_quals_check = self.supabase.table('professional_qualifications').select('qualification_id').eq('employee_id', employee_id).execute()
            is_first_qualification = len(existing_quals_check.data) == 0
            
            # Insert professional qualification entry
            self.insert_professional_qualification(
                employee_id=employee_id,
                current_registration=current_registration,
                other_qualifications=other_qualifications,
                source_filename=filename,
                set_as_primary=is_first_qualification
            )
            
            # 4. Create base assignment (employee to team and role info)
            role_in_contract = data.get('role_in_contract', '')
            
            # Create base assignment (even without projects) - Note: no longer storing qualifications here
            self.create_assignment(
                employee_id=employee_id,
                team_id=team_id,
                role_in_contract=role_in_contract
            )
            
            # 5. Insert projects and create assignments (with smart deduplication)
            projects = data.get('relevant_projects', [])
            if isinstance(projects, list):
                for i, project in enumerate(projects, 1):
                    if isinstance(project, dict) and project.get('title_and_location'):
                        project_id = self.insert_or_update_project(project)
                        if project_id:
                            # Create assignment linking employee to this project (if not duplicate)
                            self.create_assignment(
                                employee_id=employee_id,
                                team_id=team_id,
                                project_id=project_id,
                                role_in_contract=role_in_contract,
                                project_order=i
                            )
            
            print(f"✅ Successfully loaded {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading resume {resume_record.get('filename', 'unknown')}: {e}")
            return False
    
    def load_json_file(self, json_file_path: str) -> Dict[str, int]:
        """Load entire JSON file from parser output"""
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
            
            print(f"Starting to load {stats['total']} resume records into simplified schema...")
            
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
        description="Load Section E parser results into simplified Supabase schema"
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
        loader = SimpleSupabaseLoader(supabase_url, supabase_key)
        
        # Load data
        stats = loader.load_json_file(args.input)
        
        # Print results
        print(f"\n{'='*50}")
        print("LOADING COMPLETE - SIMPLIFIED SCHEMA")
        print(f"{'='*50}")
        print(f"Total records: {stats['total']}")
        print(f"Successfully loaded: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Skipped (parsing errors): {stats['skipped']}")
        
        if stats['successful'] > 0:
            print(f"\n🎉 Successfully loaded {stats['successful']} resume records into Supabase!")
            print("\nYou can now query your data using:")
            print("- SELECT * FROM employee_profiles;")
            print("- SELECT * FROM project_details;") 
            print("- SELECT * FROM team_analytics;")
        else:
            print("\n⚠️ No records were successfully loaded. Please check your data and try again.")
        
    except Exception as e:
        print(f"Error initializing Supabase connection: {e}")
        print("Please check your credentials and network connection.")


if __name__ == "__main__":
    main() 