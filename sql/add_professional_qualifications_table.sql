-- =====================================================================
-- PROFESSIONAL QUALIFICATIONS ENHANCEMENT MIGRATION
-- =====================================================================
-- This migration adds support for storing multiple professional 
-- qualifications from different resumes of the same employee.
--
-- FEATURES:
-- - Individual qualification tracking per resume
-- - Dropdown selection during Section E generation  
-- - Backward compatibility with existing data
-- - Enhanced API support for qualification management
--
-- Run this in your Supabase SQL editor after the schema is already established.
-- =====================================================================

-- =================================================================
-- CREATE PROFESSIONAL QUALIFICATIONS TABLE
-- =================================================================
CREATE TABLE professional_qualifications (
    qualification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    
    -- Qualification content
    current_professional_registration TEXT,
    other_professional_qualifications TEXT,
    
    -- Source tracking
    source_filename TEXT NOT NULL, -- Which resume this came from
    source_type VARCHAR(20) DEFAULT 'resume' CHECK (source_type IN ('resume', 'manual', 'update')),
    
    -- Metadata
    is_primary BOOLEAN DEFAULT FALSE, -- Mark one as primary for display
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure we track source
    CONSTRAINT chk_has_content CHECK (
        current_professional_registration IS NOT NULL OR 
        other_professional_qualifications IS NOT NULL
    )
);

-- =================================================================
-- INDEXES FOR PROFESSIONAL QUALIFICATIONS
-- =================================================================
CREATE INDEX idx_prof_qual_employee_id ON professional_qualifications(employee_id);
CREATE INDEX idx_prof_qual_source ON professional_qualifications(source_filename);
CREATE INDEX idx_prof_qual_primary ON professional_qualifications(employee_id, is_primary) WHERE is_primary = TRUE;

-- Full-text search indexes
CREATE INDEX idx_prof_qual_registration_fts ON professional_qualifications 
    USING GIN(to_tsvector('english', COALESCE(current_professional_registration, '')));
CREATE INDEX idx_prof_qual_other_fts ON professional_qualifications 
    USING GIN(to_tsvector('english', COALESCE(other_professional_qualifications, '')));

-- =================================================================
-- TRIGGER FOR UPDATED_AT
-- =================================================================
CREATE TRIGGER update_professional_qualifications_updated_at 
    BEFORE UPDATE ON professional_qualifications 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =================================================================
-- MIGRATE EXISTING DATA
-- =================================================================
-- Migrate existing professional qualifications from employees table
INSERT INTO professional_qualifications (
    employee_id, 
    current_professional_registration, 
    other_professional_qualifications,
    source_filename,
    source_type,
    is_primary,
    created_at
)
SELECT 
    e.employee_id,
    CASE WHEN e.current_professional_registration IS NOT NULL AND trim(e.current_professional_registration) != '' 
         THEN e.current_professional_registration 
         ELSE NULL END,
    CASE WHEN ea.other_professional_qualifications IS NOT NULL AND trim(ea.other_professional_qualifications) != '' 
         THEN ea.other_professional_qualifications 
         ELSE NULL END,
    COALESCE(e.source_filename, 'legacy_data'),
    'resume',
    TRUE, -- Mark first qualification as primary
    COALESCE(e.created_at, NOW())
FROM employees e
LEFT JOIN employee_assignments ea ON e.employee_id = ea.employee_id
WHERE (e.current_professional_registration IS NOT NULL AND trim(e.current_professional_registration) != '')
   OR (ea.other_professional_qualifications IS NOT NULL AND trim(ea.other_professional_qualifications) != '')
GROUP BY e.employee_id, e.current_professional_registration, e.source_filename, e.created_at, ea.other_professional_qualifications;

-- =================================================================
-- HELPER FUNCTIONS
-- =================================================================

-- Function to get all qualifications for an employee (for API)
CREATE OR REPLACE FUNCTION get_employee_qualifications(p_employee_id UUID)
RETURNS TABLE (
    qualification_id UUID,
    current_professional_registration TEXT,
    other_professional_qualifications TEXT,
    source_filename TEXT,
    is_primary BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pq.qualification_id,
        pq.current_professional_registration,
        pq.other_professional_qualifications,
        pq.source_filename,
        pq.is_primary,
        pq.created_at
    FROM professional_qualifications pq
    WHERE pq.employee_id = p_employee_id
    ORDER BY pq.is_primary DESC, pq.created_at DESC;
END;
$$;

-- Function to set primary qualification for an employee
CREATE OR REPLACE FUNCTION set_primary_qualification(p_employee_id UUID, p_qualification_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    -- First, unset all primary flags for this employee
    UPDATE professional_qualifications 
    SET is_primary = FALSE 
    WHERE employee_id = p_employee_id;
    
    -- Then set the specified qualification as primary
    UPDATE professional_qualifications 
    SET is_primary = TRUE 
    WHERE employee_id = p_employee_id AND qualification_id = p_qualification_id;
    
    RETURN FOUND;
END;
$$;

-- Function to add new qualification entry
CREATE OR REPLACE FUNCTION add_professional_qualification(
    p_employee_id UUID,
    p_current_registration TEXT DEFAULT NULL,
    p_other_qualifications TEXT DEFAULT NULL,
    p_source_filename TEXT DEFAULT 'manual_entry',
    p_source_type TEXT DEFAULT 'manual',
    p_set_as_primary BOOLEAN DEFAULT FALSE
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_qualification_id UUID;
BEGIN
    -- Validate input
    IF p_current_registration IS NULL AND p_other_qualifications IS NULL THEN
        RAISE EXCEPTION 'At least one qualification field must be provided';
    END IF;
    
    -- If setting as primary, unset other primaries first
    IF p_set_as_primary THEN
        UPDATE professional_qualifications 
        SET is_primary = FALSE 
        WHERE employee_id = p_employee_id;
    END IF;
    
    -- Insert new qualification
    INSERT INTO professional_qualifications (
        employee_id,
        current_professional_registration,
        other_professional_qualifications,
        source_filename,
        source_type,
        is_primary
    )
    VALUES (
        p_employee_id,
        p_current_registration,
        p_other_qualifications,
        p_source_filename,
        p_source_type,
        p_set_as_primary
    )
    RETURNING qualification_id INTO v_qualification_id;
    
    RETURN v_qualification_id;
END;
$$;

-- =================================================================
-- UPDATE EMPLOYEE PROFILES VIEW
-- =================================================================
-- Drop the existing view
DROP VIEW IF EXISTS employee_profiles;

-- Recreate with enhanced qualification support
CREATE VIEW employee_profiles AS
WITH employee_aggregated AS (
    SELECT 
        e.employee_id,
        e.employee_name,
        e.total_years_experience,
        e.current_firm_years_experience,
        e.education,
        e.source_filename,
        
        -- Get primary professional qualifications
        pq_primary.current_professional_registration,
        pq_primary.other_professional_qualifications,
        
        -- Count total qualifications available
        COALESCE(pq_count.total_qualifications, 0) as total_qualifications,
        
        -- Aggregate roles (comma-separated, unique only)
        STRING_AGG(DISTINCT ea.role_in_contract, ', ' ORDER BY ea.role_in_contract) as role_in_contract,
        
        -- Aggregate teams/firms (comma-separated, unique only)
        STRING_AGG(DISTINCT t.firm_name, ', ' ORDER BY t.firm_name) as firm_name,
        
        -- Count total projects across all assignments
        COUNT(DISTINCT ea.project_id) as total_projects
        
    FROM employees e
    LEFT JOIN employee_assignments ea ON e.employee_id = ea.employee_id
    LEFT JOIN teams t ON ea.team_id = t.team_id
    LEFT JOIN (
        -- Get primary qualification for each employee
        SELECT DISTINCT ON (employee_id) 
            employee_id,
            current_professional_registration,
            other_professional_qualifications
        FROM professional_qualifications
        ORDER BY employee_id, is_primary DESC, created_at DESC
    ) pq_primary ON e.employee_id = pq_primary.employee_id
    LEFT JOIN (
        -- Count total qualifications per employee
        SELECT 
            employee_id, 
            COUNT(*) as total_qualifications
        FROM professional_qualifications
        GROUP BY employee_id
    ) pq_count ON e.employee_id = pq_count.employee_id
    GROUP BY 
        e.employee_id,
        e.employee_name,
        e.total_years_experience,
        e.current_firm_years_experience,
        e.education,
        e.source_filename,
        pq_primary.current_professional_registration,
        pq_primary.other_professional_qualifications,
        pq_count.total_qualifications
)
SELECT 
    employee_id,
    employee_name,
    total_years_experience,
    current_firm_years_experience,
    education,
    source_filename,
    current_professional_registration,
    other_professional_qualifications,
    total_qualifications,
    role_in_contract,
    firm_name,
    total_projects
FROM employee_aggregated;

-- =================================================================
-- GRANT PERMISSIONS
-- =================================================================
GRANT ALL PRIVILEGES ON professional_qualifications TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_employee_qualifications(UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION set_primary_qualification(UUID, UUID) TO anon, authenticated;  
GRANT EXECUTE ON FUNCTION add_professional_qualification(UUID, TEXT, TEXT, TEXT, TEXT, BOOLEAN) TO anon, authenticated;
GRANT ALL PRIVILEGES ON employee_profiles TO anon, authenticated;

-- =================================================================
-- COMMENTS
-- =================================================================
COMMENT ON TABLE professional_qualifications IS 'Individual professional qualification entries from each resume, enabling version tracking and dropdown selection';
COMMENT ON FUNCTION get_employee_qualifications(UUID) IS 'Retrieve all professional qualifications for a specific employee';
COMMENT ON FUNCTION set_primary_qualification(UUID, UUID) IS 'Set a specific qualification as primary for an employee';
COMMENT ON FUNCTION add_professional_qualification(UUID, TEXT, TEXT, TEXT, TEXT, BOOLEAN) IS 'Add a new professional qualification entry for an employee';

-- =================================================================
-- VERIFICATION QUERIES  
-- =================================================================
-- After running this migration, you can verify with these queries:

-- 1. Check if qualifications were migrated correctly:
-- SELECT employee_name, total_qualifications, current_professional_registration, other_professional_qualifications
-- FROM employee_profiles 
-- WHERE total_qualifications > 0;

-- 2. View all qualifications for a specific employee:
-- SELECT * FROM get_employee_qualifications('your-employee-id-here');

-- 3. Check table structure:
-- \d professional_qualifications;

-- =====================================================================
-- MIGRATION COMPLETE
-- ===================================================================== 