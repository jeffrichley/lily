# MkDocs Configuration Contract

**Feature**: Documentation Site Infrastructure  
**Date**: 2026-01-15  
**Type**: Configuration Contract

## Overview

This contract defines the expected structure and behavior of the `mkdocs.yml` configuration file that controls MkDocs site generation.

## Configuration Schema

### Required Fields

- **site_name** (string): The title of the documentation site, displayed in the header and browser tab
- **theme.name** (string): Must be "material" to use Material theme

### Optional but Recommended Fields

- **site_description** (string): Description of the site for metadata
- **site_url** (string): Base URL for absolute links (required for GitHub Pages)
- **repo_url** (string): Repository URL for "Edit on GitHub" links
- **nav** (array): Navigation structure (auto-generated if omitted)

### Theme Configuration

**Material Theme Palette**:
- Must define at least one color scheme (default light mode)
- Should define dark mode scheme (slate) for dark mode toggle
- Color values: Any valid CSS color (hex, rgb, named colors)

**Material Theme Features**:
- `search.suggest`: Enable search suggestions
- `search.highlight`: Enable search result highlighting
- `content.code.copy`: Enable copy button on code blocks
- `navigation.tabs`: Enable tabbed navigation
- `navigation.sections`: Enable section navigation
- `navigation.top`: Enable back-to-top button

### Plugin Configuration

**Required Plugins**:
- `search`: Built-in search functionality (no configuration needed)
- `mermaid2`: Mermaid diagram rendering (default configuration sufficient)

**Plugin Order**: Plugins are processed in order listed. `search` should typically be first.

### Markdown Extensions

**Recommended Extensions**:
- `pymdownx.superfences`: Enhanced code fence support
- `pymdownx.highlight`: Syntax highlighting
- `admonition`: Admonition blocks (note, warning, etc.)
- `pymdownx.details`: Collapsible details/summary blocks
- `pymdownx.tabbed`: Tabbed content blocks
- `attr_list`: Attribute lists for HTML attributes
- `md_in_html`: Markdown within HTML blocks

## Validation Rules

1. **YAML Syntax**: Configuration must be valid YAML
2. **Theme Name**: If theme is specified, name must be "material"
3. **Plugin Names**: Plugin names must match installed plugin packages
4. **Navigation**: If nav is specified, all referenced files must exist in docs/ directory
5. **URLs**: site_url and repo_url should be valid URLs if provided

## Error Handling

**Invalid Configuration**:
- MkDocs will fail with clear error messages indicating:
  - Which field is invalid
  - What the expected format is
  - Which file/line caused the error

**Missing Files**:
- If nav references non-existent files, MkDocs will warn but may still build
- Missing source files will cause build to fail with file path error

## Example Configuration

```yaml
site_name: Lily Documentation
site_description: Documentation for the Lily project orchestration framework
site_url: https://username.github.io/lily/
repo_url: https://github.com/username/lily

theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - search.suggest
    - search.highlight
    - content.code.copy
    - navigation.tabs
    - navigation.sections
    - navigation.top

plugins:
  - search
  - mermaid2

markdown_extensions:
  - pymdownx.superfences
  - pymdownx.highlight
  - admonition
  - pymdownx.details
  - pymdownx.tabbed
  - attr_list
  - md_in_html

nav:
  - Home: index.md
  - Specs: specs/
  - Ideas: ideas/
```

## Contract Guarantees

1. **Deterministic Output**: Same configuration + same source files = same generated site
2. **Error Messages**: Invalid configuration produces clear, actionable error messages
3. **Backward Compatibility**: Configuration structure follows MkDocs conventions and will work with future MkDocs versions (within major version)
4. **Feature Support**: Configuration enables all required features (search, dark mode, Mermaid diagrams)

