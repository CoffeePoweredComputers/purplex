# Agent Instructions for Claude Code

## Automatic Agent Triggers

These agents should run automatically based on user actions:

### File Operations
```yaml
on_file_create:
  - pattern-matcher: Get correct template
  - refactoring-guardian: Avoid legacy patterns

on_file_edit:
  - refactoring-guardian: Check if using clean version
  - standards-enforcer: Validate changes

on_file_read:
  - refactoring-guardian: Warn if legacy file
```

### Code Operations
```yaml
before_writing_code:
  - pattern-matcher: Get template
  - refactoring-guardian: Check for clean versions

after_writing_code:
  - standards-enforcer: Check standards
  - architecture-validator: Check patterns

before_import:
  - refactoring-guardian: Verify not importing legacy
```

### Git Operations
```yaml
before_commit:
  - code-quality-orchestrator: Full validation
  - commit-message-generator: Create message

before_pr:
  - architecture-validator: Full review
  - test-coverage-analyzer: Check coverage
```

## Agent Implementation Prompts

### For standards-enforcer:
```
You are a code standards enforcement agent for Purplex. 

Your job:
1. Read STANDARDS.md
2. Check the current code changes
3. Report any violations
4. Block if critical issues found

Check for:
- Python: snake_case functions, PascalCase classes
- Vue: PascalCase components, Composition API only
- API: kebab-case endpoints
- Service pattern: No business logic in views
- Consistent error responses

Return BLOCKING for:
- Business logic in views
- Options API in Vue
- Wrong naming conventions
- Direct model access from views
```

### For refactoring-guardian:
```
You are a legacy code prevention agent for Purplex.

Your job:
1. Read REFACTORING_PLAN.md
2. Check if code being used is legacy
3. Suggest clean alternatives
4. Block use of legacy patterns

Check for:
- Files with _clean versions
- Legacy patterns being copied
- Imports from legacy modules

Always suggest the clean alternative from REFACTORING_PLAN.md
```

### For pattern-matcher:
```
You are a pattern suggestion agent for Purplex.

Your job:
1. Detect what user is implementing
2. Read PATTERNS.md
3. Provide exact template
4. Fill in obvious values

Patterns to match:
- API endpoint → API pattern
- Vue component → Component pattern
- Service class → Service pattern
- Celery task → Task pattern
- Test file → Test pattern

Generate complete boilerplate with TODOs for custom logic
```

### For code-quality-orchestrator:
```
You are the master quality control agent for Purplex.

Your job:
1. Orchestrate other agents based on context
2. Provide consolidated report
3. Block commits if standards not met

Workflow:
- New file: pattern-matcher → standards-enforcer
- Edit file: refactoring-guardian → standards-enforcer → architecture-validator
- Commit: Run all validators → generate message

Provide single quality report with:
- Pass/Fail for each check
- Specific fixes needed
- Ready to commit: YES/NO
```

## Example Workflows

### Creating New Feature
```
User: "Add a new endpoint for student analytics"

1. pattern-matcher runs automatically
   → Provides API endpoint template from PATTERNS.md
   
2. Claude creates file with template

3. standards-enforcer runs
   → Validates naming and structure
   
4. architecture-validator runs
   → Confirms service pattern used

5. test-coverage-analyzer runs
   → Generates test stub
```

### Refactoring Legacy Code
```
User: "Update the submission processing"

1. refactoring-guardian runs
   → Detects pipeline.py is legacy
   → Points to pipeline_clean.py
   
2. Claude uses clean version

3. standards-enforcer runs
   → Validates changes follow standards
   
4. Updates REFACTORING_PLAN.md
```

### Committing Changes
```
User: "Commit my changes"

1. code-quality-orchestrator runs
   → Runs all validators
   → Generates report
   
2. If all pass:
   → commit-message-generator runs
   → Creates formatted message
   
3. If any fail:
   → BLOCKS commit
   → Shows required fixes
```

## Integration with Existing Agents

These custom agents work alongside existing Claude Code agents:

- **django-backend-guardian**: Focus on Django-specific patterns
- **design-consistency-reviewer**: Focus on UI/UX consistency
- **frontend-logging-enforcer**: Focus on logging standards

Our custom agents focus on:
- Project-specific standards
- Legacy code prevention
- Pattern consistency
- Architecture compliance

## Enforcement Levels

### BLOCKING (Must Fix)
- Business logic in views
- Using legacy code
- Security vulnerabilities
- Breaking architectural patterns

### WARNING (Should Fix)
- Missing tests
- Suboptimal patterns
- Performance concerns
- Documentation gaps

### INFO (Consider)
- Style preferences
- Optional optimizations
- Future improvements

## Success Metrics

Track enforcement success:
- Legacy code usage: Should be 0%
- Standards compliance: Should be 100%
- Test coverage: Should be >80%
- Clean migrations completed: Track progress

## Notes for Claude Code

**IMPORTANT**: These agents are your quality gatekeepers. Always:
1. Run appropriate agents automatically
2. Never skip or override without user permission
3. Fix all BLOCKING issues before proceeding
4. Update tracking documents when refactoring