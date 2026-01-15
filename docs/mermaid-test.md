# Mermaid Diagram Test

This page tests Mermaid diagram rendering in the documentation site.

## Flowchart Example

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

## Sequence Diagram Example

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Command
    participant Storage
    
    User->>CLI: lily init
    CLI->>Command: execute()
    Command->>Storage: create files
    Storage-->>Command: success
    Command-->>CLI: result
    CLI-->>User: output
```

## State Diagram Example

```mermaid
stateDiagram-v2
    [*] --> DISCOVERY
    DISCOVERY --> SPEC
    SPEC --> ARCH
    ARCH --> IMPLEMENT
    IMPLEMENT --> POLISH
    POLISH --> [*]
```

These diagrams should render correctly if Mermaid plugin is configured properly.

