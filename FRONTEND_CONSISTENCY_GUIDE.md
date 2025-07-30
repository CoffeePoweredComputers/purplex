# Frontend Consistency Guide for Purplex

This guide documents the established design system, patterns, and conventions used throughout the Purplex frontend. It serves as a reference for maintaining visual and behavioral consistency across all UI components.

## Core Design System

### CSS Architecture

The project uses a **CSS Variables-based design system** defined in `App.vue` that provides consistent theming across all components.

#### Color System

```css
/* Primary Brand Colors */
--color-primary: #800080;
--color-primary-hover: #9b009b;
--color-primary-gradient-start: #667eea;
--color-primary-gradient-end: #764ba2;

/* Background Hierarchy */
--color-bg-main: #242424;          /* Main app background */
--color-bg-dark: #1a1a1a;          /* Darker sections */
--color-bg-panel: #1e1e1e;         /* Card/panel backgrounds */
--color-bg-panel-light: #1f1f1f;   /* Lighter panel variant */
--color-bg-header: #191919;        /* Header backgrounds */
--color-bg-table: #272727;         /* Table backgrounds */
--color-bg-hover: #2a2a2a;         /* Hover states */
--color-bg-input: #333;            /* Input backgrounds */
--color-bg-border: #444;           /* Border colors */
--color-bg-disabled: #555;         /* Disabled states */

/* Text Hierarchy */
--color-text-primary: #ffffff;     /* Main text */
--color-text-secondary: #e0e0e0;   /* Secondary text */
--color-text-tertiary: #ddd;       /* Tertiary text */
--color-text-muted: #999;          /* Muted/disabled text */

/* Status Colors */
--color-success: #4CAF50;
--color-warning: #FFC107;
--color-error: #dc3545;
--color-info: #2196F3;
```

#### Spacing System

```css
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 12px;
--spacing-base: 15px;
--spacing-lg: 20px;
--spacing-xl: 30px;
--spacing-xxl: 50px;
```

#### Typography Scale

```css
--font-size-xs: 0.75rem;
--font-size-sm: 0.85rem;
--font-size-base: 1rem;
--font-size-md: 1.125rem;
--font-size-lg: 1.5rem;
--font-size-xl: 1.75rem;
--font-size-xxl: 2rem;
```

#### Border Radius System

```css
--radius-xs: 4px;
--radius-sm: 5px;
--radius-base: 8px;
--radius-lg: 12px;
--radius-xl: 20px;
--radius-round: 30px;
--radius-circle: 50%;
```

#### Shadow System

```css
--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
--shadow-base: 0 4px 12px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 10px rgba(0, 0, 0, 0.3);
--shadow-lg: 0 8px 25px rgba(0, 0, 0, 0.4);
--shadow-colored: 0 4px 15px rgba(102, 126, 234, 0.3);
```

### Component Styling Patterns

#### 1. Scoped Styles
All Vue components use `<style scoped>` to ensure styles don't leak globally.

#### 2. Dark Theme Only
The application exclusively uses a dark theme. All components should use the CSS variables defined above for consistent theming.

#### 3. Base Element Styling
- Buttons inherit consistent base styles from `style.css`
- Inputs and form elements use unified styling
- Links use the primary gradient colors

#### 4. Component Structure Pattern
```vue
<template>
  <!-- Semantic HTML structure -->
</template>

<script lang="ts">
// TypeScript by default for new components
</script>

<style scoped>
/* Component-specific styles using CSS variables */
</style>
```

### Interactive Elements & Animations

#### Transitions
```css
--transition-fast: all 0.2s ease;
--transition-base: all 0.3s ease;
--transition-slow: all 0.5s ease;
```

#### Common Hover Effects
1. **Buttons**: 
   - Transform: `translateY(-1px)` or `translateY(-2px)` for primary actions
   - Shadow increase from `--shadow-base` to `--shadow-md`
   - Background color change using hover variants

2. **Cards/Panels**:
   - Subtle shadow increase
   - Border color highlight on interactive cards

3. **Navigation Items**:
   - Color transitions using CSS variables
   - Scale transformations for icon elements

#### Animation Patterns

1. **Loading Animations**:
   - Bouncing dots using keyframe animations
   - Spinning indicators for async operations

2. **Modal/Overlay Animations**:
   - Fade in/out for overlays
   - Slide up/down for modal content

3. **Notification Animations**:
   - Slide in from right
   - Fade out on dismissal

### Component Composition Patterns

#### 1. Modal Pattern
```vue
<div class="modal-overlay" @click="closeModal">
  <div class="modal-content" @click.stop>
    <div class="modal-header">
      <h2>Title</h2>
      <button class="modal-close">&times;</button>
    </div>
    <div class="modal-body">
      <!-- Content -->
    </div>
    <div class="modal-footer">
      <!-- Actions -->
    </div>
  </div>
</div>
```

#### 2. Admin Table Pattern
- Consistent table styling with hover states
- Action buttons grouped in cells
- Status badges using color system

#### 3. Form Pattern
```vue
<div class="form-group">
  <label for="fieldId">Label</label>
  <input 
    type="text" 
    id="fieldId" 
    v-model="value"
    class="form-input"
    :class="{ error: hasError }"
  >
  <span v-if="hasError" class="error-message">Error text</span>
</div>
```

### Responsive Design

#### Breakpoints
- Mobile: `max-width: 768px`
- Tablet: `768px - 1024px`
- Desktop: `> 1024px`

#### Mobile Considerations
- Reduce spacing using smaller spacing variables
- Stack horizontal layouts vertically
- Increase touch targets to minimum 44px
- Simplify navigation for mobile

### Accessibility Guidelines

1. **Focus States**: All interactive elements must have visible focus indicators using `outline`
2. **Color Contrast**: Maintain WCAG AA compliance with text/background combinations
3. **Semantic HTML**: Use proper heading hierarchy and ARIA labels where needed
4. **Keyboard Navigation**: Ensure all interactions are keyboard accessible

### Icon Usage

The project uses emoji icons for simplicity and consistency:
- 💡 Hints/Tips
- ✓ Success/Completion
- ⚠️ Errors/Warnings
- ℹ️ Information
- 📋 Copy/Clipboard
- 🔢 Numbers/Counting

### Best Practices

1. **Always use CSS variables** for colors, spacing, and shadows
2. **Maintain dark theme consistency** - no light mode variations
3. **Use semantic class names** that describe purpose, not appearance
4. **Keep animations subtle** - prioritize usability over flashiness
5. **Test responsive behavior** at all breakpoints
6. **Ensure accessibility** in all new components
7. **Follow existing patterns** when creating new components

### Component Checklist

When creating new components:
- [ ] Use CSS variables for all styling values
- [ ] Add hover/focus states for interactive elements
- [ ] Include proper transitions using transition variables
- [ ] Test responsiveness at mobile breakpoints
- [ ] Ensure keyboard navigation works
- [ ] Follow established modal/form/table patterns
- [ ] Use scoped styles
- [ ] Include proper TypeScript types
- [ ] Add accessibility attributes where needed

## Usage

This guide should be referenced when:
- Creating new components
- Modifying existing component styles
- Reviewing pull requests for UI consistency
- Onboarding new developers
- Planning UI/UX improvements

By following these guidelines, we ensure a cohesive, professional, and accessible user interface throughout the Purplex application.