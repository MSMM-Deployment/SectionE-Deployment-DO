-- =====================================================================
-- TEAM MERGE FUNCTIONS
-- =====================================================================
-- This file contains SQL functions to safely merge teams/firms while
-- preserving all data and maintaining referential integrity.
--
-- FEATURES:
-- - Merge team basic information with smart field selection
-- - Update all employee assignments to point to the primary team
-- - Handle employee and project relationships correctly
-- - Safe cleanup of duplicate records
--
-- Run this in your Supabase SQL editor after the basic schema
-- has been created.
-- =====================================================================

-- =================================================================
-- FUNCTION: MERGE TWO TEAMS
-- =================================================================
CREATE OR REPLACE FUNCTION merge_teams(
    p_primary_team_id UUID,     -- Team to keep (target)
    p_secondary_team_id UUID,   -- Team to merge and remove (source)
    p_merge_options JSONB DEFAULT '{}'::JSONB  -- Merge preferences
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_primary_team RECORD;
    v_secondary_team RECORD;
    v_merge_result JSONB := '{}';
    v_assignments_moved INTEGER := 0;
    v_duplicates_removed INTEGER := 0;
    v_error_message TEXT;
BEGIN
    -- Validate input parameters
    IF p_primary_team_id = p_secondary_team_id THEN
        RAISE EXCEPTION 'Cannot merge team with itself';
    END IF;
    
    IF p_primary_team_id IS NULL OR p_secondary_team_id IS NULL THEN
        RAISE EXCEPTION 'Both team IDs must be provided';
    END IF;
    
    -- Get team records
    SELECT * INTO v_primary_team FROM teams WHERE team_id = p_primary_team_id;
    SELECT * INTO v_secondary_team FROM teams WHERE team_id = p_secondary_team_id;
    
    IF v_primary_team IS NULL THEN
        RAISE EXCEPTION 'Primary team not found: %', p_primary_team_id;
    END IF;
    
    IF v_secondary_team IS NULL THEN
        RAISE EXCEPTION 'Secondary team not found: %', p_secondary_team_id;
    END IF;
    
    -- Start transaction-like operations
    BEGIN
        -- Step 1: Handle employee assignments carefully to avoid duplicates
        -- First, delete assignments from secondary team that would create duplicates
        -- The constraint is on (employee_id, project_id), so we need to check both
        DELETE FROM employee_assignments 
        WHERE team_id = p_secondary_team_id
        AND (employee_id, project_id) IN (
            SELECT ea2.employee_id, ea2.project_id
            FROM employee_assignments ea2 
            WHERE ea2.team_id = p_primary_team_id
        );
        
        GET DIAGNOSTICS v_duplicates_removed = ROW_COUNT;
        
        -- Then move remaining assignments from secondary to primary team
        UPDATE employee_assignments 
        SET team_id = p_primary_team_id
        WHERE team_id = p_secondary_team_id;
        
        GET DIAGNOSTICS v_assignments_moved = ROW_COUNT;
        
        -- Step 2: Merge team basic information
        -- Use merge options to determine which fields to keep
        UPDATE teams SET
            firm_name = CASE 
                WHEN p_merge_options->>'keep_firm_name' = 'secondary' THEN v_secondary_team.firm_name
                WHEN LENGTH(COALESCE(v_secondary_team.firm_name, '')) > LENGTH(COALESCE(teams.firm_name, '')) THEN v_secondary_team.firm_name
                ELSE COALESCE(teams.firm_name, v_secondary_team.firm_name)
            END,
            location = CASE 
                WHEN p_merge_options->>'keep_location' = 'secondary' THEN v_secondary_team.location
                WHEN LENGTH(COALESCE(v_secondary_team.location, '')) > LENGTH(COALESCE(teams.location, '')) THEN v_secondary_team.location
                ELSE COALESCE(teams.location, v_secondary_team.location)
            END,
            updated_at = NOW()
        WHERE team_id = p_primary_team_id;
        
        -- Step 3: Final cleanup - remove any remaining duplicates
        -- The constraint is on (employee_id, project_id), so we deduplicate on those fields
        WITH duplicate_assignments AS (
            SELECT assignment_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY employee_id, project_id
                       ORDER BY assignment_id
                   ) as rn
            FROM employee_assignments 
            WHERE team_id = p_primary_team_id
        )
        DELETE FROM employee_assignments 
        WHERE assignment_id IN (
            SELECT assignment_id 
            FROM duplicate_assignments 
            WHERE rn > 1
        );
        
        -- Step 4: Delete the secondary team record
        DELETE FROM teams WHERE team_id = p_secondary_team_id;
        
        -- Build result summary
        v_merge_result := jsonb_build_object(
            'success', true,
            'primary_team_id', p_primary_team_id,
            'secondary_team_id', p_secondary_team_id,
            'assignments_moved', v_assignments_moved,
            'duplicate_assignments_removed', v_duplicates_removed,
            'merged_at', NOW(),
            'primary_team_name', v_primary_team.firm_name,
            'secondary_team_name', v_secondary_team.firm_name
        );
        
        RETURN v_merge_result;
        
    EXCEPTION WHEN OTHERS THEN
        -- Rollback will happen automatically due to exception
        v_error_message := SQLERRM;
        RETURN jsonb_build_object(
            'success', false,
            'error', v_error_message,
            'primary_team_id', p_primary_team_id,
            'secondary_team_id', p_secondary_team_id
        );
    END;
END;
$$;

-- =================================================================
-- FUNCTION: GET TEAM MERGE PREVIEW
-- =================================================================
CREATE OR REPLACE FUNCTION get_team_merge_preview(
    p_primary_team_id UUID,
    p_secondary_team_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_primary_team RECORD;
    v_secondary_team RECORD;
    v_primary_employees INTEGER;
    v_secondary_employees INTEGER;
    v_primary_projects INTEGER;
    v_secondary_projects INTEGER;
    v_preview JSONB;
BEGIN
    -- Get team records
    SELECT * INTO v_primary_team FROM teams WHERE team_id = p_primary_team_id;
    SELECT * INTO v_secondary_team FROM teams WHERE team_id = p_secondary_team_id;
    
    IF v_primary_team IS NULL OR v_secondary_team IS NULL THEN
        RETURN jsonb_build_object('error', 'One or both teams not found');
    END IF;
    
    -- Get employee counts
    SELECT COUNT(DISTINCT employee_id) INTO v_primary_employees 
    FROM employee_assignments WHERE team_id = p_primary_team_id;
    
    SELECT COUNT(DISTINCT employee_id) INTO v_secondary_employees 
    FROM employee_assignments WHERE team_id = p_secondary_team_id;
    
    -- Get project counts
    SELECT COUNT(DISTINCT project_id) INTO v_primary_projects 
    FROM employee_assignments WHERE team_id = p_primary_team_id;
    
    SELECT COUNT(DISTINCT project_id) INTO v_secondary_projects 
    FROM employee_assignments WHERE team_id = p_secondary_team_id;
    
    -- Build preview
    v_preview := jsonb_build_object(
        'primary_team', jsonb_build_object(
            'team_id', v_primary_team.team_id,
            'firm_name', v_primary_team.firm_name,
            'location', v_primary_team.location,
            'created_at', v_primary_team.created_at,
            'employees_count', v_primary_employees,
            'projects_count', v_primary_projects
        ),
        'secondary_team', jsonb_build_object(
            'team_id', v_secondary_team.team_id,
            'firm_name', v_secondary_team.firm_name,
            'location', v_secondary_team.location,
            'created_at', v_secondary_team.created_at,
            'employees_count', v_secondary_employees,
            'projects_count', v_secondary_projects
        ),
        'merge_impact', jsonb_build_object(
            'total_employees_after_merge', 
                v_primary_employees + v_secondary_employees,
            'total_projects_after_merge', 
                v_primary_projects + v_secondary_projects,
            'will_delete_team_id', p_secondary_team_id
        )
    );
    
    RETURN v_preview;
END;
$$;

-- =================================================================
-- FUNCTION: FIND POTENTIAL DUPLICATE TEAMS
-- =================================================================
CREATE OR REPLACE FUNCTION find_potential_duplicate_teams(
    p_similarity_threshold FLOAT DEFAULT 0.8
)
RETURNS TABLE (
    team1_id UUID,
    team1_name TEXT,
    team1_location TEXT,
    team2_id UUID,
    team2_name TEXT,
    team2_location TEXT,
    similarity_score FLOAT,
    common_employees INTEGER,
    common_projects INTEGER,
    suggested_primary UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH team_pairs AS (
        SELECT 
            t1.team_id as team1_id,
            t1.firm_name as team1_name,
            t1.location as team1_location,
            t2.team_id as team2_id,
            t2.firm_name as team2_name,
            t2.location as team2_location,
            -- Simple similarity based on name matching
            CASE 
                WHEN LOWER(t1.firm_name) = LOWER(t2.firm_name) THEN 1.0::FLOAT
                -- Check if one name contains the other (fuzzy matching)
                WHEN LOWER(t1.firm_name) LIKE '%' || LOWER(t2.firm_name) || '%' 
                  OR LOWER(t2.firm_name) LIKE '%' || LOWER(t1.firm_name) || '%' THEN 0.8::FLOAT
                -- Check for common patterns: remove punctuation and compare
                WHEN LOWER(REGEXP_REPLACE(t1.firm_name, '[^a-zA-Z0-9 ]', '', 'g')) = 
                     LOWER(REGEXP_REPLACE(t2.firm_name, '[^a-zA-Z0-9 ]', '', 'g')) THEN 0.9::FLOAT
                -- Check if names are very similar (at least 3 characters in common)
                WHEN LENGTH(t1.firm_name) > 3 AND LENGTH(t2.firm_name) > 3 AND (
                    LOWER(t1.firm_name) LIKE '%' || LEFT(LOWER(t2.firm_name), 3) || '%'
                    OR LOWER(t2.firm_name) LIKE '%' || LEFT(LOWER(t1.firm_name), 3) || '%'
                ) THEN 0.7::FLOAT
                ELSE 0.0::FLOAT
            END as name_similarity,
            -- Count shared employees
            (SELECT COUNT(DISTINCT ea1.employee_id)
             FROM employee_assignments ea1
             JOIN employee_assignments ea2 ON ea1.employee_id = ea2.employee_id
             WHERE ea1.team_id = t1.team_id 
             AND ea2.team_id = t2.team_id) as shared_employees,
            -- Count shared projects
            (SELECT COUNT(DISTINCT ea1.project_id)
             FROM employee_assignments ea1
             JOIN employee_assignments ea2 ON ea1.project_id = ea2.project_id
             WHERE ea1.team_id = t1.team_id 
             AND ea2.team_id = t2.team_id) as shared_projects,
            -- Suggest primary based on more complete data
            CASE 
                WHEN LENGTH(COALESCE(t1.location, '')) > LENGTH(COALESCE(t2.location, '')) THEN t1.team_id
                WHEN t1.created_at < t2.created_at THEN t1.team_id
                ELSE t2.team_id
            END as suggested_primary_id
        FROM teams t1
        CROSS JOIN teams t2
        WHERE t1.team_id < t2.team_id  -- Avoid duplicates and self-comparison
    )
    SELECT 
        team1_id,
        team1_name,
        team1_location,
        team2_id,
        team2_name,
        team2_location,
        name_similarity::FLOAT,
        shared_employees::INTEGER,
        shared_projects::INTEGER,
        suggested_primary_id
    FROM team_pairs
    WHERE name_similarity >= LEAST(p_similarity_threshold, 0.7)  -- Use minimum threshold of 0.7 for our custom matching
       OR shared_employees > 0
       OR shared_projects > 0
    ORDER BY name_similarity DESC, shared_employees DESC, shared_projects DESC;
END;
$$;

-- =================================================================
-- GRANTS AND PERMISSIONS
-- =================================================================
GRANT EXECUTE ON FUNCTION merge_teams(UUID, UUID, JSONB) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_team_merge_preview(UUID, UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION find_potential_duplicate_teams(FLOAT) TO anon, authenticated;

-- =================================================================
-- COMMENTS
-- =================================================================
COMMENT ON FUNCTION merge_teams(UUID, UUID, JSONB) IS 'Safely merge two teams, combining all their data and relationships';
COMMENT ON FUNCTION get_team_merge_preview(UUID, UUID) IS 'Preview what a team merge operation would look like before executing it';
COMMENT ON FUNCTION find_potential_duplicate_teams(FLOAT) IS 'Find teams that might be duplicates based on name similarity and shared employees/projects';

-- =================================================================
-- VERIFICATION QUERIES
-- =================================================================
-- After running this migration, you can test with these queries:

-- 1. Find potential duplicates:
-- SELECT * FROM find_potential_duplicate_teams(0.7);

-- 2. Preview a merge (replace with actual team IDs):
-- SELECT get_team_merge_preview('team-id-1', 'team-id-2');

-- 3. Perform a merge (replace with actual team IDs):
-- SELECT merge_teams('primary-team-id', 'secondary-team-id', '{"keep_firm_name": "primary"}'::jsonb);

-- =====================================================================
-- TEAM MERGE FUNCTIONS COMPLETE
-- ===================================================================== 