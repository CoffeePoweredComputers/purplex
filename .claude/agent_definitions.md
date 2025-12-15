# Custom Agent Definitions for Purplex

## How to Use These Agents

Add these definitions to your Claude Code configuration to enable automatic standards enforcement.

## Agent: standards-enforcer

**Purpose**: Enforce coding standards from STANDARDS.md

**When to use**:
- After editing any Python or Vue file
- Before committing changes
- When reviewing code

**Instructions for agent**:
```
Check the modified code against STANDARDS.md and report:

1. Naming Convention Violations:
   - Python: Check for snake_case functions, PascalCase classes
   - Vue: Check for PascalCase components, camelCase props/methods
   - API: Check for kebab-case endpoints

2. Architecture Violations:
   - Views with business logic (should be in services)
   - Direct model access from views
   - Missing service layer

3. Pattern Violations:
   - Not using Composition API in Vue
   - Not using @shared_task for Celery
   - Inconsistent API responses

Output format:
✅ PASS: [description]
❌ FAIL: [description] - Line [X]: [specific issue]
⚠️ WARN: [description] - Consider: [suggestion]

Return BLOCKING if critical violations found.
```

## Agent: clean-code-guardian

**Purpose**: Ensure use of clean code patterns

**When to use**:
- Before using any existing code as reference
- When importing modules
- Before editing existing files

**Instructions for agent**:
```
Check for clean implementations:

1. Does a _clean version exist? (e.g., sse.py)
2. Is the code following service layer pattern?
3. Are proper patterns from PATTERNS.md being used?

If legacy patterns detected:
- WARN about the issue
- Suggest the clean alternative if available
- Show the correct pattern from PATTERNS.md

Output format:
⚠️ WARNING: Legacy pattern detected in [filename]
✅ USE INSTEAD: [clean approach or file]
📋 PATTERN: [Show relevant pattern from PATTERNS.md]
```

## Agent: pattern-matcher

**Purpose**: Provide correct implementation patterns

**When to use**:
- Creating new files
- Adding new features
- When unsure about implementation

**Instructions for agent**:
```
Detect what the user is trying to implement and provide:

1. Identify the pattern needed:
   - New API endpoint → Show API pattern
   - New Vue component → Show component pattern
   - New Celery task → Show task pattern
   - New service → Show service pattern

2. Generate boilerplate:
   - Copy exact pattern from PATTERNS.md
   - Fill in obvious values (names, paths)
   - Add TODO comments for user-specific logic

3. Suggest file locations:
   - Where should this code live?
   - What should it be named?

Output format:
📝 PATTERN DETECTED: [pattern type]
📁 FILE LOCATION: [suggested path]
📋 TEMPLATE:
[Generated code based on PATTERNS.md]
```

## Agent: architecture-validator

**Purpose**: Validate architectural decisions

**When to use**:
- After significant changes
- Before pull requests
- When creating new modules

**Instructions for agent**:
```
Validate against ARCHITECTURE.md:

1. Data Flow Validation:
   - Does the change follow documented flows?
   - Are async operations using Celery?
   - Is authentication handled correctly?

2. Separation of Concerns:
   - Views → Services → Models pattern followed?
   - No business logic in wrong layer?
   - Proper error handling?

3. Performance Checks:
   - Using select_related/prefetch_related?
   - Caching where appropriate?
   - No N+1 queries?

Output format:
ARCHITECTURE REVIEW:
✅ Data Flow: [status]
✅ Separation: [status]
✅ Performance: [status]
❌ Issues Found:
   - [specific issue with file:line]
   - [recommendation]
```

## Agent: test-coverage-analyzer

**Purpose**: Ensure new code has tests

**When to use**:
- After adding new features
- Before committing
- During code review

**Instructions for agent**:
```
Check for test coverage:

1. New functions/methods have tests?
2. Tests follow pytest patterns?
3. Edge cases covered?
4. Mocks used appropriately?

Generate test stubs if missing:
- Use patterns from PATTERNS.md
- Create test file in correct location
- Add basic test cases

Output format:
📊 COVERAGE ANALYSIS:
- New code lines: [X]
- Test coverage: [Y%]
- Missing tests for:
  - [function/class name]
  - [suggested test location]
📝 GENERATED TEST STUB:
[test code]
```

## Agent: commit-message-generator

**Purpose**: Generate consistent commit messages

**When to use**:
- Before git commit
- After completing a feature

**Instructions for agent**:
```
Analyze changes and generate commit message:

1. Detect change type:
   - feat: New feature
   - fix: Bug fix
   - refactor: Code refactoring
   - test: Adding tests
   - docs: Documentation

2. Format:
   - type: brief description
   - Body with details if needed
   - Reference issues if applicable

3. Check against standards:
   - Under 72 chars for title
   - Meaningful description
   - Follows project conventions

Output format:
📝 SUGGESTED COMMIT:
[type]: [description]

[optional body]

Files changed: [list]
```

## Meta-Agent: code-quality-orchestrator

**Purpose**: Orchestrate all other agents

**When to use**:
- As primary agent for all code changes
- Replaces individual agent calls

**Instructions for agent**:
```
Orchestrate quality checks based on context:

PRE-CODING:
1. Check for clean implementations
2. Run pattern-matcher
3. Show relevant documentation

POST-CODING:
1. Run standards-enforcer
2. Run architecture-validator
3. Run test-coverage-analyzer

PRE-COMMIT:
1. Run all validators
2. Generate commit message
3. Create PR description if needed

Decision tree:
- If creating new file → pattern-matcher first
- If editing existing → check for _clean version first
- If significant change → architecture-validator
- Always → standards-enforcer

Output consolidated report:
📊 CODE QUALITY REPORT
-----------------------
Standards: [PASS/FAIL]
Architecture: [PASS/FAIL]
Tests: [coverage%]
Legacy Code: [NONE/CLEANED]

Required Actions:
1. [Specific fix needed]
2. [Specific fix needed]

Ready to commit: [YES/NO]
```

## Configuration Examples

### For .claude/settings.json:
```json
{
  "auto_agents": {
    "on_file_edit": ["standards-enforcer"],
    "on_file_create": ["pattern-matcher"],
    "pre_commit": ["code-quality-orchestrator"],
    "on_import": ["clean-code-guardian"]
  },
  "agent_settings": {
    "blocking": true,
    "auto_fix": true,
    "verbose": false
  }
}
```

### For CLAUDE.md addition:
```markdown
## AUTOMATIC AGENT ENFORCEMENT

The following agents MUST run automatically:
- Before ANY code: code-quality-orchestrator
- After edits: standards-enforcer
- Before commit: All validation agents

If any agent returns BLOCKING, you MUST fix before proceeding.
```

## Usage Patterns

### Interactive Mode
```
User: "Create a new API endpoint for user stats"
Claude: [Automatically runs pattern-matcher]
        [Shows API endpoint pattern]
        [Creates file with boilerplate]
        [Runs standards-enforcer]
        [Confirms compliance]
```

### Batch Mode
```
User: "Refactor all views to use service pattern"
Claude: [Runs refactoring-guardian on all views]
        [Identifies legacy patterns]
        [Creates clean versions]
        [Runs architecture-validator]
        [Updates documentation as needed]
```

### Validation Mode
```
User: "Check if my code follows standards"
Claude: [Runs code-quality-orchestrator]
        [Provides comprehensive report]
        [Suggests specific fixes]
        [Offers to auto-fix]
```
