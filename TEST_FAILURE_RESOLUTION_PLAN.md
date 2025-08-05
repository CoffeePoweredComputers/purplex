# Test Failure Resolution Plan

## Overview
The testing-framework branch (PR #18) has 49 out of 62 tests failing due to several systematic issues. This plan addresses each issue in order of priority and dependency.

## Issue Summary
- **Backend Tests**: 49/62 failing (21% pass rate)
- **Frontend Tests**: Configuration issues preventing execution
- **GitHub Actions**: Environment and path configuration problems

## Resolution Plan

### Phase 1: Core Model/Factory Issues (CRITICAL)
**Priority**: HIGH - Blocks all hint-related tests

#### Issue 1.1: Invalid 'order' field in HintFactory
- **Problem**: `tests/factories.py` HintFactory tries to create ProblemHint objects with non-existent 'order' field
- **Impact**: All hint system tests fail with `TypeError: ProblemHint() got unexpected keyword arguments: 'order'`
- **Files Affected**: `tests/factories.py`
- **Solution**: Remove `order=1`, `order=2`, `order=3` parameters from all ProblemHint.objects.create() calls
- **Tests Fixed**: ~30+ hint-related tests

### Phase 2: GitHub Actions Configuration (HIGH)
**Priority**: HIGH - Prevents CI/CD pipeline

#### Issue 2.1: Django Settings Configuration
- **Problem**: GitHub Actions not properly setting DJANGO_SETTINGS_MODULE environment
- **Impact**: Tests can't find Django configuration in CI
- **Files Affected**: `.github/workflows/tests.yml`
- **Solution**: Ensure DJANGO_SETTINGS_MODULE is exported before pytest execution
- **Verification**: Check if tests run in CI environment

#### Issue 2.2: Working Directory Issues  
- **Problem**: pytest can't find tests/ directory in CI context
- **Impact**: "ERROR: file or directory not found: tests/"
- **Files Affected**: `.github/workflows/tests.yml`
- **Solution**: Verify working directory and test path configuration
- **Verification**: Confirm tests/ directory is accessible in CI

### Phase 3: Frontend Test Configuration (MEDIUM)
**Priority**: MEDIUM - Secondary to backend functionality

#### Issue 3.1: NPM Cache Dependency Path
- **Problem**: "Some specified paths were not resolved, unable to cache dependencies"
- **Impact**: Frontend dependency caching fails, slows CI
- **Files Affected**: `.github/workflows/tests.yml`
- **Solution**: Verify package-lock.json path: `purplex/client/package-lock.json`
- **Verification**: Check if npm cache works properly

### Phase 4: Remaining Test Issues (LOW)
**Priority**: LOW - Address after core issues resolved

#### Issue 4.1: Individual Test Logic Problems
- **Problem**: After fixing factory issues, some tests may still fail due to logic problems
- **Impact**: Reduced test coverage and confidence
- **Files Affected**: Various test files in `tests/unit/` and `tests/integration/`
- **Solution**: Debug individual failing tests after factory fix
- **Verification**: Achieve >90% test pass rate

## Execution Order

1. **Fix HintFactory** (5 minutes)
   - Remove 'order' field from all hint creation calls
   - Test locally to verify fix

2. **Fix GitHub Actions Django Settings** (10 minutes)
   - Update workflow to properly export DJANGO_SETTINGS_MODULE
   - Ensure PostgreSQL connection string is correct

3. **Verify CI Test Execution** (5 minutes)
   - Push changes and monitor GitHub Actions
   - Confirm tests can execute in CI environment

4. **Fix Frontend Dependencies** (5 minutes)
   - Correct package-lock.json path in workflow
   - Test npm cache functionality

5. **Address Remaining Test Failures** (Variable time)
   - Investigate and fix individual test logic issues
   - Ensure comprehensive test coverage

## Success Criteria

- [ ] Backend tests achieve >90% pass rate locally
- [ ] GitHub Actions successfully runs tests without environment errors
- [ ] Frontend test configuration works (even if skipped due to no tests)
- [ ] CI pipeline completes without configuration failures
- [ ] All critical functionality (hint system, progress tracking) properly tested

## Risk Assessment

- **Low Risk**: Factory field fix - straightforward removal
- **Medium Risk**: GitHub Actions configuration - may require iteration
- **Low Risk**: Frontend dependencies - configuration only
- **Variable Risk**: Individual test fixes - depends on underlying logic issues

## Timeline Estimate

- **Phase 1**: 5 minutes
- **Phase 2**: 15 minutes  
- **Phase 3**: 5 minutes
- **Phase 4**: 30-60 minutes (variable)
- **Total**: 55-85 minutes

This plan prioritizes getting the test infrastructure working before addressing individual test logic issues.