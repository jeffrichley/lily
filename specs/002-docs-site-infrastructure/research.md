# Research: Documentation Site Infrastructure

**Feature**: Documentation Site Infrastructure  
**Date**: 2026-01-15  
**Phase**: 0 - Research

## Research Questions

### 1. MkDocs Installation and Dependency Management

**Question**: How should MkDocs and its plugins be added to a Python project using uv/pyproject.toml?

**Decision**: Add MkDocs dependencies to `pyproject.toml` in a new dependency group called `docs` to keep documentation dependencies separate from runtime dependencies.

**Rationale**: 
- Keeps documentation tooling separate from application dependencies
- Allows users to install docs dependencies only when needed: `uv sync --group docs`
- Follows Python packaging best practices for optional dependencies
- Compatible with uv dependency management

**Alternatives considered**:
- Adding to main dependencies: Rejected because docs tools aren't needed for application runtime
- Separate requirements.txt: Rejected because project uses pyproject.toml for dependency management

**Implementation**:
```toml
[dependency-groups]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.5.0",
    "mkdocs-mermaid2-plugin>=1.1.0",
]
```

### 2. MkDocs Configuration Structure

**Question**: What is the optimal mkdocs.yml configuration structure for this project's documentation needs?

**Decision**: Use a minimal mkdocs.yml with Material theme, search enabled, dark mode support, and Mermaid plugin configured. Navigation structure will mirror the docs/ directory organization.

**Rationale**:
- Minimal configuration aligns with project preference for "no ceremony"
- Material theme provides all required features (search, dark mode, modern appearance)
- Directory-based navigation is simpler than manual nav configuration
- Mermaid plugin enables diagram rendering as specified

**Alternatives considered**:
- Manual navigation configuration: Rejected because directory-based is simpler and easier to maintain
- Custom theme: Rejected because Material theme meets all requirements without customization overhead

**Key Configuration Elements**:
- Site name and description from project metadata
- Material theme with dark mode toggle enabled
- Search functionality enabled (default in Material)
- Mermaid plugin for diagram support
- Directory-based navigation (nav will auto-populate from docs/ structure)

### 3. Documentation Directory Structure

**Question**: How should existing documentation files be organized in the docs/ directory?

**Decision**: Create a docs/ directory with:
- `index.md` as the site homepage (can link to or incorporate README.md content)
- `specs/` subdirectory (symlink or copy from root specs/)
- `ideas/` subdirectory (symlink or copy from root ideas/)
- Additional architecture/design docs as needed

**Rationale**:
- Follows MkDocs convention of docs/ as source directory
- Preserves existing documentation organization
- Allows incremental addition of new documentation
- Symlinks or copies maintain connection to source files

**Alternatives considered**:
- Moving all docs to docs/: Rejected because it would disrupt existing project structure
- Keeping docs at root: Rejected because MkDocs expects docs/ directory by default
- Single flat structure: Rejected because hierarchical organization is clearer

### 4. Justfile Targets for MkDocs

**Question**: What justfile targets are needed for documentation site development?

**Decision**: Create two justfile targets:
- `docs-serve`: Start local development server (mkdocs serve)
- `docs-build`: Build static site (mkdocs build)

**Rationale**:
- `docs-serve` enables local development with live reload
- `docs-build` creates production-ready static site for deployment
- Follows standard MkDocs workflow patterns
- Integrates with existing justfile structure

**Alternatives considered**:
- Single target with flags: Rejected because separate targets are clearer and more intuitive
- Additional deployment target: Deferred - GitHub Pages deployment can use mkdocs gh-deploy or be handled via CI/CD

**Implementation**:
```just
# Serve documentation site locally
docs-serve:
    uv run mkdocs serve

# Build documentation site
docs-build:
    uv run mkdocs build
```

### 5. Mermaid Diagram Support

**Question**: How should Mermaid diagrams be configured in MkDocs?

**Decision**: Use mkdocs-mermaid2-plugin with default configuration. Diagrams will be written in Markdown code blocks with `mermaid` language identifier.

**Rationale**:
- mkdocs-mermaid2-plugin is the recommended plugin for Material theme
- Standard Markdown code block syntax is familiar and easy to use
- Default configuration is sufficient for initial needs
- Can be extended later if needed

**Alternatives considered**:
- mkdocs-mermaid-plugin (older): Rejected because mkdocs-mermaid2-plugin is actively maintained and recommended
- Custom Mermaid integration: Rejected because plugin provides all needed functionality

**Configuration**:
```yaml
plugins:
  - search
  - mermaid2
```

### 6. GitHub Pages Deployment Configuration

**Question**: How should the site be configured for GitHub Pages deployment?

**Decision**: Configure mkdocs.yml with site_url and repo_url for GitHub Pages. Use mkdocs gh-deploy command or GitHub Actions for deployment. Add site/ directory to .gitignore.

**Rationale**:
- site_url enables proper absolute URLs in generated site
- repo_url enables "Edit on GitHub" links
- site/ directory should be gitignored (generated content)
- Deployment can be manual (gh-deploy) or automated (GitHub Actions)

**Alternatives considered**:
- Committing site/ directory: Rejected because generated content shouldn't be version controlled
- Manual deployment only: Accepted as initial approach, can add GitHub Actions later if needed

**Configuration**:
```yaml
site_url: https://[username].github.io/lily/
repo_url: https://github.com/[username]/lily
```

### 7. Site Output Directory

**Question**: Where should MkDocs output the generated site?

**Decision**: Use default `site/` directory at project root. Add to .gitignore.

**Rationale**:
- Default MkDocs output location is standard and expected
- Keeps generated files separate from source files
- Easy to identify and clean up
- Standard location for deployment tools

**Alternatives considered**:
- Custom output directory: Rejected because default is sufficient and standard
- docs/_build/: Rejected because site/ is more standard for MkDocs

## Summary of Decisions

1. **Dependencies**: Add to `[dependency-groups]` in pyproject.toml as `docs` group
2. **Configuration**: Minimal mkdocs.yml with Material theme, search, dark mode, Mermaid plugin
3. **Documentation Structure**: docs/ directory with index.md, specs/, ideas/ subdirectories
4. **Justfile Targets**: `docs-serve` and `docs-build` targets
5. **Mermaid**: Use mkdocs-mermaid2-plugin with default configuration
6. **GitHub Pages**: Configure site_url and repo_url, use gh-deploy or GitHub Actions
7. **Output**: Use default `site/` directory, add to .gitignore

All research questions resolved. Ready for Phase 1 design.

