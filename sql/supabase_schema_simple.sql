-- =================================================================
-- Simplified Supabase Schema - 4 Tables Only
-- Standard Form 330 Section E Resume Parser
-- =================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =================================================================
-- TABLE 1: TEAMS (Firms/Companies)
-- =================================================================
CREATE TABLE teams (
    team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_name TEXT NOT NULL,
    location TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Unique constraint for firm-location combinations
CREATE UNIQUE INDEX idx_teams_firm_location ON teams(firm_name, COALESCE(location, ''));

-- =================================================================
-- TABLE 2: EMPLOYEES
-- =================================================================
CREATE TABLE employees (
    employee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_name TEXT NOT NULL,
    total_years_experience INTEGER CHECK (total_years_experience >= 0),
    current_firm_years_experience INTEGER CHECK (current_firm_years_experience >= 0),
    education TEXT,
    current_professional_registration TEXT,
    source_filename TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraint to ensure current firm experience doesn't exceed total
    CONSTRAINT chk_experience_logic CHECK (
        current_firm_years_experience IS NULL OR 
        total_years_experience IS NULL OR 
        current_firm_years_experience <= total_years_experience
    )
);

-- =================================================================
-- TABLE 3: PROJECTS
-- =================================================================
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title_and_location TEXT NOT NULL,
    professional_services_year INTEGER CHECK (professional_services_year >= 1900 AND professional_services_year <= 2100),
    construction_year INTEGER CHECK (construction_year >= 1900 AND construction_year <= 2100),
    description_scope TEXT,
    description_cost TEXT,
    description_fee TEXT,
    description_role TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =================================================================
-- TABLE 4: EMPLOYEE_ASSIGNMENTS (Main Linking Table)
-- Connects employees to teams, projects, and stores role information
-- =================================================================
CREATE TABLE employee_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(team_id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    
    -- Role and qualification information (denormalized)
    role_in_contract TEXT,
    other_professional_qualifications TEXT,
    
    -- Project-specific information
    project_order INTEGER DEFAULT 1, -- Order of projects in resume
    
    -- Metadata
    is_current_assignment BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique employee-project combinations
    UNIQUE(employee_id, project_id)
);

-- =================================================================
-- INDEXES FOR PERFORMANCE
-- =================================================================

-- Foreign key indexes
CREATE INDEX idx_employee_assignments_employee_id ON employee_assignments(employee_id);
CREATE INDEX idx_employee_assignments_team_id ON employee_assignments(team_id);
CREATE INDEX idx_employee_assignments_project_id ON employee_assignments(project_id);

-- Search indexes
CREATE INDEX idx_employees_name ON employees(employee_name);
CREATE INDEX idx_employees_experience ON employees(total_years_experience);
CREATE INDEX idx_teams_firm_name ON teams(firm_name);
CREATE INDEX idx_projects_year_professional ON projects(professional_services_year);
CREATE INDEX idx_projects_year_construction ON projects(construction_year);

-- Full-text search indexes
CREATE INDEX idx_employees_education_fts ON employees USING GIN(to_tsvector('english', COALESCE(education, '')));
CREATE INDEX idx_employees_registration_fts ON employees USING GIN(to_tsvector('english', COALESCE(current_professional_registration, '')));
CREATE INDEX idx_projects_title_fts ON projects USING GIN(to_tsvector('english', title_and_location));
CREATE INDEX idx_projects_scope_fts ON projects USING GIN(to_tsvector('english', COALESCE(description_scope, '')));

-- =================================================================
-- TRIGGERS FOR UPDATED_AT
-- =================================================================

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
CREATE TRIGGER update_teams_updated_at 
    BEFORE UPDATE ON teams 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_employees_updated_at 
    BEFORE UPDATE ON employees 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =================================================================
-- ANALYTICAL VIEWS
-- =================================================================

-- Complete Employee Profile View (Aggregated - One Row Per Employee)
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

-- Project Details View
CREATE VIEW project_details AS
SELECT 
    p.project_id,
    p.title_and_location,
    p.professional_services_year,
    p.construction_year,
    p.description_scope,
    p.description_cost,
    p.description_fee,
    p.description_role,
    e.employee_name,
    e.employee_id,
    t.firm_name,
    ea.project_order,
    ea.role_in_contract
FROM projects p
JOIN employee_assignments ea ON p.project_id = ea.project_id
JOIN employees e ON ea.employee_id = e.employee_id
LEFT JOIN teams t ON ea.team_id = t.team_id
ORDER BY e.employee_name, ea.project_order;

-- Team Analytics View
CREATE VIEW team_analytics AS
SELECT 
    t.team_id,
    t.firm_name,
    t.location,
    COUNT(DISTINCT e.employee_id) as total_employees,
    AVG(e.total_years_experience) as avg_total_experience,
    AVG(e.current_firm_years_experience) as avg_firm_experience,
    COUNT(DISTINCT p.project_id) as total_projects,
    MIN(p.professional_services_year) as earliest_project_year,
    MAX(p.professional_services_year) as latest_project_year
FROM teams t
LEFT JOIN employee_assignments ea ON t.team_id = ea.team_id
LEFT JOIN employees e ON ea.employee_id = e.employee_id
LEFT JOIN projects p ON ea.project_id = p.project_id
GROUP BY t.team_id, t.firm_name, t.location;

-- =================================================================
-- DISABLE RLS (Simplified Approach)
-- =================================================================

-- Disable RLS on all tables to avoid permission issues
ALTER TABLE teams DISABLE ROW LEVEL SECURITY;
ALTER TABLE employees DISABLE ROW LEVEL SECURITY;
ALTER TABLE projects DISABLE ROW LEVEL SECURITY;
ALTER TABLE employee_assignments DISABLE ROW LEVEL SECURITY;

-- Grant permissions to anon and authenticated users
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO anon, authenticated;

-- =================================================================
-- HELPER FUNCTION FOR DATA INSERTION
-- =================================================================

CREATE OR REPLACE FUNCTION insert_employee_complete_simple(
    p_employee_name TEXT,
    p_total_years_experience INTEGER DEFAULT NULL,
    p_current_firm_years_experience INTEGER DEFAULT NULL,
    p_education TEXT DEFAULT NULL,
    p_current_professional_registration TEXT DEFAULT NULL,
    p_firm_name TEXT DEFAULT NULL,
    p_firm_location TEXT DEFAULT NULL,
    p_role_in_contract TEXT DEFAULT NULL,
    p_other_professional_qualifications TEXT DEFAULT NULL,
    p_source_filename TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_team_id UUID;
    v_employee_id UUID;
BEGIN
    -- Insert or get team
    IF p_firm_name IS NOT NULL THEN
        INSERT INTO teams (firm_name, location)
        VALUES (p_firm_name, p_firm_location)
        ON CONFLICT (firm_name, COALESCE(location, '')) DO UPDATE SET
            updated_at = NOW()
        RETURNING team_id INTO v_team_id;
    END IF;

    -- Insert employee
    INSERT INTO employees (
        employee_name, total_years_experience, 
        current_firm_years_experience, education, 
        current_professional_registration, source_filename
    )
    VALUES (
        p_employee_name, p_total_years_experience,
        p_current_firm_years_experience, p_education,
        p_current_professional_registration, p_source_filename
    )
    RETURNING employee_id INTO v_employee_id;

    -- Create base assignment record (even if no projects yet)
    IF v_team_id IS NOT NULL OR p_role_in_contract IS NOT NULL OR p_other_professional_qualifications IS NOT NULL THEN
        INSERT INTO employee_assignments (
            employee_id, team_id, role_in_contract, other_professional_qualifications
        )
        VALUES (
            v_employee_id, v_team_id, p_role_in_contract, p_other_professional_qualifications
        )
        ON CONFLICT DO NOTHING;
    END IF;

    RETURN v_employee_id;
END;
$$;

-- =================================================================
-- COMMENTS
-- =================================================================

COMMENT ON TABLE teams IS 'Firms and companies';
COMMENT ON TABLE employees IS 'Employee information and experience';
COMMENT ON TABLE projects IS 'Project details with description breakdown';
COMMENT ON TABLE employee_assignments IS 'Main linking table connecting employees, teams, projects, and roles';

COMMENT ON VIEW employee_profiles IS 'Complete employee profiles with firm and role information';
COMMENT ON VIEW project_details IS 'Project details with employee and firm context';
COMMENT ON VIEW team_analytics IS 'Team/firm analytics and statistics'; 