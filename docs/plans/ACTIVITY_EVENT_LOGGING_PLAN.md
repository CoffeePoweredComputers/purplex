# User Activity Event Logging System

> **Status: NOT IMPLEMENTED (Planned)**
>
> Last reviewed: 2025-12-26
>
> This document outlines a proposed design for comprehensive user activity event logging.
> None of the components described below have been implemented yet.

## Overview

Design a granular event logging foundation for tracking all user actions across Purplex. This enables future dashboards and analytics to be built on top of comprehensive raw event data.

## Current State: Probe Storage

**Probes are stored in Redis only (not persistent):**
- `probe:count:{problem_id}:{user_id}` - probe counter
- `probe:history:{problem_id}:{user_id}` - last 100 queries (JSON)
- **7-day TTL** - no long-term analytics possible
- Location: `purplex/problems_app/services/probe_service.py:22-28`

## Implementation Plan

> **Note:** All phases below are proposals. Nothing has been implemented.

### Phase 1: Foundation (Core Models + API)

#### 1.1 Create UserActivityEvent Model

**New file:** `purplex/problems_app/models/activity_event.py`

```python
class UserActivityEvent(models.Model):
    """Append-only event log for all user activity."""

    # Event identity
    event_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    # Classification
    EVENT_CATEGORIES = [
        ('session', 'Session Events'),
        ('navigation', 'Navigation Events'),
        ('problem', 'Problem Interaction Events'),
        ('submission', 'Submission Events'),
        ('hint', 'Hint Events'),
        ('probe', 'Probe Events'),
        ('editor', 'Editor Events'),
        ('feedback', 'Feedback Events'),
    ]
    category = models.CharField(max_length=20, choices=EVENT_CATEGORIES, db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)

    # User context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    session_id = models.CharField(max_length=64, db_index=True)

    # Problem context (nullable for non-problem events)
    problem = models.ForeignKey('Problem', on_delete=models.SET_NULL, null=True, blank=True)
    problem_set = models.ForeignKey('ProblemSet', on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)
    submission = models.ForeignKey('Submission', on_delete=models.SET_NULL, null=True, blank=True)

    # Timing
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    client_timestamp = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)

    # Flexible payload (schema varies by event_type)
    payload = models.JSONField(default=dict, blank=True)
    client_metadata = models.JSONField(default=dict, blank=True)
```

**Indexes:**
- `[user, -timestamp]`
- `[session_id, -timestamp]`
- `[user, problem, -timestamp]`
- `[category, event_type, -timestamp]`
- `[problem, event_type, -timestamp]`

#### 1.2 Create UserSession Model

```python
class UserSession(models.Model):
    """Session metadata for grouping events."""

    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Lifecycle
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Client info
    user_agent = models.TextField(blank=True)
    viewport_width = models.IntegerField(null=True, blank=True)
    viewport_height = models.IntegerField(null=True, blank=True)

    # Aggregates (updated periodically)
    total_events = models.IntegerField(default=0)
    problems_attempted = models.IntegerField(default=0)
    submissions_made = models.IntegerField(default=0)
```

#### 1.3 Create ActivityEventService

**New file:** `purplex/problems_app/services/activity_event_service.py`

```python
class ActivityEventService:
    @classmethod
    def record_event(cls, user, session_id, category, event_type,
                     payload=None, problem=None, ...) -> UserActivityEvent:
        """Record a single activity event."""

    @classmethod
    def record_events_batch(cls, events: List[dict], user, session_id) -> int:
        """Record multiple events in single transaction (for frontend batching)."""

    @classmethod
    def get_session_events(cls, session_id, category=None, event_type=None) -> QuerySet:
        """Query events for a session."""
```

#### 1.4 Create Event API Endpoint

**New file:** `purplex/problems_app/views/activity_views.py`

```python
class ActivityEventView(APIView):
    """POST /api/problems/events/ - Record batched events from frontend."""
    permission_classes = [IsAuthenticated]
    throttle_rate = '100/minute'  # 100 batch requests/min/user

    def post(self, request):
        # Body: {"session_id": "...", "events": [...]}
        # Returns: {"recorded": int, "errors": [...]}
```

**Add to URLs:** `purplex/problems_app/urls.py`

### Phase 2: Frontend Integration

#### 2.1 Create Activity Service

**New file:** `purplex/client/src/services/activityService.ts`

```typescript
class ActivityService {
  private sessionId: string;
  private eventQueue: ActivityEvent[] = [];
  private flushInterval = 5000; // 5 seconds
  private maxQueueSize = 50;

  trackEvent(event: ActivityEvent): void;  // Queued
  trackEventImmediate(event: ActivityEvent): Promise<void>;  // Direct
  flush(): Promise<void>;  // Send queued events
  getSessionId(): string;
  endSession(): Promise<void>;
}
```

#### 2.2 Create Activity Tracking Composable

**New file:** `purplex/client/src/composables/useActivityTracking.ts`

```typescript
export function useActivityTracking(context: {
  problemSlug?: string;
  problemSetSlug?: string;
  courseId?: string;
}) {
  const trackProblemEvent = (eventType: string, payload?: any) => {...}
  const trackEditorEvent = (eventType: string, payload?: any) => {...}
  const trackNavigationEvent = (eventType: string, payload?: any) => {...}

  // Auto-track on mount/unmount
  onMounted(() => trackNavigationEvent('problem.enter'));
  onUnmounted(() => trackNavigationEvent('problem.exit', { time_on_problem_ms }));

  return { trackProblemEvent, trackEditorEvent, trackNavigationEvent };
}
```

#### 2.3 Router Integration

**Modify:** `purplex/client/src/router.ts`

Add `afterEach` hook to track `navigation.page_view` events.

### Phase 3: Integrate with Existing Systems

#### 3.1 Submission Events

**Modify:** `purplex/problems_app/views/submission_views.py`
- Record `submission.start` when submission initiated
- Record `submission.complete` on success
- Record `submission.error` on failure

#### 3.2 Hint Events

**Modify:** `purplex/problems_app/views/hint_views.py`
- Record `hint.request` when hint fetched
- Add new endpoint for `hint.feedback` (populate `was_helpful` field)

**Frontend:** Track `hint.view`, `hint.dismiss` with duration

#### 3.3 Probe Events (Dual-Write)

**Modify:** `purplex/problems_app/services/probe_service.py`

In `_record_probe()`, add after Redis storage:
```python
ActivityEventService.record_event(
    category='probe',
    event_type='probe.execute',
    payload={'inputs': probe_input, 'output': result, 'probe_index': probes_used},
    ...
)
```

This gives persistent probe analytics while Redis handles real-time limits.

## Event Taxonomy

| Category | Event Types |
|----------|-------------|
| **session** | `session.start`, `session.end`, `session.heartbeat` |
| **navigation** | `page_view`, `problem.enter`, `problem.exit`, `problem_set.enter` |
| **submission** | `submission.start`, `submission.complete`, `submission.error` |
| **hint** | `hint.request`, `hint.view`, `hint.dismiss`, `hint.feedback` |
| **probe** | `probe.execute`, `probe.result`, `probe.history_view`, `probe.limit_reached` |
| **editor** | `editor.focus`, `editor.blur`, `editor.change` |
| **feedback** | `feedback.view`, `feedback.expand_test`, `feedback.segmentation_view` |

**Problem-type specific:**
- `mcq.option_select`, `mcq.option_hover`
- `eipl.explanation_edit`, `eipl.segmentation_result`
- `refute.counterexample_input`
- `debug.fix_attempt`

## Files to Create

| File | Purpose | Status |
|------|---------|--------|
| `purplex/problems_app/models/activity_event.py` | UserActivityEvent, UserSession models | Not created |
| `purplex/problems_app/services/activity_event_service.py` | Event recording service | Not created |
| `purplex/problems_app/views/activity_views.py` | API endpoint for events | Not created |
| `purplex/problems_app/migrations/00XX_activity_events.py` | Migration (number TBD) | Not created |
| `purplex/client/src/services/activityService.ts` | Frontend event service | Not created |
| `purplex/client/src/composables/useActivityTracking.ts` | Composable for components | Not created |

## Files to Modify

| File | Changes | Status |
|------|---------|--------|
| `purplex/problems_app/models/__init__.py` | Export UserActivityEvent, UserSession | Not modified |
| `purplex/problems_app/urls.py` | Add `/api/problems/events/` route | Not modified |
| `purplex/problems_app/views/submission_views.py` | Emit submission events | Not modified |
| `purplex/problems_app/views/hint_views.py` | Emit hint events, add feedback endpoint | Not modified |
| `purplex/problems_app/services/probe_service.py` | Dual-write to events | Not modified |
| `purplex/client/src/router.ts` | Add navigation tracking | Not modified |

## Storage Considerations

- ~500 bytes per event
- ~50-100 events per user per hour
- 1000 active users = ~2-4GB/month
- Consider table partitioning by month after 6 months

## Prerequisites Before Implementation

Before implementing this plan, consider:

1. **Database capacity**: Ensure PostgreSQL is configured for high write throughput
2. **Privacy/GDPR compliance**: Activity data may require consent and retention policies
3. **Performance impact**: Batch inserts should be used to minimize API overhead
4. **Data retention policy**: Define how long events should be kept before archival/deletion
5. **Migration to next number**: The next available migration number should be checked at implementation time (currently 0023+)

## Related Documentation

- See `purplex/problems_app/services/probe_service.py` for current Redis-based probe tracking
- See `purplex/progress/` for existing progress tracking models
