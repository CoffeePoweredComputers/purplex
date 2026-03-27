"""
Shared SQL for ActivityEvent immutability trigger.

Imported by both the migration (0012) and the test fixture (conftest.py)
so the trigger definition is a single source of truth.
"""

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION prevent_activityevent_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'activityevent_immutable: DELETE blocked (research data)'
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- Allow SET_NULL on FK columns only (Django on_delete=SET_NULL).
        -- At least one FK must actually be transitioning non-NULL -> NULL,
        -- and every non-FK column must remain unchanged.
        IF (
            -- Each FK either stays the same or goes from non-NULL to NULL
            (NEW.user_id IS NULL OR NEW.user_id IS NOT DISTINCT FROM OLD.user_id)
            AND (NEW.problem_id IS NULL OR NEW.problem_id IS NOT DISTINCT FROM OLD.problem_id)
            AND (NEW.course_id IS NULL OR NEW.course_id IS NOT DISTINCT FROM OLD.course_id)
            -- At least one FK actually changed (not a no-op)
            AND (
                (NEW.user_id IS NULL AND OLD.user_id IS NOT NULL)
                OR (NEW.problem_id IS NULL AND OLD.problem_id IS NOT NULL)
                OR (NEW.course_id IS NULL AND OLD.course_id IS NOT NULL)
            )
            -- All non-FK columns unchanged
            AND NEW.event_type        IS NOT DISTINCT FROM OLD.event_type
            AND NEW.timestamp         IS NOT DISTINCT FROM OLD.timestamp
            AND NEW.payload           IS NOT DISTINCT FROM OLD.payload
            AND NEW.anonymous_user_id IS NOT DISTINCT FROM OLD.anonymous_user_id
            AND NEW.schema_version    IS NOT DISTINCT FROM OLD.schema_version
            AND NEW.idempotency_key   IS NOT DISTINCT FROM OLD.idempotency_key
        )
        THEN
            RETURN NEW;
        END IF;

        RAISE EXCEPTION 'activityevent_immutable: UPDATE blocked (research data)'
            USING ERRCODE = '23514';
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS activityevent_immutable ON submissions_activityevent;
CREATE TRIGGER activityevent_immutable
    BEFORE UPDATE OR DELETE ON submissions_activityevent
    FOR EACH ROW
    EXECUTE FUNCTION prevent_activityevent_mutation();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS activityevent_immutable ON submissions_activityevent;
DROP FUNCTION IF EXISTS prevent_activityevent_mutation();
"""
