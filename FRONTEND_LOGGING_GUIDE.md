# Frontend Logging Guide for Purplex

## Overview

Purplex uses a three-layer logging architecture to maintain clean separation between developer logging, Vue component integration, and user notifications. This guide documents the proper usage patterns and helps standardize logging across the entire frontend codebase.

## Architecture

### Three Logging Utilities

1. **`utils/logger.ts`** - Core logging engine
   - Framework-agnostic, can be used anywhere
   - Handles log levels, formatting, and buffering
   - Environment-aware (dev vs production)

2. **`composables/useLogger.ts`** - Vue component integration
   - Auto-detects component names
   - Provides reactive logger instance
   - Component-specific convenience methods

3. **`composables/useNotification.ts`** - User notifications
   - Shows visual feedback to users
   - NOT for developer logging
   - Toast/popup messages with different durations

## Usage Patterns

### 1. Vue Components

Use the `useLogger` composable for all component logging:

```typescript
<script setup lang="ts">
import { useLogger } from '@/composables/useLogger';
import { useNotification } from '@/composables/useNotification';

const logger = useLogger();  // Auto-detects component name
const { notify } = useNotification();

// Basic logging
logger.debug('Component initialized');
logger.info('User action completed');
logger.warn('Deprecated feature used');
logger.error('Component error', error);

// Convenience methods
logger.logApiError('/api/users', error);
logger.logAsyncError('loadUserData', error);
logger.logUserAction('clicked-submit', { formData });
logger.logStateChange(oldState, newState);

// User notifications (separate from logging)
notify.success('Profile updated successfully');
notify.error('Failed to save. Please try again.');
</script>
```

### 2. Services and Utilities

Use the `log` export from utils/logger:

```typescript
// services/auth.service.ts
import { log } from '@/utils/logger';

class AuthService {
  async validateToken(): Promise<AuthResponse> {
    try {
      const response = await axios.post(API_URL, data);
      log.info('Token validated successfully');
      return response.data;
    } catch (error) {
      log.error('Token validation error', error);
      throw error;
    }
  }
}
```

### 3. Vuex Stores

```typescript
// store/courses.module.ts
import { log } from '@/utils/logger';

const actions = {
  async fetchCourses({ commit }) {
    try {
      const response = await axios.get('/api/courses/');
      commit('SET_COURSES', response.data);
    } catch (error) {
      log.error('Failed to fetch courses', error);
      throw error;
    }
  }
};
```

### 4. Combined Pattern: Log + Notify

For operations that need both developer logging and user feedback:

```typescript
// Common pattern in components
async function saveData() {
  try {
    await api.saveUserData(formData);
    logger.info('User data saved successfully');
    notify.success('Your changes have been saved');
  } catch (error) {
    // Log full error for developers
    logger.error('Failed to save user data', error);
    
    // Show user-friendly message
    notify.error('Unable to save your changes. Please try again.');
  }
}
```

## Migration Guide

#### Basic Replacements

```typescript
// In Vue Components
const logger = useLogger();
logger.info('Loading data...');
logger.error('Error', error);
logger.warn('Deprecated');
logger.debug('Debug info', data);

// In Services/Utilities
import { log } from '@/utils/logger';
log.info('Loading data...');
log.error('Error', error);
log.warn('Deprecated');
log.debug('Debug info', data);
```

#### Error Handling Patterns

```typescript
async function loadData() {
  try {
    const response = await axios.get('/api/data');
    logger.info('Data loaded successfully');
    this.data = response.data;
  } catch (error) {
    logger.error('Failed to load data', error);
    notify.error('Unable to load data. Please refresh the page.');
  }
}
```

#### API Error Handling

```typescript
try {
  await axios.post('/api/users/', userData);
  logger.info('User created successfully');
  notify.success('User account created');
} catch (error) {
  logger.logApiError('/api/users/', error);
  
  // Show specific error message if available
  const message = error.response?.data?.message || 'Failed to create user';
  notify.error(message);
}
```

## Best Practices

### 1. Log Levels Guide

- **DEBUG**: Detailed information for debugging (dev only)
  ```typescript
  logger.debug('Computed property recalculated', { oldValue, newValue });
  ```

- **INFO**: General informational messages
  ```typescript
  logger.info('User logged in', { userId: user.id });
  ```

- **WARN**: Warning messages for potentially problematic situations
  ```typescript
  logger.warn('API deprecated endpoint used', { endpoint: '/api/v1/users' });
  ```

- **ERROR**: Error messages for failures
  ```typescript
  logger.error('Failed to submit form', { error, formData });
  ```

### 2. Including Context

Always include relevant context with your logs:

```typescript
// ❌ Bad - No context
logger.error('Request failed');

// ✅ Good - Rich context
logger.error('Failed to update user profile', {
  userId: user.id,
  endpoint: '/api/users/profile',
  error: error.message,
  statusCode: error.response?.status
});
```

### 3. User vs Developer Errors

Distinguish between what developers need to see and what users should see:

```typescript
try {
  await submitOrder(orderData);
} catch (error) {
  // Full technical details for developers
  logger.error('Order submission failed', {
    error: error.stack,
    orderData,
    userId: currentUser.id,
    timestamp: new Date().toISOString()
  });
  
  // Friendly message for users
  if (error.response?.status === 402) {
    notify.error('Payment method declined. Please try another card.');
  } else {
    notify.error('Unable to process your order. Please try again.');
  }
}
```

### 4. Async Operation Patterns

```typescript
// Standard async operation with logging
async function performAsyncOperation() {
  logger.debug('Starting async operation');
  
  try {
    const result = await api.someOperation();
    logger.info('Async operation completed', { resultId: result.id });
    return result;
  } catch (error) {
    logger.logAsyncError('performAsyncOperation', error);
    throw error; // Re-throw if caller needs to handle
  }
}
```

## Quick Reference

### Import Statements

```typescript
// For Vue components
import { useLogger } from '@/composables/useLogger';
import { useNotification } from '@/composables/useNotification';

// For services/utilities/stores
import { log } from '@/utils/logger';

// In component setup
const logger = useLogger();
const { notify } = useNotification();
```

### Common Replacements

| Old Pattern | New Pattern (Component) | New Pattern (Service) |
|------------|------------------------|---------------------|
| `console.log(msg)` | `logger.info(msg)` | `log.info(msg)` |
| `console.error(msg, err)` | `logger.error(msg, err)` | `log.error(msg, err)` |
| `console.warn(msg)` | `logger.warn(msg)` | `log.warn(msg)` |
| `console.debug(msg)` | `logger.debug(msg)` | `log.debug(msg)` |
| `alert(msg)` | `notify.info(msg)` | N/A |
| `console.error(err)` + `alert(msg)` | `logger.error(msg, err)` + `notify.error(msg)` | N/A |

### Component Template

```typescript
<script setup lang="ts">
import { ref } from 'vue';
import { useLogger } from '@/composables/useLogger';
import { useNotification } from '@/composables/useNotification';

const logger = useLogger();
const { notify } = useNotification();

async function handleAction() {
  logger.logUserAction('button-clicked');
  
  try {
    const result = await performAction();
    logger.info('Action completed successfully');
    notify.success('Changes saved');
  } catch (error) {
    logger.error('Action failed', error);
    notify.error('Something went wrong. Please try again.');
  }
}
</script>
```

## Enforcement

To maintain consistency:

1. **No console.* statements** should appear in production code
2. **All async operations** must have try-catch with proper logging
3. **User-facing errors** must use the notification system
4. **Component names** should be auto-detected (don't pass manually)
5. **Context should be included** in all error logs

## Examples from Codebase

### Good Example: auth.service.ts
```typescript
async validateToken(): Promise<AuthResponse> {
  try {
    const user = firebaseAuth.currentUser;
    if (!user) {
      return { authenticated: false };
    }
    
    const token = await getIdToken(user);
    const response = await axios.post(API_URL, {}, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    return response.data;
  } catch (error: any) {
    log.error('Token validation error', error);
    return { authenticated: false, error: error.message };
  }
}
```

### Good Example: submissionService.ts
```typescript
async getSubmissionsSummary(): Promise<SubmissionSummary[]> {
  try {
    const response = await axios.get(`${this.baseURL}/submissions/summary/`);
    return response.data;
  } catch (error) {
    log.error('Failed to fetch submissions summary', error);
    throw error;
  }
}
```

## Troubleshooting

### Logger not working?
1. Check import path is correct
2. Ensure you're using the right utility for your context
3. Remember logs only show in console for DEBUG/INFO in development

### Notifications not showing?
1. Verify window.$notify is initialized (check App.vue)
2. Check notification component is mounted
3. Ensure you're destructuring notify: `const { notify } = useNotification()`

### Component name shows as "UnknownComponent"?
1. Make sure you're using `<script setup>` or defining component name
2. Call useLogger inside setup() function
3. Don't pass component name manually unless necessary

---

*Last updated: January 2025*
*Last compliance check: January 29, 2025*
*Status: Migration 99% complete - 2 console.error statements remain in AdminProblems.vue (lines 144, 225)*
