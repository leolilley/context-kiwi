# Publishing Context Kiwi

## Overview

Three things to set up:
1. **GitHub repo** - Public repository
2. **PyPI package** - `pip install context-kiwi`
3. **Registry backend** - Supabase (current) or proxy API

---

## 1. GitHub Repository

### Create Repo

```bash
# On GitHub: Create new public repo "context-kiwi"

git remote add origin git@github.com:YOUR_USERNAME/context-kiwi.git
git branch -M main
git push -u origin main
```

### Files to Review Before Pushing

| File | Action |
|------|--------|
| `.env` | **DO NOT COMMIT** - add to .gitignore |
| `.cursor/mcp.json` | Remove SUPABASE_SECRET_KEY before committing |
| `pyproject.toml` | Update `project.urls` with real GitHub URLs |

### Recommended: GitHub Actions for PyPI

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

---

## 2. PyPI Publishing

### One-Time Setup

```bash
# Create PyPI account at https://pypi.org/account/register/
# Generate API token at https://pypi.org/manage/account/token/

# Install build tools
pip install build twine
```

### Manual Publish

```bash
# Build
python -m build

# Check the build
twine check dist/*

# Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

### Version Bumping

```bash
# In pyproject.toml, bump version
version = "0.1.0"  →  version = "0.2.0"

# Tag the release
git tag v0.2.0
git push origin v0.2.0
```

---

## 3. Supabase Security Analysis

### Current Setup

```
User's MCP Config:
  SUPABASE_URL = "https://xxx.supabase.co"      # Public (like a hostname)
  SUPABASE_SECRET_KEY = "sb_secret_xxx"         # Private (for publishing)
  # OR
  CONTEXT_KIWI_API_KEY = "xxx"                  # Alternative for publishing
```

### What's Actually Exposed?

| Item | Visibility | Risk |
|------|------------|------|
| Supabase URL | Public | **Low** - Just a hostname, like `api.github.com` |
| Anon Key | Public | **Low** - Designed to be public, like Firebase config |
| Secret Key | Private | **High** - Full DB access, never expose |

### How Supabase Security Works

```
┌─────────────────────────────────────────────────────────────┐
│                        Supabase                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ANON KEY (public)          SERVICE KEY (secret)           │
│   ─────────────────          ───────────────────            │
│   • Read public data         • Full access                  │
│   • Subject to RLS           • Bypasses RLS                 │
│   • Rate limited             • For server-side only         │
│                                                             │
│   Used for:                  Used for:                      │
│   • search()                 • publish()                    │
│   • get()                    • Admin operations             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Current RLS (Row Level Security) Needed

```sql
-- Directives table: Anyone can read
CREATE POLICY "Public read" ON directives FOR SELECT USING (true);

-- Directive versions: Anyone can read
CREATE POLICY "Public read" ON directive_versions FOR SELECT USING (true);

-- Publishing requires auth (handled by service key)
CREATE POLICY "Auth write" ON directives FOR INSERT 
  USING (auth.role() = 'service_role');
```

### Is This Secure Enough?

**For MVP: Yes**
- Supabase URL + anon key is standard (same as Firebase)
- Reading directives is meant to be public
- Writing requires the secret key (which users provide for publishing)

**Concerns:**
- Anyone can see your Supabase project URL
- No rate limiting without additional setup
- No analytics on who's downloading what

---

## 4. Options for Backend

### Option A: Direct Supabase (Current)

```
┌─────────┐     ┌───────────┐
│  User   │────▶│  Supabase │
│   MCP   │◀────│    DB     │
└─────────┘     └───────────┘
```

**Pros:**
- No extra infrastructure
- Free tier is generous
- Already working

**Cons:**
- URL is visible
- No custom analytics
- Can't add custom logic

**Verdict:** Fine for MVP and probably long-term

---

### Option B: Proxy API (Fly.io/Vercel)

```
┌─────────┐     ┌───────────┐     ┌───────────┐
│  User   │────▶│   Proxy   │────▶│  Supabase │
│   MCP   │◀────│    API    │◀────│    DB     │
└─────────┘     └───────────┘     └───────────┘
```

**Pros:**
- Hide Supabase entirely
- Add rate limiting, analytics
- Custom validation logic

**Cons:**
- More infrastructure to maintain
- Added latency
- Costs money at scale

**When to add:**
- If you want download analytics
- If you need rate limiting
- If you want custom auth (GitHub OAuth for publishing)

---

### Option C: Supabase Edge Functions

```
┌─────────┐     ┌─────────────────────────┐
│  User   │────▶│       Supabase          │
│   MCP   │◀────│  Edge Fn ──▶ DB         │
└─────────┘     └─────────────────────────┘
```

**Pros:**
- Same infrastructure
- Can add custom logic
- No separate hosting

**Cons:**
- Still Supabase-locked
- Cold starts

---

## 5. Recommended Approach

### Phase 1: MVP (Now)

1. **Keep direct Supabase** - It works, it's simple
2. **Use anon key in code** - It's designed to be public
3. **Secret key via env var** - Only needed for publishing
4. **Set up RLS properly** - Read-public, write-authenticated

```python
# context_kiwi/config/registry.py

# All Supabase configuration must come from environment variables
# Users must create their own Supabase project

def get_supabase_url() -> str:
    """Get Supabase URL from environment."""
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL environment variable is required")
    return url

def get_supabase_anon_key() -> str:
    """Get Supabase anon key from environment."""
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not key:
        raise ValueError("SUPABASE_ANON_KEY environment variable is required")
    return key

# Secret key must come from env var - never hardcode
# Accepts either CONTEXT_KIWI_API_KEY or SUPABASE_SECRET_KEY
def get_supabase_secret_key():
    return os.environ.get("CONTEXT_KIWI_API_KEY") or os.environ.get("SUPABASE_SECRET_KEY")
```

### Phase 2: If Needed Later

Add a thin proxy API on Fly.io when you need:
- Download analytics
- Rate limiting
- GitHub OAuth for publishing

---

## 6. Pre-Launch Checklist

### Code

- [ ] Remove any hardcoded secret keys
- [ ] Update `pyproject.toml` URLs
- [ ] Add LICENSE file (MIT)
- [ ] Review .gitignore

### Supabase

- [ ] Enable RLS on all tables
- [ ] Test with anon key (reads should work)
- [ ] Test without secret key (writes should fail)

### GitHub

- [ ] Create public repo
- [ ] Add GitHub Actions for CI
- [ ] Add GitHub Actions for PyPI publish
- [ ] Write GitHub release notes

### PyPI

- [ ] Create account
- [ ] Generate API token
- [ ] Add token to GitHub secrets
- [ ] Test with TestPyPI first

---

## Quick Commands

```bash
# Build and check
python -m build && twine check dist/*

# Test install
pip install dist/context_kiwi-0.1.0-py3-none-any.whl

# Test run
context-kiwi --help

# Publish to TestPyPI
twine upload --repository testpypi dist/*

# Publish to real PyPI
twine upload dist/*
```

