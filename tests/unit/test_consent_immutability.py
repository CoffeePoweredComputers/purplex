"""
Tests for UserConsent database-level immutability (GDPR Art. 7).

Three groups:
  1. Core vulnerability — prove QuerySet/raw SQL bypass Python guards.
     These should FAIL before the DB trigger exists, PASS after.
  2. Edge cases — bulk delete, SET_NULL carve-out, TRUNCATE, FK reassignment.
     Also FAIL before trigger (except SET_NULL, which tests trigger design).
  3. Regression — existing Python guards and INSERT paths still work.
     Should PASS both before and after trigger.

Note on TRUNCATE:
  PostgreSQL TRUNCATE does NOT fire row-level triggers (BEFORE DELETE FOR EACH
  ROW). It requires a separate BEFORE TRUNCATE FOR EACH STATEMENT trigger or,
  more practically, REVOKE TRUNCATE on the application DB role. A statement-level
  trigger would break pytest-django's TransactionTestCase cleanup (which uses
  TRUNCATE ... CASCADE), so REVOKE is the recommended production fix.
"""

import pytest
from django.db import IntegrityError, connection
from django.db.models import F

from purplex.users_app.models import UserConsent
from tests.factories import UserConsentFactory, UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

TABLE = "users_app_userconsent"


# ── Group 1: Core vulnerability (FAIL before trigger, PASS after) ──────


@pytest.mark.usefixtures("_userconsent_immutability_trigger")
class TestQuerySetBypassBlocked:
    """QuerySet.update() and .delete() must be blocked by the DB trigger."""

    def test_queryset_update_blocked_by_trigger(self):
        consent = UserConsentFactory()
        with pytest.raises(IntegrityError):
            UserConsent.objects.filter(pk=consent.pk).update(granted=False)

    def test_queryset_delete_blocked_by_trigger(self):
        consent = UserConsentFactory()
        with pytest.raises(IntegrityError):
            UserConsent.objects.filter(pk=consent.pk).delete()

    def test_raw_sql_update_blocked_by_trigger(self):
        consent = UserConsentFactory()
        with pytest.raises(IntegrityError):
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {TABLE} SET granted = false WHERE id = %s",
                    [consent.pk],
                )

    def test_raw_sql_delete_blocked_by_trigger(self):
        consent = UserConsentFactory()
        with pytest.raises(IntegrityError):
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {TABLE} WHERE id = %s",
                    [consent.pk],
                )

    def test_bulk_update_blocked_by_trigger(self):
        """bulk_update() is a separate API from QuerySet.update().

        It generates CASE/WHEN SQL rather than a flat SET, and Django docs
        explicitly state save() is not called. This is a distinct code path
        that must be caught by the trigger.
        """
        consent = UserConsentFactory()
        consent.granted = False
        with pytest.raises(IntegrityError):
            UserConsent.objects.bulk_update([consent], ["granted"])

    def test_f_expression_update_blocked_by_trigger(self):
        """F() expressions generate computed SQL (e.g. SET granted = NOT granted).

        Different SQL shape from literal-value updates — proves the trigger
        fires regardless of how the new value is expressed.
        """
        consent = UserConsentFactory()
        with pytest.raises(IntegrityError):
            UserConsent.objects.filter(pk=consent.pk).update(
                policy_version=F("policy_version")
            )


# ── Group 2: Edge cases (FAIL before trigger, PASS after) ─────────────


@pytest.mark.usefixtures("_userconsent_immutability_trigger")
class TestEdgeCases:
    """Bulk operations, SET_NULL carve-out, FK reassignment, and TRUNCATE."""

    def test_bulk_queryset_delete_blocked(self):
        UserConsentFactory.create_batch(3)
        with pytest.raises(IntegrityError):
            UserConsent.objects.all().delete()

    def test_update_only_user_fk_to_null_allowed(self):
        """The trigger must allow SET_NULL on user_id (Django FK cascade).

        When a user is deleted, Django fires:
            UPDATE users_app_userconsent SET user_id = NULL WHERE user_id = %s
        This is the ONE permitted mutation — the trigger must have a carve-out.
        """
        consent = UserConsentFactory()
        user_pk = consent.user.pk
        # Simulate exactly what Django's SET_NULL does
        UserConsent.objects.filter(user_id=user_pk).update(user_id=None)
        consent.refresh_from_db()
        assert consent.user_id is None

    def test_set_null_plus_data_mutation_blocked(self):
        """SET_NULL combined with other field changes must be blocked.

        If the trigger carve-out only checks "is user_id becoming NULL?" without
        verifying other columns are unchanged, an attacker could piggyback data
        mutations onto a legitimate-looking SET_NULL update.
        """
        consent = UserConsentFactory()
        user_pk = consent.user.pk
        with pytest.raises(IntegrityError):
            UserConsent.objects.filter(user_id=user_pk).update(
                user_id=None, granted=False
            )

    def test_reassign_user_fk_blocked(self):
        """Transferring a consent record to a different user must be blocked.

        user_id non-NULL → different non-NULL is not a SET_NULL cascade —
        it's ownership reassignment, which corrupts the audit trail.
        """
        consent = UserConsentFactory()
        other_user = UserFactory()
        with pytest.raises(IntegrityError):
            UserConsent.objects.filter(pk=consent.pk).update(user_id=other_user.pk)

    @pytest.mark.xfail(
        reason="TRUNCATE bypasses row-level triggers — needs REVOKE TRUNCATE on app DB role",
        strict=True,
    )
    @pytest.mark.django_db(transaction=True)
    def test_raw_sql_truncate_blocked(self):
        """TRUNCATE bypasses row-level triggers entirely in PostgreSQL.

        This is a fundamentally different code path from DELETE — PostgreSQL
        does not fire BEFORE DELETE FOR EACH ROW triggers on TRUNCATE.
        Protection requires either:
          - A BEFORE TRUNCATE FOR EACH STATEMENT trigger, or
          - REVOKE TRUNCATE on the application DB role (preferred, since a
            statement trigger would break pytest-django cleanup).
        """
        UserConsentFactory.create_batch(3)
        with pytest.raises(IntegrityError):
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE {TABLE}")


# ── Group 3: Regression (should PASS now and after trigger) ────────────


class TestRegressionGuards:
    """Existing Python guards and INSERT paths must keep working."""

    def test_new_record_creation_succeeds(self):
        consent = UserConsentFactory()
        assert consent.pk is not None
        assert UserConsent.objects.filter(pk=consent.pk).exists()

    def test_bulk_create_succeeds(self):
        user = UserFactory()
        records = [
            UserConsent(
                user=user,
                consent_type="privacy_policy",
                granted=True,
                ip_address="127.0.0.1",
                policy_version="1.0",
                consent_method="registration",
            ),
            UserConsent(
                user=user,
                consent_type="data_processing",
                granted=True,
                ip_address="127.0.0.1",
                policy_version="1.0",
                consent_method="registration",
            ),
        ]
        created = UserConsent.objects.bulk_create(records)
        assert len(created) == 2

    def test_instance_save_existing_raises_value_error(self):
        consent = UserConsentFactory()
        consent.granted = False
        with pytest.raises(ValueError, match="immutable"):
            consent.save()

    def test_instance_delete_raises_value_error(self):
        consent = UserConsentFactory()
        with pytest.raises(ValueError, match="cannot be deleted"):
            consent.delete()

    def test_update_or_create_existing_raises_value_error(self):
        """update_or_create() calls save() internally on the update path.

        Django fetches the object, sets attributes, then calls save() — so
        the Python guard catches it. This regression test ensures that if
        Django ever changes to use QuerySet.update() internally, we'd notice.
        """
        consent = UserConsentFactory()
        with pytest.raises(ValueError, match="immutable"):
            UserConsent.objects.update_or_create(
                pk=consent.pk,
                defaults={"granted": False},
            )

    def test_user_deletion_preserves_consent_via_set_null(self):
        """Deleting a user nullifies FK but leaves the consent record intact."""
        consent = UserConsentFactory()
        consent_pk = consent.pk
        user = consent.user
        user.delete()

        consent.refresh_from_db()
        assert consent.pk == consent_pk
        assert consent.user_id is None
