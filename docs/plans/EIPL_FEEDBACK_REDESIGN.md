# EiPL Feedback Panel Redesign

> **Status: IMPLEMENTED**
>
> This design has been fully implemented. See the Implementation Status section at the end for details.

## Overview

This document outlines a redesigned feedback panel for EiPL (Explain in Plain Language) and Prompt problem types. The goal is to reduce cognitive load for novices by presenting feedback as two clear, scannable progress bars with modal drill-downs.

## Core Concept

Two clickable progress bars that give an instant "how am I doing" read, with modals for detailed information. The bars fill left-to-right toward the goal, with color indicating status.

### Key Insight: Unified Correctness/Ambiguity Model

Correctness and ambiguity are not independent dimensions—they're points on a single spectrum:

| State | Variants Passing | Meaning |
|-------|------------------|---------|
| **Incorrect** | 0/N | Explanation doesn't produce working code |
| **Correct but Ambiguous** | 1 to N-1 | Works but could be misinterpreted |
| **Correct and Clear** | N/N | Reliably produces working code |

**Abstraction** is a separate dimension that only unlocks when correctness reaches 100%.

---

## Main Panel States

### State 1: Incorrect (0/3 pass)

```
┌─────────────────────────────────────────────────────────┐
│  Feedback                              Attempt 3/5  42% │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 💭  "Loop through the array and return the      │    │
│  │     biggest number"                              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  CORRECTNESS                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  ✗  Not yet working                    0/3 pass │    │
│  │     None of the versions passed the tests        │    │
│  │                                              ›   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ABSTRACTION                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  🔒  Locked                                      │    │
│  │     Unlocks when all versions pass               │    │
│  │                                                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### State 2: Ambiguous (2/3 pass)

```
┌─────────────────────────────────────────────────────────┐
│  Feedback                              Attempt 3/5  67% │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 💭  "Use binary search by checking the middle   │    │
│  │     and narrowing the range until found"         │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  CORRECTNESS                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  ~  Works, but ambiguous               2/3 pass │    │
│  │     One version interpreted it differently       │    │
│  │                                              ›   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ABSTRACTION                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  🔒  Locked                                      │    │
│  │     Unlocks when all versions pass               │    │
│  │                                                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### State 3a: Clear but Too Detailed

```
┌─────────────────────────────────────────────────────────┐
│  Feedback                              Attempt 3/5  85% │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 💭  "Set left to 0, right to length minus 1.    │    │
│  │     While left <= right, calculate mid as       │    │
│  │     (left + right) / 2. Compare and adjust..."  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  CORRECTNESS                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │████████████████████████████████████████░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  ✓  Clear                              3/3 pass │    │
│  │     All versions produced working code           │    │
│  │                                              ›   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ABSTRACTION                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  ✗  Too detailed                    5 segments  │    │
│  │     Describe the goal, not the steps   (want 2) │    │
│  │                                              ›   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### State 3b: Fully Successful

```
┌─────────────────────────────────────────────────────────┐
│  Feedback                             Attempt 3/5  100% │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 💭  "Efficiently finds a target in a sorted     │    │
│  │     list by repeatedly halving the search       │    │
│  │     space"                                       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  CORRECTNESS                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │████████████████████████████████████████░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  ✓  Clear                              3/3 pass │    │
│  │     All versions produced working code           │    │
│  │                                              ›   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ABSTRACTION                                     │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │████████████████████████████████████████░░│   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │  ✓  High-level                      2 segments  │    │
│  │     Focused on purpose, not implementation       │    │
│  │                                              ›   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Progress Bar Styling

### Color States

| Bar State | Fill Level | Color |
|-----------|------------|-------|
| 0% (none pass) | Empty | Red border |
| 33-67% (some pass) | Partial | Yellow/Amber |
| 100% (all pass) | Full | Green |
| Locked | Empty | Gray |

### Status Icons

| Status | Icon | Label |
|--------|------|-------|
| Failing | ✗ | "Not yet working" |
| Partial | ~ | "Works, but ambiguous" |
| Passing | ✓ | "Clear" / "High-level" |
| Locked | 🔒 | "Locked" |

---

## Correctness Modal

Triggered by clicking the correctness card. Shows variant comparison and test details.

### Viewing a Passing Version

```
┌─────────────────────────────────────────────────────────────────┐
│  Correctness Details                                        ✕   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  I generated 3 code versions from your explanation.              │
│                                                                  │
│  ┌───────────────┬───────────────┬───────────────┐              │
│  │   VERSION 1   │   VERSION 2   │   VERSION 3   │              │
│  │       ✓       │       ✓       │       ✗       │              │
│  │    5/5 pass   │    5/5 pass   │    3/5 pass   │              │
│  └───────────────┴───────────────┴───────────────┘              │
│          ▲                                                       │
│       viewing                                                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  def binary_search(arr, target):                          │  │
│  │      left, right = 0, len(arr) - 1                        │  │
│  │      while left <= right:                                 │  │
│  │          mid = (left + right) // 2                        │  │
│  │          if arr[mid] == target:                           │  │
│  │              return mid                                   │  │
│  │          elif arr[mid] < target:                          │  │
│  │              left = mid + 1                               │  │
│  │          else:                                            │  │
│  │              right = mid - 1                              │  │
│  │      return -1                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  TESTS                                           5/5 pass │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │  ✓  binary_search([1,2,3,4,5], 3)  →  2                   │  │
│  │  ✓  binary_search([1,2,3,4,5], 1)  →  0                   │  │
│  │  ✓  binary_search([1,2,3,4,5], 5)  →  4                   │  │
│  │  ✓  binary_search([1,2,3,4,5], 6)  →  -1                  │  │
│  │  ✓  binary_search([], 1)           →  -1                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Viewing a Failing Version

```
┌─────────────────────────────────────────────────────────────────┐
│  Correctness Details                                        ✕   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  I generated 3 code versions from your explanation.              │
│                                                                  │
│  ┌───────────────┬───────────────┬───────────────┐              │
│  │   VERSION 1   │   VERSION 2   │   VERSION 3   │              │
│  │       ✓       │       ✓       │       ✗       │              │
│  │    5/5 pass   │    5/5 pass   │    3/5 pass   │              │
│  └───────────────┴───────────────┴───────────────┘              │
│                                          ▲                       │
│                                       viewing                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  def binary_search(arr, target):                          │  │
│  │      left, right = 0, len(arr)        # off by one        │  │
│  │      while left < right:              # != versions 1,2   │  │
│  │          mid = (left + right) // 2                        │  │
│  │          ...                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  💡 WHY THIS VERSION FAILED                               │  │
│  │                                                           │  │
│  │  "Narrowing the range" was interpreted as while left <    │  │
│  │  right instead of while left <= right, missing the edge   │  │
│  │  case when the target is at the boundary.                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  TESTS                                           3/5 pass │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │  ✓  binary_search([1,2,3,4,5], 3)  →  2                   │  │
│  │  ✓  binary_search([1,2,3,4,5], 1)  →  0                   │  │
│  │  ✗  binary_search([1,2,3,4,5], 5)  expected 4, got -1     │  │
│  │  ✓  binary_search([1,2,3,4,5], 6)  →  -1                  │  │
│  │  ✗  binary_search([], 1)           expected -1, got error │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│                                              [Debug in PyTutor]  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Abstraction Modal

Triggered by clicking the abstraction card. Shows segment mapping between explanation and code.

```
┌─────────────────────────────────────────────────────────────────┐
│  Abstraction Details                                        ✕   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ✗  You described 5 steps — aim for 2 or fewer.           │  │
│  │                                                           │  │
│  │  Focus on WHAT the code accomplishes, not HOW it works.   │  │
│  │                                                           │  │
│  │  Try: "Efficiently finds a target by repeatedly halving   │  │
│  │  the search space."                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────┬──────────────────────────────┐  │
│  │  YOUR EXPLANATION          │  REFERENCE CODE              │  │
│  ├────────────────────────────┼──────────────────────────────┤  │
│  │                            │                              │  │
│  │  ① Set left to 0, right    │   1│ def binary_search():   │  │
│  │     to length minus 1      │   2│     left = 0      ← ①  │  │
│  │                            │   3│     right = len()-1    │  │
│  │                            │   4│                        │  │
│  │  ② While left <= right     │   5│     while left<=right: │  │
│  │                            │   6│                   ← ②  │  │
│  │                            │   7│                        │  │
│  │  ③ Calculate mid as        │   8│         mid = (l+r)//2 │  │
│  │     (left + right) / 2     │   9│                   ← ③  │  │
│  │                            │  10│                        │  │
│  │  ④ If target equals mid    │  11│         if arr[mid]==t:│  │
│  │     value, return mid      │  12│             return mid │  │
│  │                            │  13│                   ← ④  │  │
│  │                            │  14│                        │  │
│  │  ⑤ Otherwise adjust left   │  15│         elif ...:      │  │
│  │     or right               │  16│             left=mid+1 │  │
│  │                            │  17│         else:          │  │
│  │                            │  18│             right=mid-1│  │
│  │                            │  19│                   ← ⑤  │  │
│  │                            │  20│                        │  │
│  └────────────────────────────┴──────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Interaction

- Hovering over a segment number (①②③④⑤) on either side highlights the corresponding lines/text on the other side
- Color-coded segment markers (subway map style from existing implementation)

---

## Component Architecture

### Main Components

| Component | Purpose | Interaction | Status |
|-----------|---------|-------------|--------|
| `Feedback.vue` | Container with explanation + two cards | — | **Implemented** |
| *(inline)* Explanation Section | Display student's submission | Read-only | **Implemented** |
| *(inline)* Correctness Card | Progress bar + status + summary | Click → modal | **Implemented** |
| *(inline)* Abstraction Card | Progress bar + status (or locked) | Click → modal | **Implemented** |
| `CorrectnessModal.vue` | Version tabs, code, test results | Tab between versions | **Implemented** |
| `SegmentAnalysisModal.vue` | Segment mapping with hover highlighting | Hover to highlight | **Implemented** |

**Note:** The design proposed separate components (`FeedbackPanel.vue`, `ExplanationBox.vue`, `CorrectnessCard.vue`, `AbstractionCard.vue`), but the implementation consolidated these into a single `Feedback.vue` component with inline sections. This is functionally equivalent and reduces component overhead.

### Actual Data Flow

```
Feedback.vue
├── (inline) Explanation Section
│   └── props: userPrompt
├── (inline) Correctness Card (metric-card)
│   └── computed: variants[], correctnessStatus, correctnessFill
│   └── click: opens CorrectnessModal
├── (inline) Abstraction Card (metric-card)
│   └── computed: segmentation, isAbstractionLocked, abstractionFill
│   └── click: opens SegmentAnalysisModal (when unlocked)
├── CorrectnessModal
│   └── props: variants[], selectedVersion, isVisible
│   └── emits: @close, @update:selectedVersion, @debug
├── PyTutorModal
│   └── props: pythonTutorUrl, isVisible
│   └── emits: @close
└── SegmentAnalysisModal
    └── props: segmentation, referenceCode, userPrompt, isVisible
    └── emits: @close
```

---

## Design Rationale

### Why Two Bars?

1. **Glanceable**: Students see status instantly without reading
2. **Progressive**: Clear path from "not working" → "working" → "excellent"
3. **Gated**: Abstraction only matters after correctness, so it locks

### Why Modals for Details?

1. **Reduces initial overwhelm**: Main panel stays clean
2. **Consistent pattern**: Both dimensions work the same way
3. **Focus**: When debugging, student focuses on one thing

### Why Combined Correctness/Ambiguity?

1. **Mental model matches reality**: "Some of my code versions failed" is intuitive
2. **Simpler UI**: One bar instead of two
3. **Clearer action**: "Make it clearer" vs "fix correctness AND ambiguity"

---

## Implementation Notes

> **Status: IMPLEMENTED** - See actual implementation in `Feedback.vue`

### Scoring Logic

**Correctness Bar Fill:** (implemented in `correctnessFill` computed)
```typescript
// Actual implementation:
correctnessFill(): number {
  if (this.totalVariants === 0) return 0
  return (this.passingVariants / this.totalVariants) * 100
}
```

**Abstraction Bar Fill:** (implemented in `abstractionFill` computed)
```typescript
// Actual implementation:
abstractionFill(): number {
  if (this.isAbstractionLocked) return 0
  if (this.segmentCount <= 2) return 100
  return Math.max(0, 100 - (this.segmentCount - 2) * 20)
}
```

### Status Determination

**Correctness Status:** (implemented in `correctnessStatus` computed)
```typescript
// Actual implementation:
correctnessStatus(): { icon: string; label: string; description: string } {
  if (this.passingVariants === 0) {
    return { icon: '✗', label: 'Not yet working', description: 'None of the versions passed the tests' }
  }
  if (this.passingVariants < this.totalVariants) {
    return { icon: '~', label: 'Works, but ambiguous', description: 'One version interpreted it differently' }
  }
  return { icon: '✓', label: 'Clear', description: 'All versions produced working code' }
}
```

**Abstraction Status:** (implemented in `abstractionStatus` computed)
```typescript
// Actual implementation:
abstractionStatus(): { icon: string; label: string; description: string } {
  if (this.isAbstractionLocked) {
    return { icon: '🔒', label: 'Locked', description: 'Unlocks when all versions pass' }
  }
  if (this.segmentCount <= 2) {
    return { icon: '✓', label: 'High-level', description: 'Focused on purpose, not implementation' }
  }
  return { icon: '✗', label: 'Too detailed', description: 'Describe the goal, not the steps' }
}
```

**Abstraction Lock Logic:** (implemented in `isAbstractionLocked` computed)
```typescript
// Actual implementation:
isAbstractionLocked(): boolean {
  // Lock abstraction when not all variants pass OR segmentation is disabled
  return !this.allVariationsPass || !this.segmentationEnabled
}
```

---

## Migration from Current Design

> **Status: COMPLETE** - All migrations have been executed.

### Components Removed/Replaced

- ~~`ComprehensionBanner.vue`~~ → **Kept but deprecated** - Abstraction card is now inline in `Feedback.vue`
- ~~`LockedSegmentationBanner.vue`~~ → **Kept but deprecated** - Locked state handled inline in `Feedback.vue`
- ~~Timeline nodes in `Feedback.vue`~~ → **Replaced** with metric cards (correctness + abstraction)
- ~~Inline test results~~ → **Moved** to `CorrectnessModal.vue`

### Components Kept/Adapted

- `SegmentAnalysisModal.vue` → **Kept** with simplified header and segment mapping
- `SegmentMapping.vue` → **Kept** with subway-map style segment markers
- `PyTutorModal.vue` → **Kept**, triggered from correctness modal debug flow

---

## Open Questions

> **Status: RESOLVED** - All open questions have been addressed.

1. **"Why this failed" explanation**: ~~Should this be AI-generated or templated?~~
   - **Resolution:** Currently uses templated summary messages based on status. AI-generated explanations were not implemented. The `CorrectnessModal` shows variant tabs with code and test results, allowing users to see what failed directly.

2. **Diff highlighting**: ~~Should we visually diff passing vs failing versions?~~
   - **Resolution:** Not implemented. Users can switch between version tabs to compare manually. Code is displayed with syntax highlighting in the Ace editor.

3. **Score calculation**: ~~How exactly should abstraction % map from segment count?~~
   - **Resolution:** Implemented as: `if (segmentCount <= 2) return 100; return Math.max(0, 100 - (segmentCount - 2) * 20)`

4. **Animation**: ~~Should bars animate when filling?~~
   - **Resolution:** Yes, implemented with CSS transition: `transition: width 0.4s ease;`

---

## Implementation Status

### Summary

The EiPL Feedback Panel redesign has been **fully implemented** and is live in the codebase.

### Key Files

| File | Path | Purpose |
|------|------|---------|
| Feedback.vue | `purplex/client/src/components/Feedback.vue` | Main feedback panel with two metric cards |
| CorrectnessModal.vue | `purplex/client/src/modals/CorrectnessModal.vue` | Detailed correctness analysis with version tabs |
| SegmentAnalysisModal.vue | `purplex/client/src/components/segmentation/SegmentAnalysisModal.vue` | Abstraction details with segment mapping |
| SegmentMapping.vue | `purplex/client/src/components/segmentation/SegmentMapping.vue` | Subway-map style segment visualization |
| PyTutorModal.vue | `purplex/client/src/modals/PyTutorModal.vue` | Python Tutor integration for debugging |

### Implementation Matches Design

| Design Feature | Implementation Status | Notes |
|----------------|----------------------|-------|
| Two progress bars (Correctness + Abstraction) | **Implemented** | Inline in Feedback.vue as `.metric-card` buttons |
| Unified Correctness/Ambiguity model | **Implemented** | `correctnessStatus` computed property handles all states |
| Abstraction locked until 100% correctness | **Implemented** | `isAbstractionLocked` computed property |
| Modal drill-downs for details | **Implemented** | CorrectnessModal + SegmentAnalysisModal |
| Version tabs in Correctness Modal | **Implemented** | Pills with passing/failing indicators |
| Code display with test results | **Implemented** | Two-column layout with Ace editor |
| Segment mapping with hover highlighting | **Implemented** | Subway-map style markers with color coordination |
| Next Step Banner | **Implemented** | Dynamic urgency-based CTAs |
| Attempt history selector | **Implemented** | Dropdown in header with score badges |

### Minor Deviations from Design

1. **Component consolidation:** Design proposed 6 separate components; implementation uses single `Feedback.vue` with inline sections.

2. **Modal naming:** Design called it `AbstractionModal.vue`; implemented as `SegmentAnalysisModal.vue` (kept existing name).

3. **Debug flow:** Design showed "Debug in PyTutor" button in correctness modal; implemented but the `_handleDebug` method is prefixed with underscore (currently unused in template - PyTutor triggered from parent).

4. **"Why this failed" section:** Design showed AI-generated explanations for failing versions; implementation shows templated summary messages instead.

### Additional Features Not in Original Design

1. **Modal size controls** - Small/Medium/Large/Fullscreen presets with persistence
2. **Submission history** - Full attempt history dropdown with score badges
3. **Open in new tab** - Segment analysis can be opened in new window
4. **Loading states** - Skeleton UI during navigation and "Generating feedback" panel
5. **Accessibility** - ARIA labels, focus traps, keyboard navigation, screen reader announcements
