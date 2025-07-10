-- =====================================================================
-- ROLE MERGE FUNCTIONS (PER-EMPLOYEE FOCUS)
-- =====================================================================
-- This file contains SQL functions to safely merge and normalize roles
-- stored in comma-separated format within individual employee records.
--
-- FEATURES:
-- - Extract all roles grouped by employee
-- - Find potential duplicate roles within each employee (not across employees)
-- - Merge roles within individual employee records only
-- - Split compound roles within employee records
-- - Normalize role formatting within each employee record
--
-- KEY PRINCIPLE: Role operations are scoped to individual employees
-- to prevent merging roles across different people.
--
-- NOTE: Uses employee_profiles view which aggregates role_in_contract
-- from employee_assignments table.
-- =====================================================================

-- =================================================================
-- DROP EXISTING FUNCTIONS (to allow return type changes)
-- =================================================================
DROP FUNCTION IF EXISTS extract_all_roles();
DROP FUNCTION IF EXISTS find_potential_duplicate_roles(FLOAT);
DROP FUNCTION IF EXISTS split_compound_roles(TEXT, UUID);
DROP FUNCTION IF EXISTS merge_roles(TEXT, TEXT, JSONB);
DROP FUNCTION IF EXISTS get_role_merge_preview(TEXT, TEXT);
DROP FUNCTION IF EXISTS normalize_all_roles();

-- =================================================================
-- FUNCTION: EXTRACT ALL ROLES BY EMPLOYEE
-- =================================================================
CREATE OR REPLACE FUNCTION extract_all_roles()
RETURNS TABLE (
    employee_id UUID,
    employee_name TEXT,
    roles TEXT[],
    role_count INTEGER,
    has_duplicates BOOLEAN
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH employee_roles AS (
        SELECT 
            ep.employee_id,
            ep.employee_name,
            string_to_array(COALESCE(ep.role_in_contract, ''), ',') as raw_roles
        FROM employee_profiles ep
        WHERE ep.role_in_contract IS NOT NULL 
        AND LENGTH(TRIM(ep.role_in_contract)) > 0
    ),
    processed_roles AS (
        SELECT 
            employee_roles.employee_id,
            employee_roles.employee_name,
            ARRAY_AGG(TRIM(role) ORDER BY TRIM(role)) as all_roles,
            ARRAY_AGG(DISTINCT TRIM(role) ORDER BY TRIM(role)) as unique_roles
        FROM employee_roles,
        LATERAL unnest(raw_roles) as role
        WHERE LENGTH(TRIM(role)) > 0
        GROUP BY employee_roles.employee_id, employee_roles.employee_name
    )
    SELECT 
        pr.employee_id,
        pr.employee_name,
        pr.unique_roles as roles,
        array_length(pr.unique_roles, 1) as role_count,
        (array_length(pr.all_roles, 1) > array_length(pr.unique_roles, 1)) as has_duplicates
    FROM processed_roles pr
    ORDER BY pr.employee_name;
END;
$$;

-- =================================================================
-- FUNCTION: FIND POTENTIAL DUPLICATE ROLES PER EMPLOYEE
-- =================================================================
CREATE OR REPLACE FUNCTION find_potential_duplicate_roles(
    p_similarity_threshold FLOAT DEFAULT 0.8
)
RETURNS TABLE (
    employee_id UUID,
    employee_name TEXT,
    role1_name TEXT,
    role2_name TEXT,
    similarity_score FLOAT,
    suggested_primary TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH employee_roles AS (
        SELECT 
            ep.employee_id,
            ep.employee_name,
            TRIM(unnest(string_to_array(
                COALESCE(ep.role_in_contract, ''), ','
            ))) as role_name
        FROM employee_profiles ep
        WHERE ep.role_in_contract IS NOT NULL 
        AND LENGTH(TRIM(ep.role_in_contract)) > 0
    ),
    clean_roles AS (
        SELECT DISTINCT employee_roles.employee_id, employee_roles.employee_name, employee_roles.role_name
        FROM employee_roles
        WHERE LENGTH(employee_roles.role_name) > 0
    ),
    role_pairs AS (
        SELECT 
            r1.employee_id,
            r1.employee_name,
            r1.role_name as role1,
            r2.role_name as role2,
            -- Advanced similarity scoring within same employee
            CASE 
                -- Exact match (case insensitive)
                WHEN LOWER(TRIM(r1.role_name)) = LOWER(TRIM(r2.role_name)) THEN 1.0::FLOAT
                
                -- One contains the other
                WHEN LOWER(TRIM(r1.role_name)) LIKE '%' || LOWER(TRIM(r2.role_name)) || '%' 
                  OR LOWER(TRIM(r2.role_name)) LIKE '%' || LOWER(TRIM(r1.role_name)) || '%' THEN 0.9::FLOAT
                
                -- Similar after removing punctuation and extra spaces
                WHEN LOWER(REGEXP_REPLACE(TRIM(r1.role_name), '[^a-zA-Z0-9 ]', '', 'g')) = 
                     LOWER(REGEXP_REPLACE(TRIM(r2.role_name), '[^a-zA-Z0-9 ]', '', 'g')) THEN 0.85::FLOAT
                
                -- Check for common role patterns (Engineer variants)
                WHEN (LOWER(r1.role_name) LIKE '%engineer%' AND LOWER(r2.role_name) LIKE '%engineer%')
                  OR (LOWER(r1.role_name) LIKE '%manager%' AND LOWER(r2.role_name) LIKE '%manager%')
                  OR (LOWER(r1.role_name) LIKE '%specialist%' AND LOWER(r2.role_name) LIKE '%specialist%') THEN
                    CASE 
                        WHEN LENGTH(r1.role_name) > 5 AND LENGTH(r2.role_name) > 5 AND
                             LOWER(LEFT(r1.role_name, 5)) = LOWER(LEFT(r2.role_name, 5)) THEN 0.8::FLOAT
                        ELSE 0.7::FLOAT
                    END
                
                -- Partial word matches
                WHEN LENGTH(r1.role_name) > 3 AND LENGTH(r2.role_name) > 3 AND (
                    LOWER(r1.role_name) LIKE '%' || LEFT(LOWER(r2.role_name), 4) || '%'
                    OR LOWER(r2.role_name) LIKE '%' || LEFT(LOWER(r1.role_name), 4) || '%'
                ) THEN 0.6::FLOAT
                
                ELSE 0.0::FLOAT
            END as similarity,
            
            -- Determine suggested primary (longer/more complete name)
            CASE 
                WHEN LENGTH(r1.role_name) > LENGTH(r2.role_name) THEN r1.role_name
                ELSE r2.role_name
            END as suggested_primary_role
            
        FROM clean_roles r1
        INNER JOIN clean_roles r2 ON r1.employee_id = r2.employee_id  -- Same employee only
        WHERE r1.role_name < r2.role_name  -- Avoid duplicates and self-comparison
    )
    SELECT 
        rp.employee_id,
        rp.employee_name,
        rp.role1,
        rp.role2,
        rp.similarity,
        rp.suggested_primary_role
    FROM role_pairs rp
    WHERE rp.similarity >= LEAST(p_similarity_threshold, 0.6)
    ORDER BY rp.employee_name, rp.similarity DESC;
END;
$$;

-- =================================================================
-- FUNCTION: MERGE ROLES WITHIN EMPLOYEE (Updated for View)
-- =================================================================
CREATE OR REPLACE FUNCTION merge_roles(
    p_primary_role TEXT,        -- Role to keep
    p_secondary_role TEXT,      -- Role to replace/merge
    p_merge_options JSONB DEFAULT '{}'::JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_affected_employees INTEGER := 0;
    v_role_instances_replaced INTEGER := 0;
    v_final_role TEXT;
    v_result JSONB;
    v_employee_record RECORD;
    v_old_roles TEXT[];
    v_new_roles TEXT[];
    v_updated_role_string TEXT;
    v_target_employee_id UUID;
BEGIN
    -- Extract target employee ID if provided
    v_target_employee_id := (p_merge_options->>'employee_id')::UUID;
    
    -- Determine final role name (allow override via merge options)
    v_final_role := CASE 
        WHEN p_merge_options->>'keep_role_name' = 'secondary' THEN p_secondary_role
        WHEN p_merge_options->>'custom_role_name' IS NOT NULL THEN p_merge_options->>'custom_role_name'
        ELSE p_primary_role
    END;
    
    -- Process employees - update employee_assignments table
    FOR v_employee_record IN 
        SELECT DISTINCT ea.employee_id, ep.employee_name, ea.role_in_contract
        FROM employee_assignments ea
        JOIN employee_profiles ep ON ea.employee_id = ep.employee_id
        WHERE ea.role_in_contract IS NOT NULL
        AND ea.role_in_contract LIKE '%' || p_primary_role || '%' 
        AND ea.role_in_contract LIKE '%' || p_secondary_role || '%'
        AND (v_target_employee_id IS NULL OR ea.employee_id = v_target_employee_id)
    LOOP
        -- Split current roles into array
        v_old_roles := string_to_array(v_employee_record.role_in_contract, ',');
        
        -- Clean, merge, and deduplicate roles within this employee
        SELECT ARRAY_AGG(DISTINCT 
            CASE 
                WHEN TRIM(role) = p_primary_role OR TRIM(role) = p_secondary_role THEN v_final_role
                ELSE TRIM(role)
            END
            ORDER BY 
            CASE 
                WHEN TRIM(role) = p_primary_role OR TRIM(role) = p_secondary_role THEN v_final_role
                ELSE TRIM(role)
            END
        ) INTO v_new_roles
        FROM unnest(v_old_roles) AS role
        WHERE LENGTH(TRIM(role)) > 0;
        
        -- Create updated role string
        v_updated_role_string := array_to_string(v_new_roles, ', ');
        
        -- Update employee_assignments records if changed
        IF v_updated_role_string != v_employee_record.role_in_contract THEN
            UPDATE employee_assignments 
            SET role_in_contract = v_updated_role_string
            WHERE employee_assignments.employee_id = v_employee_record.employee_id
            AND employee_assignments.role_in_contract = v_employee_record.role_in_contract;
            
            v_affected_employees := v_affected_employees + 1;
            v_role_instances_replaced := v_role_instances_replaced + 1;
        END IF;
    END LOOP;
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'primary_role', p_primary_role,
        'secondary_role', p_secondary_role,
        'final_role', v_final_role,
        'employees_affected', v_affected_employees,
        'role_instances_merged', v_role_instances_replaced,
        'target_employee_id', v_target_employee_id,
        'merged_at', NOW()
    );
    
    RETURN v_result;
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'primary_role', p_primary_role,
        'secondary_role', p_secondary_role,
        'target_employee_id', v_target_employee_id
    );
END;
$$;

-- =================================================================
-- FUNCTION: GET ROLE MERGE PREVIEW (PER EMPLOYEE)
-- =================================================================
CREATE OR REPLACE FUNCTION get_role_merge_preview(
    p_primary_role TEXT,
    p_secondary_role TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_affected_employees JSONB[];
    v_employee_record RECORD;
    v_preview JSONB;
    v_total_affected INTEGER := 0;
BEGIN
    -- Get employees that have both roles (the ones that would be affected)
    FOR v_employee_record IN 
        SELECT ep.employee_id, ep.employee_name, ep.role_in_contract
        FROM employee_profiles ep
        WHERE ep.role_in_contract LIKE '%' || p_primary_role || '%'
        AND ep.role_in_contract LIKE '%' || p_secondary_role || '%'
        ORDER BY ep.employee_name
    LOOP
        v_affected_employees := v_affected_employees || jsonb_build_object(
            'employee_id', v_employee_record.employee_id,
            'employee_name', v_employee_record.employee_name,
            'current_roles', string_to_array(v_employee_record.role_in_contract, ','),
            'would_merge', true
        );
        v_total_affected := v_total_affected + 1;
    END LOOP;
    
    -- Build preview
    v_preview := jsonb_build_object(
        'primary_role', p_primary_role,
        'secondary_role', p_secondary_role,
        'merge_scope', 'per_employee',
        'merge_impact', jsonb_build_object(
            'total_affected_employees', v_total_affected,
            'will_merge_into', p_primary_role,
            'affected_employees', COALESCE(v_affected_employees, '[]'::JSONB)
        ),
        'description', 'This will merge duplicate roles within individual employee records only'
    );
    
    RETURN v_preview;
END;
$$;

-- =================================================================
-- FUNCTION: NORMALIZE ROLES PER EMPLOYEE (Updated for View)
-- =================================================================
CREATE OR REPLACE FUNCTION normalize_all_roles()
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_employee_record RECORD;
    v_old_roles TEXT[];
    v_new_roles TEXT[];
    v_updated_role_string TEXT;
    v_employees_updated INTEGER := 0;
    v_total_duplicates_removed INTEGER := 0;
    v_employee_changes JSONB[] := '{}';
BEGIN
    -- Process each employee individually - work with employee_assignments
    FOR v_employee_record IN 
        SELECT DISTINCT ea.employee_id, ep.employee_name, ea.role_in_contract
        FROM employee_assignments ea
        JOIN employee_profiles ep ON ea.employee_id = ep.employee_id
        WHERE ea.role_in_contract IS NOT NULL
        AND LENGTH(TRIM(ea.role_in_contract)) > 0
    LOOP
        -- Split roles and clean them
        v_old_roles := string_to_array(v_employee_record.role_in_contract, ',');
        
        -- Clean, trim, and deduplicate roles within this employee
        SELECT ARRAY_AGG(DISTINCT TRIM(role) ORDER BY TRIM(role)) INTO v_new_roles
        FROM unnest(v_old_roles) AS role
        WHERE LENGTH(TRIM(role)) > 0;
        
        -- Create updated role string
        v_updated_role_string := array_to_string(v_new_roles, ', ');
        
        -- Update if changed
        IF v_updated_role_string != v_employee_record.role_in_contract THEN
            UPDATE employee_assignments 
            SET role_in_contract = v_updated_role_string
            WHERE employee_assignments.employee_id = v_employee_record.employee_id
            AND employee_assignments.role_in_contract = v_employee_record.role_in_contract;
            
            v_employees_updated := v_employees_updated + 1;
            
            DECLARE
                v_duplicates_removed INTEGER;
            BEGIN
                v_duplicates_removed := array_length(v_old_roles, 1) - array_length(v_new_roles, 1);
                v_total_duplicates_removed := v_total_duplicates_removed + v_duplicates_removed;
                
                -- Track changes per employee
                v_employee_changes := v_employee_changes || jsonb_build_object(
                    'employee_id', v_employee_record.employee_id,
                    'employee_name', v_employee_record.employee_name,
                    'old_roles', array_to_json(v_old_roles),
                    'new_roles', array_to_json(v_new_roles),
                    'duplicates_removed', v_duplicates_removed
                );
            END;
        END IF;
    END LOOP;
    
    RETURN jsonb_build_object(
        'success', true,
        'employees_updated', v_employees_updated,
        'total_duplicates_removed', v_total_duplicates_removed,
        'normalized_at', NOW(),
        'scope', 'per_employee',
        'employee_changes', v_employee_changes
    );
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM
    );
END;
$$;

-- =================================================================
-- FUNCTION: SPLIT COMPOUND ROLES (Updated for Assignments Table)
-- =================================================================
CREATE OR REPLACE FUNCTION split_compound_roles(
    p_compound_role TEXT,
    p_employee_id UUID DEFAULT NULL  -- If provided, only affect this employee
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_split_roles TEXT[];
    v_clean_roles TEXT[];
    v_new_role_string TEXT;
    v_affected_count INTEGER := 0;
    v_result JSONB;
BEGIN
    -- Split the compound role on common separators
    v_split_roles := string_to_array(p_compound_role, '/');
    
    -- If no split occurred, try other separators
    IF array_length(v_split_roles, 1) = 1 THEN
        v_split_roles := string_to_array(p_compound_role, '|');
    END IF;
    
    IF array_length(v_split_roles, 1) = 1 THEN
        v_split_roles := string_to_array(p_compound_role, ' & ');
    END IF;
    
    -- Clean and trim each role
    SELECT ARRAY_AGG(TRIM(role)) INTO v_clean_roles
    FROM unnest(v_split_roles) AS role
    WHERE LENGTH(TRIM(role)) > 0;
    
    -- Create new role string
    v_new_role_string := array_to_string(v_clean_roles, ', ');
    
    -- Update employee_assignments records
    IF p_employee_id IS NOT NULL THEN
        -- Update specific employee only
        UPDATE employee_assignments 
        SET role_in_contract = REPLACE(employee_assignments.role_in_contract, p_compound_role, v_new_role_string)
        WHERE employee_assignments.employee_id = p_employee_id
        AND employee_assignments.role_in_contract LIKE '%' || p_compound_role || '%';
        
        GET DIAGNOSTICS v_affected_count = ROW_COUNT;
    ELSE
        -- Update all employees with this compound role
        UPDATE employee_assignments 
        SET role_in_contract = REPLACE(employee_assignments.role_in_contract, p_compound_role, v_new_role_string)
        WHERE employee_assignments.role_in_contract LIKE '%' || p_compound_role || '%';
        
        GET DIAGNOSTICS v_affected_count = ROW_COUNT;
    END IF;
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'original_role', p_compound_role,
        'split_roles', array_to_json(v_clean_roles),
        'new_role_string', v_new_role_string,
        'assignments_affected', v_affected_count,
        'employee_id', p_employee_id
    );
    
    RETURN v_result;
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'original_role', p_compound_role,
        'employee_id', p_employee_id
    );
END;
$$;

-- =================================================================
-- FUNCTION: GET ROLES FOR MERGE (Role-level aggregation)
-- =================================================================
CREATE OR REPLACE FUNCTION get_roles_for_merge()
RETURNS TABLE (
    role_name TEXT,
    employee_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH role_aggregation AS (
        SELECT 
            TRIM(unnest(string_to_array(COALESCE(ep.role_in_contract, ''), ','))) as role_name
        FROM employee_profiles ep
        WHERE ep.role_in_contract IS NOT NULL 
        AND LENGTH(TRIM(ep.role_in_contract)) > 0
    ),
    clean_roles AS (
        SELECT role_aggregation.role_name
        FROM role_aggregation
        WHERE LENGTH(role_aggregation.role_name) > 0
    )
    SELECT 
        cr.role_name,
        COUNT(*)::INTEGER as employee_count
    FROM clean_roles cr
    GROUP BY cr.role_name
    HAVING COUNT(*) > 0
    ORDER BY cr.role_name;
END;
$$;

-- =================================================================
-- GRANTS AND PERMISSIONS
-- =================================================================
GRANT EXECUTE ON FUNCTION extract_all_roles() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_roles_for_merge() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION find_potential_duplicate_roles(FLOAT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION split_compound_roles(TEXT, UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION merge_roles(TEXT, TEXT, JSONB) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_role_merge_preview(TEXT, TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION normalize_all_roles() TO anon, authenticated;

-- =================================================================
-- COMMENTS
-- =================================================================
COMMENT ON FUNCTION extract_all_roles() IS 'Extract all roles grouped by employee';
COMMENT ON FUNCTION get_roles_for_merge() IS 'Get aggregated roles with employee counts for merge interface';
COMMENT ON FUNCTION find_potential_duplicate_roles(FLOAT) IS 'Find roles that might be duplicates within each employee';
COMMENT ON FUNCTION split_compound_roles(TEXT, UUID) IS 'Split compound roles like "Civil Engineer/Engineering Manager" within an employee record';
COMMENT ON FUNCTION merge_roles(TEXT, TEXT, JSONB) IS 'Merge two roles within an individual employee record';
COMMENT ON FUNCTION get_role_merge_preview(TEXT, TEXT) IS 'Preview what a role merge operation would look like within an employee record';
COMMENT ON FUNCTION normalize_all_roles() IS 'Clean and normalize all role data within each employee record, removing duplicates and extra whitespace';

-- =================================================================
-- VERIFICATION QUERIES
-- =================================================================
-- After running this migration, you can test with these queries:

-- 1. Extract all roles:
-- SELECT * FROM extract_all_roles();

-- 2. Find potential duplicates:
-- SELECT * FROM find_potential_duplicate_roles(0.7);

-- 3. Split a compound role:
-- SELECT split_compound_roles('Civil Engineer/Engineering Manager');

-- 4. Preview a role merge:
-- SELECT get_role_merge_preview('Civil Engineer', 'Civil Engineer');

-- 5. Merge roles:
-- SELECT merge_roles('Civil Engineer', 'Civil Engineer', '{"keep_role_name": "primary"}'::jsonb);

-- 6. Normalize all roles:
-- SELECT normalize_all_roles();

-- =====================================================================
-- ROLE MERGE FUNCTIONS COMPLETE
-- ===================================================================== 