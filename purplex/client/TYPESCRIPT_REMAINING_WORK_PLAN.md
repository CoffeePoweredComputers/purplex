# TypeScript Migration - Remaining Work Plan

## Executive Summary
- **21 non-critical errors** remaining (all unused imports/declarations)
- **9 Vue components** to migrate (5,353 lines total)
- **2 JavaScript test files** to convert
- **Estimated time**: 7-12 hours

## Part 1: Code Cleanup (1-2 hours)

### 1.1 Unused Imports (13 TS6133 errors)

#### Quick Fixes (< 1 minute each)
1. `src/components/__tests__/HintButton.test.ts` - Remove unused `vi` import
2. `src/composables/useEditorHints.ts` - Remove unused `ComputedRef` import
3. `src/composables/useHintTracking.ts` - Remove unused `Ref` import
4. `src/router.ts` - Remove unused `firebaseAuth` import
5. `src/router.ts` - Remove unused `from` parameter
6. `src/services/problemService.ts` - Remove unused `HintUpdateRequest` import
7. `src/utils/logger.ts` - Remove unused `entry` parameter
8. `src/utils/typeSystem.ts` - Remove unused `keyContext` parameter

#### Requires Investigation (2-3 minutes each)
9. `src/services/auth.service.ts` - Check if `createUserWithEmailAndPassword` and `signInWithEmailAndPassword` are needed
10. `src/services/pythonTutor.service.ts` - Check if `response` variable is needed
11. `src/store/courses.module.ts` - Check if `state` and `getters` parameters are needed

### 1.2 Unused Type Definitions (8 TS6196 errors)

#### Store Module Types (5 minutes total)
1. `src/store/auth.module.ts` - Remove or export `AuthGetters`, `AuthMutations`, `AuthActions`
2. `src/store/courses.module.ts` - Remove or export `CoursesGetters`, `CoursesMutations`, `CoursesActions`

#### Component Types (3 minutes total)
3. `src/composables/useEditorHints.ts` - Remove unused `ActiveHint` and `Processor` interfaces
4. `src/composables/useNotification.ts` - Remove or export `NotificationType`

## Part 2: Vue Component Migration (5-8 hours)

### 2.1 Small Components (30 minutes each, 2 hours total)
These components are under 400 lines and likely straightforward to migrate:

1. **ComprehensionBanner.vue** (319 lines)
   - Display component for comprehension feedback
   - Likely props: `message`, `type`, `visible`
   
2. **SegmentationProgressBar.vue** (328 lines)
   - Progress indicator component
   - Likely props: `progress`, `segments`, `currentSegment`
   
3. **SegmentationSection.vue** (356 lines)
   - Container for segmentation UI
   - Likely props: `segments`, `activeSegment`
   
4. **SegmentMapping.vue** (416 lines)
   - Mapping display for segments
   - Likely props: `mappings`, `highlightedSegment`

### 2.2 Medium Components (45 minutes each, 3 hours total)
These components are 400-700 lines with moderate complexity:

5. **AdminCourseStudentsModal.vue** (441 lines)
   - Modal for managing course students
   - API calls, form validation
   - Props: `courseId`, `visible`
   
6. **SegmentAnalysisButton.vue** (461 lines)
   - Button component with analysis functionality
   - Event handling, state management
   
7. **AdminCourseProblemSetsModal.vue** (656 lines)
   - Modal for managing problem sets in courses
   - Complex form handling, API integration
   
8. **SegmentAnalysisModal.vue** (685 lines)
   - Modal for displaying segment analysis
   - Complex data visualization

### 2.3 Large Component (2-3 hours)
9. **SmartTestCaseInput.vue** (1,691 lines)
   - Most complex component in the codebase
   - Recommendation: Consider refactoring while migrating
   - Break down into sub-tasks:
     - Extract types and interfaces (30 min)
     - Convert props and data (30 min)
     - Convert computed properties (30 min)
     - Convert methods (60 min)
     - Test thoroughly (30 min)

## Part 3: Test File Migration (1 hour)

### 3.1 Convert JavaScript Tests
1. **hintProcessors.test.js**
   - Convert to TypeScript syntax
   - Add proper type annotations for test utilities
   - Ensure all mocks are properly typed

2. **hintComponents.test.js**
   - Convert to TypeScript syntax
   - Add component prop types
   - Type test helper functions

## Part 4: Final Validation (1 hour)

### 4.1 Type Check
```bash
npx tsc --noEmit --skipLibCheck
# Goal: 0 errors
```

### 4.2 Build Verification
```bash
npm run build
# Ensure no build-time errors
```

### 4.3 Test Suite
```bash
npm run test
# All tests should pass
```

### 4.4 Runtime Testing
- Start dev server: `npm run dev`
- Test all major workflows:
  - Problem creation/editing
  - Hint system (all three types)
  - Course management
  - User authentication
  - Code submission and execution

## Implementation Strategy

### Phase 1: Quick Wins (Day 1, 1-2 hours)
- Clean up all unused imports and type definitions
- Run type check to confirm down to 0 errors

### Phase 2: Small Components (Day 2, 2 hours)
- Migrate the 4 small segmentation components
- Test each component after migration

### Phase 3: Medium Components (Day 3, 3 hours)
- Migrate the 4 medium-sized modal components
- Focus on proper typing of props and events

### Phase 4: Large Component (Day 4, 2-3 hours)
- Tackle SmartTestCaseInput.vue
- Consider refactoring opportunities
- Break into smaller components if beneficial

### Phase 5: Tests & Validation (Day 5, 2 hours)
- Convert test files to TypeScript
- Run full validation suite
- Document any issues found

## Risk Mitigation

### Potential Challenges
1. **SmartTestCaseInput.vue complexity**
   - Mitigation: Time-box to 3 hours, accept partial migration if needed
   
2. **Hidden dependencies in unused imports**
   - Mitigation: Test thoroughly after each removal
   
3. **Component prop drilling**
   - Mitigation: Document prop types carefully during migration

### Rollback Strategy
- Commit after each successful component migration
- Keep original `.vue` files until migration is validated
- Use git branches for major changes

## Success Metrics
- ✅ 0 TypeScript errors
- ✅ All tests passing
- ✅ Successful production build
- ✅ No runtime errors in major features
- ✅ Improved developer experience with full type safety

## Notes for Implementation
1. Always backup current state before major changes
2. Test components in isolation after migration
3. Update component tests alongside migrations
4. Document any architectural decisions made during migration
5. Consider creating shared type definitions for common patterns