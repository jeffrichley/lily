---
description: Execute an implementation plan
argument-hint: [path-to-plan]
---

# Execute: Implement from Plan

## Plan to Execute

Read plan file: `$ARGUMENTS`

## Execution Instructions

### 0. Branch Safety Gate

- Confirm the plan includes a `## Branch Setup` section with executable branch commands.
- Execute the branch commands from that section before any implementation work.
- If `## Branch Setup` is missing, stop and add a `Plan Patch` to include it.
- After branch setup:
  - verify current branch is not `main` via `git branch --show-current`
  - continue only when on the plan-derived feature branch

### 1. Read and Understand

- Read the ENTIRE plan carefully
- Understand all tasks and their dependencies
- Note the validation commands to run
- Review the testing strategy

### 2. Execute Tasks in Order

Before starting each implementation phase, run:
- `.ai/COMMANDS/phase-intent-check.md <plan-path> "<phase-heading>"`

Execution gate:
- Do not begin phase tasks until that phase has an explicit `Intent Lock` block in the plan.
- If the lock is missing or ambiguous, stop and patch the plan first.

For EACH task in "Step by Step Tasks":

#### a. Navigate to the task
- Identify the file and action required
- Read existing related files if modifying

#### b. Implement the task
- Follow the detailed specifications exactly
- Maintain consistency with existing code patterns
- Include proper type hints and documentation
- Add structured logging where appropriate

#### c. Verify as you go
- After each file change, check syntax
- Ensure imports are correct
- Verify types are properly defined

#### d. Update plan tracking live
- If the plan includes checkbox tasks, mark them complete as each phase/task is finished.
- Do not defer checklist updates until the end.

#### e. Run status sync after each completed phase
- Run `.ai/COMMANDS/status-sync.md <plan-path>` (or without a plan path when not applicable).
- Ensure `just docs-check` and `just status` pass before moving to the next phase.

### 3. Implement Testing Strategy

After completing implementation tasks:

- Create all test files specified in the plan
- Implement all test cases mentioned
- Follow the testing approach outlined
- Ensure tests cover edge cases

### 4. Run Validation Commands

Start with `.ai/COMMANDS/validate.md` as the baseline validation workflow, then run all plan-specific commands.

Execute ALL validation commands from the plan in order:

```bash
# Run each command exactly as specified in plan
```

If any command fails:
- Fix the issue
- Re-run the command
- Continue only when it passes

If the plan depends on pre-existing inputs/resources:
- Execute prerequisite generation/setup commands from the plan when available.
- If prerequisites are unavailable, mark the run as partial/blocked in `## Execution Report`.

### 5. Final Verification

Before completing:

- ✅ All tasks from plan completed
- ✅ All tests created and passing
- ✅ All validation commands pass
- ✅ Code follows project conventions
- ✅ Documentation added/updated as needed

## Output Report

Provide summary:

### Completed Tasks
- List of all tasks completed
- Files created (with paths)
- Files modified (with paths)

### Tests Added
- Test files created
- Test cases implemented
- Test results

### Validation Results
```bash
# Output from each validation command
```

### Execution Report Update
- Append `## Execution Report` to the plan file with:
  - completion status
  - commands run and outcomes
  - output artifact paths
  - phase intent checks run + resulting acceptance gate evidence
  - any partial/blocked items and why

### Ready for Commit
- Confirm all changes are complete
- Confirm all validations pass
- Ready for `/commit` command

## Notes

- If you encounter issues not addressed in the plan, document them
- If you need to deviate from the plan, explain why
- If tests fail, fix implementation until they pass
- Don't skip validation steps
