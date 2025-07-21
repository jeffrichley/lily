# Development Strategy

## Current Phase: MVP Development

### Approach: "Dirty but Pragmatic"

We're using a **rapid prototyping approach** for the MVP phase:

- **Cross-repository dependencies** via git checkouts in CI
- **Editable local installations** for tandem development
- **Tight coupling** between Lily and Petal
- **Manual repository management** in workflows

### Why This Approach?

1. **Speed**: Quick to set up and iterate
2. **Immediate Feedback**: Changes in Petal instantly available in Lily
3. **Tandem Development**: Single developer working on both projects
4. **Experimental**: Not production-ready, so we can be flexible

### Current Setup

```yaml
# CI: Multi-repo checkout
- uses: actions/checkout@v4
  with:
    repository: ${{ github.repository_owner }}/petal
    path: ../petal

# Local: Editable installation
uv pip install -e ../petal
```

## Future Phase: Production Ready

### Migration Criteria

Move to clean architecture when:

- [ ] Petal is **feature complete**
- [ ] Petal has **stable API**
- [ ] Petal has **comprehensive tests**
- [ ] Petal is **production tested**
- [ ] Team size **increases**
- [ ] **Open source** release planned

### Target Architecture

#### Option 1: Package Registry (Recommended)
```toml
# pyproject.toml
dependencies = [
    "petal>=1.0.0,<2.0.0"
]
```

**Steps:**
1. Publish Petal to PyPI or private registry
2. Use semantic versioning
3. Remove CI complexity
4. Standard Python dependency management

#### Option 2: Monorepo
```
dream/
├── packages/
│   ├── petal/
│   └── lily/
├── tools/
└── docs/
```

**Steps:**
1. Consolidate repositories
2. Shared tooling and CI
3. Atomic commits across projects
4. Simplified dependency management

#### Option 3: Git Dependencies (Cleaner)
```toml
dependencies = [
    "petal @ git+https://github.com/jeffrichley/petal.git@v1.0.0"
]
```

**Steps:**
1. Tag stable releases in Petal
2. Pin to specific versions
3. Remove manual CI checkouts
4. Standard git-based dependencies

## Migration Checklist

### Phase 1: Stabilize Petal
- [ ] Complete core features
- [ ] Comprehensive test coverage
- [ ] API stability
- [ ] Documentation
- [ ] Version 1.0.0 release

### Phase 2: Prepare for Migration
- [ ] Choose target architecture
- [ ] Set up package registry (if needed)
- [ ] Create migration plan
- [ ] Test new approach

### Phase 3: Execute Migration
- [ ] Update dependency management
- [ ] Simplify CI/CD
- [ ] Update documentation
- [ ] Deploy new architecture

## Current Benefits

- **Fast iteration** during MVP
- **Immediate feedback** between projects
- **Simple setup** for development
- **Flexible** for rapid changes

## Future Benefits

- **Clean architecture**
- **Standard tooling**
- **Better scalability**
- **Easier onboarding**
- **Production ready**

## Notes

- **Don't optimize prematurely** - MVP first
- **Document technical debt** - track what needs cleanup
- **Plan migration** - but don't implement until needed
- **Keep it working** - functionality over perfection

---

*This document should be updated as the project evolves and migration criteria are met.*
