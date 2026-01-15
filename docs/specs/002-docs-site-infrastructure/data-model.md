# Data Model: Documentation Site Infrastructure

**Feature**: Documentation Site Infrastructure  
**Date**: 2026-01-15  
**Phase**: 1 - Design

## Overview

This feature is an integration task with no application data model. However, there are configuration structures that define the system behavior.

## Configuration Models

### MkDocs Configuration (mkdocs.yml)

**Purpose**: Defines site structure, appearance, and behavior

**Structure**:
```yaml
site_name: string          # Site title displayed in header
site_description: string   # Site description/metadata
site_url: string          # Base URL for absolute links (GitHub Pages)
repo_url: string          # Repository URL for "Edit on GitHub" links

theme:
  name: material          # Material theme identifier
  palette:
    - scheme: default     # Light mode scheme
      primary: color       # Primary color
      accent: color       # Accent color
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate       # Dark mode scheme
      primary: color
      accent: color
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - search.suggest      # Search suggestions
    - search.highlight    # Search highlighting
    - content.code.copy   # Copy code block button
    - navigation.tabs     # Tabbed navigation
    - navigation.sections # Section navigation
    - navigation.top      # Back to top button

plugins:
  - search               # Built-in search plugin
  - mermaid2             # Mermaid diagram plugin

markdown_extensions:
  - pymdownx.superfences # Enhanced code fences
  - pymdownx.highlight   # Syntax highlighting
  - admonition           # Admonition blocks
  - pymdownx.details     # Details/summary blocks
  - pymdownx.tabbed      # Tabbed content
  - attr_list            # Attribute lists
  - md_in_html           # Markdown in HTML

nav:                      # Navigation structure (auto-generated from docs/ or manual)
  - Home: index.md
  - Specs: specs/
  - Ideas: ideas/
```

**Validation Rules**:
- `site_name` is required
- `theme.name` must be "material" for Material theme
- `plugins` must include "search" for search functionality
- `plugins` must include "mermaid2" for Mermaid diagram support
- `site_url` should be set for GitHub Pages deployment
- `repo_url` should be set for "Edit on GitHub" links

### Documentation Page Structure

**Purpose**: Represents a single documentation page in the site

**Attributes**:
- **source_path**: Relative path from docs/ directory to Markdown source file
- **generated_path**: Relative path from site/ directory to generated HTML file
- **title**: Page title (extracted from first H1 or frontmatter)
- **navigation_position**: Position in sidebar navigation (determined by file order or nav config)
- **content**: Markdown content converted to HTML

**Relationships**:
- One source Markdown file → One generated HTML page
- Pages organized hierarchically in navigation structure
- Pages can reference other pages via relative links

### Navigation Structure

**Purpose**: Defines the hierarchical organization of pages in sidebar

**Attributes**:
- **items**: Array of navigation items (pages or sections)
- **order**: Determined by file system order or explicit nav configuration
- **nesting_levels**: Supports multiple levels of nesting

**Structure**:
- Top-level items appear in main sidebar
- Nested items appear as expandable sections
- Order can be explicit (nav config) or implicit (directory structure)

## File System Structure

### Source Files (docs/)

```
docs/
├── index.md              # Homepage
├── README.md             # Documentation overview (optional)
├── specs/                # Specifications directory
│   ├── 001-init-command/
│   └── 002-docs-site-infrastructure/
├── ideas/                # Ideas directory
│   ├── commands/
│   └── core/
└── [other-docs].md       # Additional documentation files
```

### Generated Files (site/)

```
site/                     # Generated static site (gitignored)
├── index.html
├── specs/
│   ├── 001-init-command/
│   │   └── index.html
│   └── 002-docs-site-infrastructure/
│       └── index.html
├── ideas/
│   ├── commands/
│   │   └── index.html
│   └── core/
│       └── index.html
├── search/
│   └── search_index.json # Search index
└── assets/               # CSS, JS, images
```

## State Transitions

### Site Generation Process

1. **Source State**: Markdown files in docs/ directory
2. **Configuration Load**: Read and validate mkdocs.yml
3. **Processing**: MkDocs processes Markdown files
4. **Generation**: HTML files generated in site/ directory
5. **Index Creation**: Search index generated
6. **Complete State**: Static site ready for viewing/deployment

### Local Development Workflow

1. **Start Server**: `just docs-serve` → MkDocs dev server starts
2. **File Change**: User edits Markdown file
3. **Auto-reload**: MkDocs detects change and regenerates
4. **Browser Refresh**: Browser shows updated content

## Notes

- No database or persistent storage required
- All state is file-based (source Markdown + generated HTML)
- Configuration is YAML-based (mkdocs.yml)
- Search index is generated JSON file
- Site is fully static (no server-side processing)

