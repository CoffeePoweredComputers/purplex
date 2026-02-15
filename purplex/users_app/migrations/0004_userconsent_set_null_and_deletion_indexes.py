"""
Migration to:
1. Change UserConsent.user FK from CASCADE to SET_NULL (GDPR Art. 7 audit trail)
2. Add indexes on UserProfile deletion fields for cleanup queries
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users_app", "0003_userprofile_deletion_requested_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Change UserConsent.user from CASCADE to SET_NULL
        migrations.AlterField(
            model_name="userconsent",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="consents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Add index on deletion_requested_at for cleanup query performance
        migrations.AddIndex(
            model_name="userprofile",
            index=models.Index(
                fields=["deletion_requested_at"],
                name="users_app_p_deletion_req_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userprofile",
            index=models.Index(
                fields=["deletion_scheduled_at"],
                name="users_app_p_deletion_sched_idx",
            ),
        ),
    ]
