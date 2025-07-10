-- =================================================================
-- FUNCTION: FIND POTENTIAL DUPLICATES (CORRECTED VERSION)
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
            -- Simple similarity based on name matching (with explicit FLOAT casting)
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

-- Grant permissions
GRANT EXECUTE ON FUNCTION find_potential_duplicate_employees(FLOAT) TO anon, authenticated;