<!--
Sync Impact Report:
Version change: 0.0.0 → 1.0.0 (MAJOR - initial constitution ratification)
Modified principles: N/A (new constitution)
Added sections: Core Principles (5 principles), Design Patterns, Code Generation Standards, Governance
Removed sections: N/A
Templates requiring updates:
  ✅ plan-template.md - Constitution Check section aligns with new principles
  ✅ spec-template.md - No changes needed (already focuses on requirements)
  ✅ tasks-template.md - No changes needed (already focuses on minimal tasks)
Follow-up TODOs: None
-->

# Lily Constitution

## Core Principles

### I. Code Quality First (NON-NEGOTIABLE)

All generated code MUST meet production-quality standards. Code quality is not negotiable or deferred.

**Rules:**
- Code MUST be readable, maintainable, and follow language-specific best practices
- Code MUST include appropriate error handling and validation
- Code MUST be properly structured with clear separation of concerns
- Code MUST be documented where complexity or non-obvious behavior exists
- Code MUST pass all linting and static analysis checks before acceptance
- Code MUST be testable and include tests for critical paths

**Rationale:** High-quality code reduces technical debt, improves maintainability, and ensures long-term project viability. Quality cannot be retrofitted effectively.

### II. Minimal Code Generation (YAGNI - You Aren't Gonna Need It)

Generate ONLY the code that is absolutely required to fulfill the specification. No speculative code, no "nice-to-have" features, no premature optimization.

**Rules:**
- Code MUST directly implement requirements from the specification
- Code MUST NOT include features not explicitly specified
- Code MUST NOT include abstractions or patterns "for future use"
- Code MUST NOT include helper utilities unless they are immediately required
- Code MUST NOT include configuration or infrastructure beyond minimum viable needs
- If a requirement is unclear, MUST request clarification rather than implementing assumptions

**Rationale:** Extra code increases complexity, maintenance burden, and the risk of bugs. Every line of code must justify its existence against the specification.

### III. Gang of Four Design Patterns

Use established Gang of Four (GoF) design patterns to solve common design problems. Patterns provide proven solutions and improve code maintainability.

**Required Patterns:**
- **Command Pattern**: MUST be used for all user actions and operations that can be invoked, undone, or logged
- **Strategy Pattern**: MUST be used when multiple algorithms or implementations can be swapped (e.g., different coder targets, prompt formats)
- **Template Method Pattern**: MUST be used for consistent artifact generation and document creation workflows
- **State Pattern**: MUST be used for workflow state management and phase enforcement
- **Observer Pattern**: MUST be used for event-driven communication between components
- **Facade Pattern**: MUST be used to provide simple interfaces to complex subsystems
- **Abstract Factory Pattern**: MUST be used for creating families of related objects (e.g., adapters, formatters)

**Rules:**
- Patterns MUST be applied only when they solve a concrete problem identified in the specification
- Patterns MUST NOT be applied speculatively or "just in case"
- Pattern selection MUST be justified in architecture documentation
- When a GoF pattern fits a problem, it MUST be preferred over ad-hoc solutions

**Rationale:** GoF patterns provide battle-tested solutions to common design problems, improving code quality, maintainability, and team understanding. They reduce the need for custom solutions that may introduce bugs or complexity.

### IV. Specification-Driven Development

All code generation MUST be driven by explicit specifications. No code is written without a corresponding specification requirement.

**Rules:**
- Every code artifact MUST trace to a specific requirement in the specification
- Code MUST NOT implement features not present in the specification
- Specification changes MUST precede code changes
- Code reviews MUST verify specification compliance

**Rationale:** Specifications serve as the source of truth and prevent scope creep and unauthorized features.

### V. Testability and Validation

Code MUST be structured to enable testing and validation. Critical paths MUST have corresponding tests.

**Rules:**
- Code structure MUST allow unit testing of individual components
- Critical business logic MUST have unit tests
- Integration points MUST have integration tests
- Tests MUST be written before or alongside implementation (TDD preferred)
- Test coverage MUST meet project standards (minimum 80% for critical paths)

**Rationale:** Testable code is maintainable code. Tests provide confidence in changes and serve as living documentation.

## Design Patterns

### Pattern Application Guidelines

When implementing features, identify design problems and apply appropriate GoF patterns:

- **Command Pattern**: User actions, undoable operations, command queues
- **Strategy Pattern**: Algorithm selection, format variations, target adapters
- **Template Method**: Document generation, consistent workflows, validation pipelines
- **State Pattern**: Workflow management, phase transitions, state machines
- **Observer Pattern**: Event notifications, UI updates, logging
- **Facade Pattern**: Complex subsystem interfaces, API simplification
- **Abstract Factory**: Adapter creation, multi-format support, platform abstraction

Patterns MUST solve real problems, not be applied for their own sake.

## Code Generation Standards

### Minimal Viable Implementation

Code generation MUST follow these constraints:

1. **Requirement Traceability**: Every function, class, and module MUST map to a specification requirement
2. **No Speculative Code**: Do not generate code for "future" requirements or "might need" scenarios
3. **No Premature Abstraction**: Generate concrete implementations first; abstract only when duplication emerges
4. **No Over-Engineering**: Choose the simplest solution that meets the requirement
5. **Explicit Over Implicit**: Prefer explicit code over "clever" solutions that require deep understanding

### Code Review Checklist

Before accepting generated code, verify:

- [ ] Every function/class traces to a specification requirement
- [ ] No code exists that isn't required by the specification
- [ ] Appropriate GoF patterns are used where applicable
- [ ] Code quality standards are met (readability, error handling, documentation)
- [ ] Tests exist for critical paths
- [ ] No speculative or "future-proofing" code is present

## Development Workflow

### Code Generation Process

1. **Specification Review**: Verify all requirements are clear and testable
2. **Pattern Selection**: Identify which GoF patterns apply to the requirements
3. **Minimal Design**: Design the smallest implementation that meets requirements
4. **Implementation**: Generate only the required code
5. **Validation**: Verify code quality, pattern application, and specification compliance
6. **Testing**: Ensure tests cover critical paths

### Quality Gates

Code MUST pass these gates before acceptance:

- Specification compliance verification
- Code quality checks (linting, static analysis)
- Pattern application review
- Minimal code verification (no extra code)
- Test coverage validation

## Governance

This constitution supersedes all other development practices and guidelines. All code generation and development work MUST comply with these principles.

**Amendment Process:**
- Amendments require explicit documentation of the change rationale
- Version numbers follow semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Backward-incompatible principle changes
- MINOR: New principles or significant expansions
- PATCH: Clarifications and non-semantic refinements
- All amendments MUST be reflected in dependent templates and documentation

**Compliance:**
- All code reviews MUST verify constitution compliance
- Violations MUST be addressed before code acceptance
- Complexity or pattern deviations MUST be justified in architecture documentation

**Version**: 1.0.0 | **Ratified**: 2025-01-27 | **Last Amended**: 2025-01-27
