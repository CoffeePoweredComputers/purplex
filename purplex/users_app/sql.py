"""
Shared SQL for UserConsent immutability trigger.

Imported by both the migration (0005) and the test fixture (conftest.py)
so the trigger definition is a single source of truth.
"""

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION prevent_userconsent_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'userconsent_immutable: DELETE blocked (GDPR Art. 7 audit trail)'
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- Allow SET_NULL on user_id only (Django FK cascade on user deletion).
        -- Every other column must remain unchanged.
        IF (NEW.user_id IS NULL AND OLD.user_id IS NOT NULL)
            AND NEW.consent_type   IS NOT DISTINCT FROM OLD.consent_type
            AND NEW.granted        IS NOT DISTINCT FROM OLD.granted
            AND NEW.granted_at     IS NOT DISTINCT FROM OLD.granted_at
            AND NEW.withdrawn_at   IS NOT DISTINCT FROM OLD.withdrawn_at
            AND NEW.ip_address     IS NOT DISTINCT FROM OLD.ip_address
            AND NEW.policy_version IS NOT DISTINCT FROM OLD.policy_version
            AND NEW.consent_method IS NOT DISTINCT FROM OLD.consent_method
        THEN
            RETURN NEW;
        END IF;

        RAISE EXCEPTION 'userconsent_immutable: UPDATE blocked (GDPR Art. 7 audit trail)'
            USING ERRCODE = '23514';
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER userconsent_immutable
    BEFORE UPDATE OR DELETE ON users_app_userconsent
    FOR EACH ROW
    EXECUTE FUNCTION prevent_userconsent_mutation();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS userconsent_immutable ON users_app_userconsent;
DROP FUNCTION IF EXISTS prevent_userconsent_mutation();
"""
