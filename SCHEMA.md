# Context Kiwi Database Schema

**Project:** Your Supabase Project  
**Last Exported:** 2025-01-27

## Overview

The database consists of 5 main tables:
- `users` - User accounts
- `directives` - Directive metadata
- `directive_versions` - Versioned directive content
- `runs` - Directive execution history
- `lockfiles` - Version pinning per project

## Tables

### `users`
User accounts and authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Auto-generated UUID |
| `email` | TEXT | UNIQUE, nullable | User email address |
| `username` | TEXT | UNIQUE, NOT NULL | Username |
| `trust_score` | INTEGER | DEFAULT 0 | User trust/reputation score |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `email`
- Unique index on `username`

**Triggers:**
- `users_updated_at` - Auto-updates `updated_at` on UPDATE

---

### `directives`
Metadata for directives (reusable AI prompts/workflows).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Auto-generated UUID |
| `name` | TEXT | UNIQUE, NOT NULL | Directive name (e.g., "bootstrap") |
| `category` | TEXT | NOT NULL | Dynamic category (any name allowed, e.g., "core", "patterns", "workflows", "actions") |
| `subcategory` | TEXT | nullable | Optional nested category (e.g., "api-endpoints", "react-components") |
| `description` | TEXT | nullable | Directive description |
| `author_id` | UUID | FK → `users.id` | Creator of the directive |
| `is_official` | BOOLEAN | DEFAULT false | Whether this is an official directive |
| `download_count` | INTEGER | DEFAULT 0 | Number of times downloaded |
| `quality_score` | NUMERIC | DEFAULT 0 | Quality/reliability score |
| `tech_stack` | JSONB | DEFAULT `[]` | Array of compatible technologies |
| `dependencies` | JSONB | DEFAULT `[]` | Array of `{name, version}` dependency objects |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `name`
- Index on `name` (for lookups)
- Index on `category` (for filtering)
- Index on `subcategory` (for filtering)
- Index on `author_id` (for user queries)

**Triggers:**
- `directives_updated_at` - Auto-updates `updated_at` on UPDATE

**Foreign Keys:**
- `author_id` → `users.id`

---

### `directive_versions`
Versioned content for directives. Each directive can have multiple versions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Auto-generated UUID |
| `directive_id` | UUID | FK → `directives.id`, NOT NULL | Parent directive |
| `version` | TEXT | NOT NULL, CHECK | Semver version (e.g., "1.0.0") |
| `content` | TEXT | NOT NULL | Full directive content (XML/markdown) |
| `content_hash` | TEXT | NOT NULL | SHA256 hash of content (first 16 chars) |
| `changelog` | TEXT | nullable | Version changelog |
| `is_latest` | BOOLEAN | DEFAULT false | Whether this is the latest version |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Version creation timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `(directive_id, version)` - ensures one version per directive
- Index on `directive_id` (for lookups)
- Partial index on `directive_id WHERE is_latest = true` (for latest version queries)

**Foreign Keys:**
- `directive_id` → `directives.id` ON DELETE CASCADE

**Constraints:**
- `version` must match semver format (validated by `is_valid_semver()` function)

---

### `runs`
Execution history for directives. Tracks when directives were run, their inputs/outputs, and results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Auto-generated UUID |
| `directive_name` | TEXT | NOT NULL | Name of directive executed |
| `directive_version` | TEXT | nullable | Version of directive executed |
| `status` | TEXT | NOT NULL, CHECK | One of: `success`, `error`, `partial_success` |
| `duration_sec` | NUMERIC | nullable | Execution duration in seconds |
| `cost_usd` | NUMERIC | nullable | Estimated cost in USD |
| `inputs` | JSONB | nullable | Input parameters passed to directive |
| `outputs` | JSONB | nullable | Outputs/results from execution |
| `error` | TEXT | nullable | Error message if execution failed |
| `user_id` | UUID | FK → `users.id` | User who executed the directive |
| `project_context` | JSONB | nullable | Project context at execution time |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Execution timestamp |

**Indexes:**
- Primary key on `id`
- Index on `directive_name` (for filtering by directive)
- Index on `status` (for filtering by status)
- Index on `user_id` (for user history)
- Index on `created_at DESC` (for recent executions)

**Foreign Keys:**
- `user_id` → `users.id`

---

### `lockfiles`
Version pinning per project. Locks specific directive versions for a project to ensure reproducibility.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Auto-generated UUID |
| `project_hash` | TEXT | NOT NULL | Hash identifying the project |
| `user_id` | UUID | FK → `users.id` | Owner of the lockfile |
| `locked_versions` | JSONB | NOT NULL | Map of directive names to pinned versions |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Lockfile creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Index on `project_hash` (for lookups)
- Index on `user_id` (for user queries)

**Triggers:**
- `lockfiles_updated_at` - Auto-updates `updated_at` on UPDATE

**Foreign Keys:**
- `user_id` → `users.id`

---

## Functions

### `is_valid_semver(version text) → boolean`
Validates that a version string matches semantic versioning format (e.g., "1.0.0", "2.1.3-beta.1").

**Regex Pattern:** `^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$`

Used in CHECK constraint on `directive_versions.version`.

### `update_updated_at() → trigger`
Automatically updates the `updated_at` timestamp when a row is updated.

Used by triggers on:
- `directives`
- `users`
- `lockfiles`

---

## Relationships

```
users (1) ──< (many) directives (author_id)
users (1) ──< (many) runs (user_id)
users (1) ──< (many) lockfiles (user_id)

directives (1) ──< (many) directive_versions (directive_id)
  └─ CASCADE DELETE: deleting a directive deletes all its versions
```

---

## Row Level Security (RLS)

All tables have RLS enabled. Policies are configured separately and are environment-specific, so they are not included in this schema export.

---

## Data Types

- **UUID**: PostgreSQL UUID type (uses `extensions.uuid_generate_v4()`)
- **TEXT**: Variable-length text
- **TIMESTAMPTZ**: Timestamp with timezone
- **JSONB**: Binary JSON (efficient for querying)
- **NUMERIC**: Arbitrary precision numeric
- **BOOLEAN**: True/false

---

## Notes

1. **Semver Validation**: The `directive_versions.version` column uses a custom function to validate semantic versioning format.

2. **Cascade Deletes**: Deleting a directive automatically deletes all its versions.

3. **Latest Version Tracking**: The `is_latest` flag on `directive_versions` tracks the current version. Only one version per directive should have `is_latest = true`.

4. **JSONB Usage**: JSONB is used for flexible schema fields like `tech_stack`, `dependencies`, `inputs`, `outputs`, etc.

5. **Project Hash**: The `lockfiles.project_hash` is used to identify projects uniquely, likely a hash of project path or configuration.
