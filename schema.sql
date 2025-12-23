-- Context Kiwi Database Schema
-- Exported from Supabase project: Your Project Name
-- Generated: 2025-01-27

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Validate semver version format
CREATE OR REPLACE FUNCTION public.is_valid_semver(version text)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
SET search_path TO 'public'
AS $function$
BEGIN
    RETURN version ~ '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$';
END;
$function$;

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

-- ============================================================================
-- TABLES
-- ============================================================================

-- Users table
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    email TEXT UNIQUE,
    username TEXT UNIQUE NOT NULL,
    trust_score INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Directives metadata table
CREATE TABLE public.directives (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,  -- Dynamic category (any name allowed, no CHECK constraint)
    subcategory TEXT,        -- Optional nested category (e.g., 'api-endpoints', 'react-components')
    description TEXT,
    author_id UUID REFERENCES public.users(id),
    is_official BOOLEAN DEFAULT false,
    download_count INTEGER DEFAULT 0,
    quality_score NUMERIC DEFAULT 0,
    tech_stack JSONB DEFAULT '[]'::jsonb,
    dependencies JSONB DEFAULT '[]'::jsonb,  -- Array of {name, version} objects for directive dependencies
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Directive versions table (stores versioned content)
CREATE TABLE public.directive_versions (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    directive_id UUID NOT NULL REFERENCES public.directives(id) ON DELETE CASCADE,
    version TEXT NOT NULL CHECK (is_valid_semver(version)),
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    changelog TEXT,
    is_latest BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(directive_id, version)
);

-- Execution runs table (tracks directive executions)
CREATE TABLE public.runs (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    directive_name TEXT NOT NULL,
    directive_version TEXT,
    status TEXT NOT NULL CHECK (status = ANY (ARRAY['success'::text, 'error'::text, 'partial_success'::text])),
    duration_sec NUMERIC,
    cost_usd NUMERIC,
    inputs JSONB,
    outputs JSONB,
    error TEXT,
    user_id UUID REFERENCES public.users(id),
    project_context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lockfiles table (version pinning per project)
CREATE TABLE public.lockfiles (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    project_hash TEXT NOT NULL,
    user_id UUID REFERENCES public.users(id),
    locked_versions JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Users indexes
CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id);
CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email);
CREATE UNIQUE INDEX users_username_key ON public.users USING btree (username);

-- Directives indexes
CREATE UNIQUE INDEX directives_pkey ON public.directives USING btree (id);
CREATE UNIQUE INDEX directives_name_key ON public.directives USING btree (name);
CREATE INDEX idx_directives_name ON public.directives USING btree (name);
CREATE INDEX idx_directives_category ON public.directives USING btree (category);
CREATE INDEX idx_directives_subcategory ON public.directives USING btree (subcategory);
CREATE INDEX idx_directives_author_id ON public.directives USING btree (author_id);

-- Directive versions indexes
CREATE UNIQUE INDEX directive_versions_pkey ON public.directive_versions USING btree (id);
CREATE UNIQUE INDEX directive_versions_directive_id_version_key ON public.directive_versions USING btree (directive_id, version);
CREATE INDEX idx_directive_versions_directive_id ON public.directive_versions USING btree (directive_id);
CREATE INDEX idx_directive_versions_latest ON public.directive_versions USING btree (directive_id) WHERE (is_latest = true);

-- Runs indexes
CREATE UNIQUE INDEX runs_pkey ON public.runs USING btree (id);
CREATE INDEX idx_runs_directive_name ON public.runs USING btree (directive_name);
CREATE INDEX idx_runs_status ON public.runs USING btree (status);
CREATE INDEX idx_runs_user_id ON public.runs USING btree (user_id);
CREATE INDEX idx_runs_created_at ON public.runs USING btree (created_at DESC);

-- Lockfiles indexes
CREATE UNIQUE INDEX lockfiles_pkey ON public.lockfiles USING btree (id);
CREATE INDEX idx_lockfiles_project_hash ON public.lockfiles USING btree (project_hash);
CREATE INDEX idx_lockfiles_user_id ON public.lockfiles USING btree (user_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at on directives
CREATE TRIGGER directives_updated_at
    BEFORE UPDATE ON public.directives
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Auto-update updated_at on users
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Auto-update updated_at on lockfiles
CREATE TRIGGER lockfiles_updated_at
    BEFORE UPDATE ON public.lockfiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Note: RLS is enabled on all tables. Policies should be configured
-- based on your security requirements. This schema export does not
-- include RLS policies as they are environment-specific.

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.directives ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.directive_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lockfiles ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- NOTES
-- ============================================================================

-- Foreign Key Relationships:
--   directives.author_id -> users.id
--   directive_versions.directive_id -> directives.id (CASCADE DELETE)
--   runs.user_id -> users.id
--   lockfiles.user_id -> users.id

-- Key Constraints:
--   - directive_versions: UNIQUE(directive_id, version) - ensures one version per directive
--   - directives.name: UNIQUE - directive names must be unique
--   - users.email: UNIQUE (nullable)
--   - users.username: UNIQUE NOT NULL

-- Check Constraints:
--   - directives.category: dynamic (any category name allowed, no CHECK constraint)
--   - directive_versions.version: must be valid semver (via is_valid_semver function)
--   - runs.status: must be one of ['success', 'error', 'partial_success']

-- JSONB Fields:
--   - directives.tech_stack: Array of technology tags
--   - directives.dependencies: Array of {name, version} objects
--   - runs.inputs: Execution inputs
--   - runs.outputs: Execution outputs
--   - runs.project_context: Project context at execution time
--   - lockfiles.locked_versions: Map of directive names to pinned versions
