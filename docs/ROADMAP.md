# Context Kiwi: Roadmap

## Vision

Build a directive-based MCP ecosystem that makes LLM code generation deterministic, self-improving, and shareable. Think "npm for AI-generated code patterns" - but the patterns heal themselves and get better over time.

---

## Current Status

### ✅ Completed

- [x] Python MCP server with stdio and HTTP transports
- [x] 6 tools: search, run, get, publish, delete, help
- [x] Local directive loading (project > user > registry)
- [x] Supabase integration for directive storage
- [x] Semver versioning for directives
- [x] Project initialization (init directive)
- [x] Tech stack compatibility filtering
- [x] Category and subcategory support
- [x] Multi-tier deletion (registry/user/project)
- [x] Preflight validation (credentials, inputs, packages)
- [x] Project context loading (.ai/tech_stack.md, patterns/)

### 🔄 In Progress

- [ ] HTTP transport with Streamable HTTP
- [ ] Core directive content in database
- [ ] Analytics tracking

---

## Phase 1: Foundation (Current)

**Goal:** Stable MCP server with core functionality

### Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| Core server | 6 tools working | ✅ Done |
| Database integration | Supabase with versioning | ✅ Done |
| Project initialization | Init directive | ✅ Done |
| Local directive loading | Project/user/registry resolution | ✅ Done |
| Multi-tier deletion | Registry/user/project deletion | ✅ Done |
| HTTP transport | Production deployment | 🔄 In Progress |
| Analytics | Usage tracking | 📋 Planned |

### Deliverables

1. **Working MCP server** that can:
   - Search for directives (local/registry/all)
   - Run directives from local space
   - Get directives from registry
   - Publish directives to registry
   - Delete directives from any tier
   - Provide help and guidance

2. **Core directives** in database:
   - bootstrap
   - bootstrap_check
   - help_workflow
   - help_permissions
   - help_bootstrap

3. **Development tooling**:
   - Local dev with stdio
   - Tests for core functionality
   - Documentation

---

## Phase 2: Pattern System

**Goal:** Enable reusable code patterns with context awareness

### Features

| Feature | Description |
|---------|-------------|
| Pattern storage | Store code patterns in Supabase |
| Context matching | Match patterns to project tech stack |
| Pattern versioning | Semver for patterns like directives |
| Local caching | Cache patterns in ~/.context-kiwi/ |

### New Directives

- `create_component` - Generate UI components
- `create_api` - Generate API endpoints
- `create_migration` - Generate database migrations
- `create_pattern` - Create new patterns

### Data Model

```
patterns table:
├── id, name, version
├── template (Jinja2/Handlebars)
├── variables (schema)
├── tech_stack (compatibility)
├── quality_score, downloads
└── self_annealing_log
```

---

## Phase 3: Self-Annealing

**Goal:** Patterns improve automatically when they fail

### How It Works

```
1. Pattern generates code
2. Code fails (lint error, test failure, etc.)
3. heal_directive analyzes failure
4. Pattern updated with fix
5. self_annealing_log records improvement
6. Next generation works better
```

### Components

| Component | Purpose |
|-----------|---------|
| Failure detection | Catch errors during generation |
| Analysis engine | Understand what went wrong |
| Pattern updater | Modify pattern to fix issue |
| Annealing log | Track improvements over time |

### New Directives

- `heal_directive` - Analyze and fix failing patterns
- `analyze_failure` - Understand generation errors

---

## Phase 4: Pattern Marketplace

**Goal:** Share patterns across users and projects

### Features

| Feature | Description |
|---------|-------------|
| Publishing | Share patterns to registry |
| Discovery | Search with context matching |
| Quality metrics | Success rate, downloads, ratings |
| User accounts | Publisher identity and trust |

### New Endpoints

```
GET  /patterns/search?q=...&tech_stack=react
GET  /patterns/{name}
GET  /patterns/{name}/{version}
POST /patterns/publish (authenticated)
```

### Trust System

| Level | Description |
|-------|-------------|
| Official | Context Kiwi team maintained |
| Verified | Community, reviewed |
| Community | User-submitted |

---

## Phase 5: Vision Integration

**Goal:** Generate patterns from screenshots

### How It Works

```
User: "Create component like this [screenshot]"

1. Send screenshot to vision API (Claude/GPT-4)
2. Extract: layout, colors, spacing, typography
3. Map to project's design system
4. Generate component using project patterns
```

### Features

- Screenshot → component generation
- Design system extraction
- Pattern inference from existing code

---

## Phase 6: Team Features

**Goal:** Enable team collaboration

### Features

| Feature | Description |
|---------|-------------|
| Private patterns | Org-only visibility |
| Team workspaces | Shared namespace |
| Access control | Role-based permissions |
| Usage analytics | Team pattern usage stats |

### Pricing (Future)

| Tier | Features | Price |
|------|----------|-------|
| Free | Public patterns, unlimited use | $0 |
| Pro | Private patterns, priority support | $10/mo |
| Team | Workspace, analytics, admin | $50/mo |
| Enterprise | SSO, SLA, support | Custom |

---

## Technical Debt & Improvements

### Near-term

- [ ] Improve error messages
- [ ] Add request logging
- [ ] Implement rate limiting
- [ ] Add health check endpoint
- [ ] Improve test coverage

### Medium-term

- [ ] Edge caching for directives
- [ ] Connection pooling
- [ ] Metrics/monitoring
- [ ] Webhook notifications

### Long-term

- [ ] Multi-region deployment
- [ ] Offline-first architecture
- [ ] Plugin system
- [ ] IDE extensions

---

## Success Metrics

### Phase 1 (Foundation)
- [ ] Server handles 100 req/min
- [ ] Bootstrap works reliably
- [ ] <500ms response time

### Phase 2 (Patterns)
- [ ] 20+ patterns available
- [ ] 90%+ generation success rate
- [ ] Context matching accuracy >80%

### Phase 3 (Self-Annealing)
- [ ] 50% reduction in generation failures
- [ ] Patterns improve over time
- [ ] Zero manual pattern fixes needed

### Phase 4 (Marketplace)
- [ ] 100+ community patterns
- [ ] 1000+ active users
- [ ] Quality score >0.9 average

---

## Contributing

We welcome contributions! Areas where help is needed:

### High Priority
- Core directive content
- Test coverage
- Documentation

### Medium Priority
- Pattern templates
- Tech stack detection
- Error handling

### Future
- IDE extensions
- Vision integration
- Analytics dashboard

See [Getting Started](./GETTING_STARTED.md) for development setup.

---

## Timeline (Rough)

| Phase | Timeline | Status |
|-------|----------|--------|
| Foundation | Q4 2024 | 🔄 In Progress |
| Pattern System | Q1 2025 | 📋 Planned |
| Self-Annealing | Q1-Q2 2025 | 📋 Planned |
| Marketplace | Q2 2025 | 📋 Planned |
| Vision | Q3 2025 | 📋 Planned |
| Team Features | Q3-Q4 2025 | 📋 Planned |

---

## Related Documentation

- [Architecture](./ARCHITECTURE.md) - Technical design
- [Getting Started](./GETTING_STARTED.md) - Setup guide
- [Permissions](./PERMISSIONS.md) - Security model

