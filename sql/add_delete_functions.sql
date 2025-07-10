-- =====================================================================
-- DELETE FUNCTIONS FOR EMPLOYEES AND PROJECTS
-- =====================================================================
-- This file contains SQL functions to safely delete employees and projects
-- with proper cascading and error handling.
--
-- FEATURES:
-- - Safe employee deletion with cascade to all related records
-- - Individual project deletion for specific employee-project assignments
-- - Proper error handling and transaction management
-- - Return detailed information about what was deleted
--
-- Run this in your Supabase SQL editor after the main schema is established.
-- =====================================================================

-- =================================================================
-- FUNCTION: DELETE EMPLOYEE AND ALL RELATED DATA
-- =================================================================
CREATE OR REPLACE FUNCTION delete_employee_complete(
    p_employee_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_employee_record RECORD;
    v_assignments_deleted INTEGER := 0;
    v_qualifications_deleted INTEGER := 0;
    v_projects_affected INTEGER := 0;
    v_error_message TEXT;
BEGIN
    -- Validate employee exists
    SELECT employee_id, employee_name INTO v_employee_record
    FROM employees 
    WHERE employee_id = p_employee_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Employee not found',
            'employee_id', p_employee_id
        );
    END IF;
    
    BEGIN
        -- Step 1: Count and delete professional qualifications
        SELECT COUNT(*) INTO v_qualifications_deleted
        FROM professional_qualifications 
        WHERE employee_id = p_employee_id;
        
        DELETE FROM professional_qualifications 
        WHERE employee_id = p_employee_id;
        
        -- Step 2: Count affected projects and delete assignments
        SELECT COUNT(DISTINCT project_id) INTO v_projects_affected
        FROM employee_assignments 
        WHERE employee_id = p_employee_id;
        
        SELECT COUNT(*) INTO v_assignments_deleted
        FROM employee_assignments 
        WHERE employee_id = p_employee_id;
        
        DELETE FROM employee_assignments 
        WHERE employee_id = p_employee_id;
        
        -- Step 3: Delete the employee record (this will cascade automatically)
        DELETE FROM employees 
        WHERE employee_id = p_employee_id;
        
        -- Build success result
        RETURN jsonb_build_object(
            'success', true,
            'employee_id', p_employee_id,
            'employee_name', v_employee_record.employee_name,
            'assignments_deleted', v_assignments_deleted,
            'qualifications_deleted', v_qualifications_deleted,
            'projects_affected', v_projects_affected,
            'deleted_at', NOW(),
            'message', format('Successfully deleted employee %s and all related data', v_employee_record.employee_name)
        );
        
    EXCEPTION WHEN OTHERS THEN
        -- Rollback will happen automatically due to exception
        v_error_message := SQLERRM;
        RETURN jsonb_build_object(
            'success', false,
            'error', v_error_message,
            'employee_id', p_employee_id,
            'employee_name', v_employee_record.employee_name
        );
    END;
END;
$$;

-- =================================================================
-- FUNCTION: DELETE INDIVIDUAL PROJECT FROM EMPLOYEE
-- =================================================================
CREATE OR REPLACE FUNCTION delete_employee_project(
    p_employee_id UUID,
    p_project_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_employee_record RECORD;
    v_project_record RECORD;
    v_assignment_record RECORD;
    v_other_assignments INTEGER := 0;
    v_error_message TEXT;
BEGIN
    -- Validate employee exists
    SELECT employee_id, employee_name INTO v_employee_record
    FROM employees 
    WHERE employee_id = p_employee_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Employee not found',
            'employee_id', p_employee_id
        );
    END IF;
    
    -- Validate project exists
    SELECT project_id, title_and_location INTO v_project_record
    FROM projects 
    WHERE project_id = p_project_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Project not found',
            'project_id', p_project_id
        );
    END IF;
    
    -- Validate assignment exists
    SELECT assignment_id, role_in_contract INTO v_assignment_record
    FROM employee_assignments 
    WHERE employee_id = p_employee_id AND project_id = p_project_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Assignment between employee and project not found',
            'employee_id', p_employee_id,
            'project_id', p_project_id
        );
    END IF;
    
    BEGIN
        -- Check if other employees are assigned to this project
        SELECT COUNT(*) INTO v_other_assignments
        FROM employee_assignments 
        WHERE project_id = p_project_id AND employee_id != p_employee_id;
        
        -- Delete the specific assignment
        DELETE FROM employee_assignments 
        WHERE employee_id = p_employee_id AND project_id = p_project_id;
        
        -- If no other employees are assigned to this project, delete the project too
        IF v_other_assignments = 0 THEN
            DELETE FROM projects WHERE project_id = p_project_id;
        END IF;
        
        -- Build success result
        RETURN jsonb_build_object(
            'success', true,
            'employee_id', p_employee_id,
            'employee_name', v_employee_record.employee_name,
            'project_id', p_project_id,
            'project_title', v_project_record.title_and_location,
            'assignment_role', v_assignment_record.role_in_contract,
            'project_deleted', (v_other_assignments = 0),
            'other_assignments_remaining', v_other_assignments,
            'deleted_at', NOW(),
            'message', format('Successfully removed %s from project %s', 
                v_employee_record.employee_name, 
                v_project_record.title_and_location)
        );
        
    EXCEPTION WHEN OTHERS THEN
        -- Rollback will happen automatically due to exception
        v_error_message := SQLERRM;
        RETURN jsonb_build_object(
            'success', false,
            'error', v_error_message,
            'employee_id', p_employee_id,
            'project_id', p_project_id
        );
    END;
END;
$$;

-- =================================================================
-- FUNCTION: GET DELETE PREVIEW FOR EMPLOYEE
-- =================================================================
CREATE OR REPLACE FUNCTION get_employee_delete_preview(
    p_employee_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_employee_record RECORD;
    v_stats RECORD;
BEGIN
    -- Get employee information
    SELECT employee_id, employee_name, total_years_experience, 
           education, source_filename INTO v_employee_record
    FROM employees 
    WHERE employee_id = p_employee_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Employee not found',
            'employee_id', p_employee_id
        );
    END IF;
    
    -- Get deletion statistics
    SELECT 
        (SELECT COUNT(*) FROM employee_assignments WHERE employee_id = p_employee_id) as total_assignments,
        (SELECT COUNT(DISTINCT project_id) FROM employee_assignments WHERE employee_id = p_employee_id) as total_projects,
        (SELECT COUNT(*) FROM professional_qualifications WHERE employee_id = p_employee_id) as total_qualifications,
        (SELECT STRING_AGG(DISTINCT p.title_and_location, ', ' ORDER BY p.title_and_location) 
         FROM employee_assignments ea 
         JOIN projects p ON ea.project_id = p.project_id 
         WHERE ea.employee_id = p_employee_id) as project_titles
    INTO v_stats;
    
    RETURN jsonb_build_object(
        'success', true,
        'employee', jsonb_build_object(
            'employee_id', v_employee_record.employee_id,
            'employee_name', v_employee_record.employee_name,
            'total_years_experience', v_employee_record.total_years_experience,
            'education', v_employee_record.education,
            'source_filename', v_employee_record.source_filename
        ),
        'deletion_impact', jsonb_build_object(
            'assignments_to_delete', v_stats.total_assignments,
            'projects_affected', v_stats.total_projects,
            'qualifications_to_delete', v_stats.total_qualifications,
            'project_titles', v_stats.project_titles
        ),
        'warning', 'This action cannot be undone. All assignments, qualifications, and project relationships for this employee will be permanently deleted.'
    );
END;
$$;

-- =================================================================
-- GRANTS AND PERMISSIONS
-- =================================================================
GRANT EXECUTE ON FUNCTION delete_employee_complete(UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION delete_employee_project(UUID, UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_employee_delete_preview(UUID) TO anon, authenticated;

-- =================================================================
-- COMMENTS
-- =================================================================
COMMENT ON FUNCTION delete_employee_complete(UUID) IS 'Safely delete an employee and all related data with proper cascading';
COMMENT ON FUNCTION delete_employee_project(UUID, UUID) IS 'Remove a specific project assignment from an employee';
COMMENT ON FUNCTION get_employee_delete_preview(UUID) IS 'Get preview of what will be deleted when removing an employee'; 