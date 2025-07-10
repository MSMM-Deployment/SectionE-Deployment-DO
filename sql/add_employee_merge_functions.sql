-- =====================================================================
-- EMPLOYEE MERGE FUNCTIONS
-- =====================================================================
-- This file contains SQL functions to safely merge employees while
-- preserving all data and maintaining referential integrity.
--
-- FEATURES:
-- - Merge employee basic information with smart field selection
-- - Combine all professional qualifications from both employees
-- - Update all assignments to point to the primary employee
-- - Handle team and project relationships correctly
-- - Safe cleanup of duplicate records
--
-- Run this in your Supabase SQL editor after the professional
-- qualifications table has been created.
-- =====================================================================

-- =================================================================
-- FUNCTION: MERGE TWO EMPLOYEES
-- =================================================================
CREATE OR REPLACE FUNCTION merge_employees(
    p_primary_employee_id UUID,     -- Employee to keep (target)
    p_secondary_employee_id UUID,   -- Employee to merge and remove (source)
    p_merge_options JSONB DEFAULT '{}'::JSONB  -- Merge preferences
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_primary_employee RECORD;
    v_secondary_employee RECORD;
    v_merge_result JSONB := '{}';
    v_assignments_moved INTEGER := 0;
    v_qualifications_moved INTEGER := 0;
    v_duplicates_removed INTEGER := 0;
    v_error_message TEXT;
BEGIN
    -- Validate input parameters
    IF p_primary_employee_id = p_secondary_employee_id THEN
        RAISE EXCEPTION 'Cannot merge employee with itself';
    END IF;
    
    IF p_primary_employee_id IS NULL OR p_secondary_employee_id IS NULL THEN
        RAISE EXCEPTION 'Both employee IDs must be provided';
    END IF;
    
    -- Get employee records
    SELECT * INTO v_primary_employee FROM employees WHERE employee_id = p_primary_employee_id;
    SELECT * INTO v_secondary_employee FROM employees WHERE employee_id = p_secondary_employee_id;
    
    IF v_primary_employee IS NULL THEN
        RAISE EXCEPTION 'Primary employee not found: %', p_primary_employee_id;
    END IF;
    
    IF v_secondary_employee IS NULL THEN
        RAISE EXCEPTION 'Secondary employee not found: %', p_secondary_employee_id;
    END IF;
    
    -- Start transaction-like operations
    BEGIN
        -- Step 1: Merge professional qualifications
        -- Move all qualifications from secondary to primary employee
        UPDATE professional_qualifications 
        SET employee_id = p_primary_employee_id
        WHERE employee_id = p_secondary_employee_id;
        
        GET DIAGNOSTICS v_qualifications_moved = ROW_COUNT;
        
        -- Ensure primary employee has a primary qualification
        -- If primary employee had no qualifications before, set the first moved one as primary
        IF NOT EXISTS (
            SELECT 1 FROM professional_qualifications 
            WHERE employee_id = p_primary_employee_id AND is_primary = TRUE
        ) THEN
            UPDATE professional_qualifications 
            SET is_primary = TRUE 
            WHERE qualification_id = (
                SELECT qualification_id 
                FROM professional_qualifications 
                WHERE employee_id = p_primary_employee_id 
                ORDER BY created_at ASC 
                LIMIT 1
            );
        END IF;
        
        -- Step 2: Handle employee assignments carefully to avoid duplicates
        -- First, delete assignments from secondary employee that would create duplicates
        -- The constraint is on (employee_id, project_id), so we check only project_id
        DELETE FROM employee_assignments 
        WHERE employee_id = p_secondary_employee_id
        AND project_id IN (
            SELECT ea2.project_id
            FROM employee_assignments ea2 
            WHERE ea2.employee_id = p_primary_employee_id
        );
        
        GET DIAGNOSTICS v_duplicates_removed = ROW_COUNT;
        
        -- Then move remaining assignments from secondary to primary employee
        UPDATE employee_assignments 
        SET employee_id = p_primary_employee_id
        WHERE employee_id = p_secondary_employee_id;
        
        GET DIAGNOSTICS v_assignments_moved = ROW_COUNT;
        
        -- Step 3: Merge employee basic information
        -- Use merge options to determine which fields to keep
        UPDATE employees SET
            employee_name = CASE 
                WHEN p_merge_options->>'keep_name' = 'secondary' THEN v_secondary_employee.employee_name
                ELSE COALESCE(employees.employee_name, v_secondary_employee.employee_name)
            END,
            total_years_experience = CASE 
                WHEN p_merge_options->>'keep_experience' = 'secondary' THEN v_secondary_employee.total_years_experience
                WHEN v_secondary_employee.total_years_experience > COALESCE(employees.total_years_experience, 0) THEN v_secondary_employee.total_years_experience
                ELSE employees.total_years_experience
            END,
            current_firm_years_experience = CASE 
                WHEN p_merge_options->>'keep_firm_experience' = 'secondary' THEN v_secondary_employee.current_firm_years_experience
                WHEN v_secondary_employee.current_firm_years_experience > COALESCE(employees.current_firm_years_experience, 0) THEN v_secondary_employee.current_firm_years_experience
                ELSE employees.current_firm_years_experience
            END,
            education = CASE 
                WHEN p_merge_options->>'keep_education' = 'secondary' THEN v_secondary_employee.education
                WHEN LENGTH(COALESCE(v_secondary_employee.education, '')) > LENGTH(COALESCE(employees.education, '')) THEN v_secondary_employee.education
                ELSE COALESCE(employees.education, v_secondary_employee.education)
            END,
            source_filename = employees.source_filename || ', ' || COALESCE(v_secondary_employee.source_filename, ''),
            updated_at = NOW()
        WHERE employee_id = p_primary_employee_id;
        
        -- Step 4: Final cleanup - remove any remaining duplicates based on the actual constraint
        -- The constraint is on (employee_id, project_id), so we deduplicate on those fields
        WITH duplicate_assignments AS (
            SELECT assignment_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY employee_id, project_id
                       ORDER BY assignment_id
                   ) as rn
            FROM employee_assignments 
            WHERE employee_id = p_primary_employee_id
        )
        DELETE FROM employee_assignments 
        WHERE assignment_id IN (
            SELECT assignment_id 
            FROM duplicate_assignments 
            WHERE rn > 1
        );
        
        -- Step 5: Delete the secondary employee record
        DELETE FROM employees WHERE employee_id = p_secondary_employee_id;
        
        -- Build result summary
        v_merge_result := jsonb_build_object(
            'success', true,
            'primary_employee_id', p_primary_employee_id,
            'secondary_employee_id', p_secondary_employee_id,
            'assignments_moved', v_assignments_moved,
            'qualifications_moved', v_qualifications_moved,
            'duplicate_assignments_removed', v_duplicates_removed,
            'merged_at', NOW(),
            'primary_employee_name', v_primary_employee.employee_name,
            'secondary_employee_name', v_secondary_employee.employee_name
        );
        
        RETURN v_merge_result;
        
    EXCEPTION WHEN OTHERS THEN
        -- Rollback will happen automatically due to exception
        v_error_message := SQLERRM;
        RETURN jsonb_build_object(
            'success', false,
            'error', v_error_message,
            'primary_employee_id', p_primary_employee_id,
            'secondary_employee_id', p_secondary_employee_id
        );
    END;
END;
$$;

-- =================================================================
-- FUNCTION: GET MERGE PREVIEW
-- =================================================================
CREATE OR REPLACE FUNCTION get_merge_preview(
    p_primary_employee_id UUID,
    p_secondary_employee_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_primary_employee RECORD;
    v_secondary_employee RECORD;
    v_primary_quals JSONB;
    v_secondary_quals JSONB;
    v_primary_assignments INTEGER;
    v_secondary_assignments INTEGER;
    v_preview JSONB;
BEGIN
    -- Get employee records
    SELECT * INTO v_primary_employee FROM employees WHERE employee_id = p_primary_employee_id;
    SELECT * INTO v_secondary_employee FROM employees WHERE employee_id = p_secondary_employee_id;
    
    IF v_primary_employee IS NULL OR v_secondary_employee IS NULL THEN
        RETURN jsonb_build_object('error', 'One or both employees not found');
    END IF;
    
    -- Get qualifications counts
    SELECT jsonb_agg(
        jsonb_build_object(
            'qualification_id', qualification_id,
            'current_professional_registration', current_professional_registration,
            'other_professional_qualifications', other_professional_qualifications,
            'source_filename', source_filename,
            'is_primary', is_primary
        )
    ) INTO v_primary_quals
    FROM professional_qualifications 
    WHERE employee_id = p_primary_employee_id;
    
    SELECT jsonb_agg(
        jsonb_build_object(
            'qualification_id', qualification_id,
            'current_professional_registration', current_professional_registration,
            'other_professional_qualifications', other_professional_qualifications,
            'source_filename', source_filename,
            'is_primary', is_primary
        )
    ) INTO v_secondary_quals
    FROM professional_qualifications 
    WHERE employee_id = p_secondary_employee_id;
    
    -- Get assignment counts
    SELECT COUNT(*) INTO v_primary_assignments 
    FROM employee_assignments WHERE employee_id = p_primary_employee_id;
    
    SELECT COUNT(*) INTO v_secondary_assignments 
    FROM employee_assignments WHERE employee_id = p_secondary_employee_id;
    
    -- Build preview
    v_preview := jsonb_build_object(
        'primary_employee', jsonb_build_object(
            'employee_id', v_primary_employee.employee_id,
            'employee_name', v_primary_employee.employee_name,
            'total_years_experience', v_primary_employee.total_years_experience,
            'current_firm_years_experience', v_primary_employee.current_firm_years_experience,
            'education', v_primary_employee.education,
            'source_filename', v_primary_employee.source_filename,
            'qualifications', COALESCE(v_primary_quals, '[]'::jsonb),
            'assignments_count', v_primary_assignments
        ),
        'secondary_employee', jsonb_build_object(
            'employee_id', v_secondary_employee.employee_id,
            'employee_name', v_secondary_employee.employee_name,
            'total_years_experience', v_secondary_employee.total_years_experience,
            'current_firm_years_experience', v_secondary_employee.current_firm_years_experience,
            'education', v_secondary_employee.education,
            'source_filename', v_secondary_employee.source_filename,
            'qualifications', COALESCE(v_secondary_quals, '[]'::jsonb),
            'assignments_count', v_secondary_assignments
        ),
        'merge_impact', jsonb_build_object(
            'total_qualifications_after_merge', 
                COALESCE(jsonb_array_length(v_primary_quals), 0) + COALESCE(jsonb_array_length(v_secondary_quals), 0),
            'total_assignments_after_merge', 
                v_primary_assignments + v_secondary_assignments,
            'will_delete_employee_id', p_secondary_employee_id
        )
    );
    
    RETURN v_preview;
END;
$$;

-- =================================================================
-- FUNCTION: FIND POTENTIAL DUPLICATES
-- =================================================================
CREATE OR REPLACE FUNCTION find_potential_duplicate_employees(
    p_similarity_threshold FLOAT DEFAULT 0.8
)
RETURNS TABLE (
    employee1_id UUID,
    employee1_name TEXT,
    employee2_id UUID,
    employee2_name TEXT,
    similarity_score FLOAT,
    common_projects INTEGER,
    suggested_primary UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH employee_pairs AS (
        SELECT 
            e1.employee_id as emp1_id,
            e1.employee_name as emp1_name,
            e2.employee_id as emp2_id,
            e2.employee_name as emp2_name,
            -- Simple similarity based on name matching (simplified version)
            CASE 
                WHEN LOWER(e1.employee_name) = LOWER(e2.employee_name) THEN 1.0::FLOAT
                -- Check if one name contains the other (fuzzy matching)
                WHEN LOWER(e1.employee_name) LIKE '%' || LOWER(e2.employee_name) || '%' 
                  OR LOWER(e2.employee_name) LIKE '%' || LOWER(e1.employee_name) || '%' THEN 0.8::FLOAT
                -- Check for common patterns: remove punctuation and compare
                WHEN LOWER(REGEXP_REPLACE(e1.employee_name, '[^a-zA-Z0-9 ]', '', 'g')) = 
                     LOWER(REGEXP_REPLACE(e2.employee_name, '[^a-zA-Z0-9 ]', '', 'g')) THEN 0.9::FLOAT
                -- Check if names are very similar (at least 3 characters in common)
                WHEN LENGTH(e1.employee_name) > 3 AND LENGTH(e2.employee_name) > 3 AND (
                    LOWER(e1.employee_name) LIKE '%' || LEFT(LOWER(e2.employee_name), 3) || '%'
                    OR LOWER(e2.employee_name) LIKE '%' || LEFT(LOWER(e1.employee_name), 3) || '%'
                ) THEN 0.7::FLOAT
                ELSE 0.0::FLOAT
            END as name_similarity,
            -- Count shared projects
            (SELECT COUNT(DISTINCT p.project_id)
             FROM employee_assignments ea1
             JOIN employee_assignments ea2 ON ea1.project_id = ea2.project_id
             JOIN projects p ON ea1.project_id = p.project_id
             WHERE ea1.employee_id = e1.employee_id 
             AND ea2.employee_id = e2.employee_id) as shared_projects,
            -- Suggest primary based on more complete data
            CASE 
                WHEN COALESCE(e1.total_years_experience, 0) > COALESCE(e2.total_years_experience, 0) THEN e1.employee_id
                WHEN LENGTH(COALESCE(e1.education, '')) > LENGTH(COALESCE(e2.education, '')) THEN e1.employee_id
                WHEN e1.created_at < e2.created_at THEN e1.employee_id
                ELSE e2.employee_id
            END as suggested_primary_id
        FROM employees e1
        CROSS JOIN employees e2
        WHERE e1.employee_id < e2.employee_id  -- Avoid duplicates and self-comparison
    )
    SELECT 
        emp1_id,
        emp1_name,
        emp2_id,
        emp2_name,
        name_similarity::FLOAT,
        shared_projects::INTEGER,
        suggested_primary_id
    FROM employee_pairs
    WHERE name_similarity >= LEAST(p_similarity_threshold, 0.7)  -- Use minimum threshold of 0.7 for our custom matching
       OR shared_projects > 0
    ORDER BY name_similarity DESC, shared_projects DESC;
END;
$$;

-- =================================================================
-- GRANTS AND PERMISSIONS
-- =================================================================
GRANT EXECUTE ON FUNCTION merge_employees(UUID, UUID, JSONB) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_merge_preview(UUID, UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION find_potential_duplicate_employees(FLOAT) TO anon, authenticated;

-- =================================================================
-- COMMENTS
-- =================================================================
COMMENT ON FUNCTION merge_employees(UUID, UUID, JSONB) IS 'Safely merge two employees, combining all their data and relationships';
COMMENT ON FUNCTION get_merge_preview(UUID, UUID) IS 'Preview what a merge operation would look like before executing it';
COMMENT ON FUNCTION find_potential_duplicate_employees(FLOAT) IS 'Find employees that might be duplicates based on name similarity and shared projects';

-- =================================================================
-- VERIFICATION QUERIES
-- =================================================================
-- After running this migration, you can test with these queries:

-- 1. Find potential duplicates:
-- SELECT * FROM find_potential_duplicate_employees(0.7);

-- 2. Preview a merge (replace with actual employee IDs):
-- SELECT get_merge_preview('employee-id-1', 'employee-id-2');

-- 3. Perform a merge (replace with actual employee IDs):
-- SELECT merge_employees('primary-employee-id', 'secondary-employee-id', '{"keep_name": "primary"}'::jsonb);

-- =====================================================================
-- MERGE FUNCTIONS COMPLETE
-- ===================================================================== 