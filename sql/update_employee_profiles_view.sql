-- =====================================================================
-- UPDATE EMPLOYEE PROFILES VIEW FOR PROPER AGGREGATION
-- =====================================================================
-- This script updates the employee_profiles view to show ONE row per employee
-- with all roles, teams, and projects properly aggregated.
-- 
-- Run this in your Supabase SQL editor to fix the duplicate employee rows.
-- =====================================================================

-- Drop the existing view
DROP VIEW IF EXISTS employee_profiles;

-- Create the new aggregated view
CREATE VIEW employee_profiles AS
WITH employee_aggregated AS (
    SELECT 
        e.employee_id,
        e.employee_name,
        e.total_years_experience,
        e.current_firm_years_experience,
        e.education,
        e.current_professional_registration,
        e.source_filename,
        
        -- Aggregate roles (comma-separated, unique only)
        STRING_AGG(DISTINCT ea.role_in_contract, ', ' ORDER BY ea.role_in_contract) as role_in_contract,
        
        -- Aggregate teams/firms (comma-separated, unique only)
        STRING_AGG(DISTINCT t.firm_name, ', ' ORDER BY t.firm_name) as firm_name,
        
        -- Aggregate qualifications (semicolon-separated, unique only)
        STRING_AGG(DISTINCT ea.other_professional_qualifications, '; ') as other_professional_qualifications,
        
        -- Count total projects across all assignments
        COUNT(DISTINCT ea.project_id) as total_projects
        
    FROM employees e
    LEFT JOIN employee_assignments ea ON e.employee_id = ea.employee_id
    LEFT JOIN teams t ON ea.team_id = t.team_id
    GROUP BY 
        e.employee_id,
        e.employee_name,
        e.total_years_experience,
        e.current_firm_years_experience,
        e.education,
        e.current_professional_registration,
        e.source_filename
)
SELECT 
    employee_id,
    employee_name,
    total_years_experience,
    current_firm_years_experience,
    education,
    current_professional_registration,
    source_filename,
    role_in_contract,
    firm_name,
    other_professional_qualifications,
    total_projects
FROM employee_aggregated;

-- Grant access to the view
GRANT ALL PRIVILEGES ON employee_profiles TO anon, authenticated;

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================
-- After running the above, test with these queries:

-- 1. Check if John Smith now appears as ONE row:
-- SELECT employee_name, role_in_contract, firm_name, total_projects 
-- FROM employee_profiles 
-- WHERE employee_name ILIKE '%john smith%';

-- 2. Verify all employees are properly aggregated:
-- SELECT employee_name, role_in_contract, firm_name, total_projects 
-- FROM employee_profiles 
-- ORDER BY employee_name;

-- 3. Check total count (should be unique employees only):
-- SELECT COUNT(*) as total_unique_employees FROM employee_profiles; 