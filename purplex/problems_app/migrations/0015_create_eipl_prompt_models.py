# Migration: Create EiplProblem and PromptProblem, migrate data, remove legacy fields
#
# Uses SeparateDatabaseAndState to:
# 1. Create new tables (DB only)
# 2. Migrate data (DB only)
# 3. Remove old fields from Problem state
# 4. Add new model state

import django.db.models.deletion
from django.db import migrations, models


def migrate_eipl_prompt_data_forward(apps, schema_editor):
    """Migrate EiPL and Prompt problems from base Problem table to new tables."""
    from django.db import connection

    with connection.cursor() as cursor:
        # Check if llm_config column exists (it might not in older schemas)
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'problems_app_problem' AND column_name = 'llm_config'
        """
        )
        has_llm_config = cursor.fetchone() is not None

        # Migrate EiPL problems
        llm_config_expr = (
            "COALESCE(llm_config, '{}')::jsonb" if has_llm_config else "'{}'::jsonb"
        )
        cursor.execute(
            f"""
            INSERT INTO problems_app_eiplproblem (
                problem_ptr_id,
                reference_solution,
                function_signature,
                function_name,
                memory_limit,
                llm_config,
                segmentation_config,
                segmentation_threshold,
                requires_highlevel_comprehension
            )
            SELECT
                id,
                COALESCE(reference_solution, ''),
                COALESCE(function_signature, ''),
                COALESCE(function_name, ''),
                COALESCE(memory_limit, 128),
                {llm_config_expr},
                COALESCE(segmentation_config, '{{}}'::jsonb),
                COALESCE(segmentation_threshold, 2),
                COALESCE(requires_highlevel_comprehension, true)
            FROM problems_app_problem
            WHERE problem_type = 'eipl'
              AND NOT EXISTS (
                  SELECT 1 FROM problems_app_eiplproblem WHERE problem_ptr_id = problems_app_problem.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM problems_app_mcqproblem WHERE problem_ptr_id = problems_app_problem.id
              )
        """
        )

        # Migrate Prompt problems
        cursor.execute(
            f"""
            INSERT INTO problems_app_promptproblem (
                problem_ptr_id,
                reference_solution,
                function_signature,
                function_name,
                memory_limit,
                llm_config,
                image_url,
                image_alt_text,
                segmentation_config,
                segmentation_threshold,
                requires_highlevel_comprehension
            )
            SELECT
                id,
                COALESCE(reference_solution, ''),
                COALESCE(function_signature, ''),
                COALESCE(function_name, ''),
                COALESCE(memory_limit, 128),
                {llm_config_expr},
                COALESCE((prompt_config->>'image_url')::text, ''),
                COALESCE((prompt_config->>'image_alt_text')::text, ''),
                COALESCE(segmentation_config, '{{}}'::jsonb),
                COALESCE(segmentation_threshold, 2),
                COALESCE(requires_highlevel_comprehension, true)
            FROM problems_app_problem
            WHERE problem_type = 'prompt'
              AND NOT EXISTS (
                  SELECT 1 FROM problems_app_promptproblem WHERE problem_ptr_id = problems_app_problem.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM problems_app_mcqproblem WHERE problem_ptr_id = problems_app_problem.id
              )
        """
        )

        # Update polymorphic_ctype_id for migrated problems
        cursor.execute(
            """
            UPDATE problems_app_problem
            SET polymorphic_ctype_id = (
                SELECT id FROM django_content_type
                WHERE app_label = 'problems_app' AND model = 'eiplproblem'
            )
            WHERE id IN (SELECT problem_ptr_id FROM problems_app_eiplproblem)
        """
        )

        cursor.execute(
            """
            UPDATE problems_app_problem
            SET polymorphic_ctype_id = (
                SELECT id FROM django_content_type
                WHERE app_label = 'problems_app' AND model = 'promptproblem'
            )
            WHERE id IN (SELECT problem_ptr_id FROM problems_app_promptproblem)
        """
        )


def migrate_eipl_prompt_data_reverse(apps, schema_editor):
    """Reverse migration - not fully supported but removes child table rows."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM problems_app_promptproblem")
        cursor.execute("DELETE FROM problems_app_eiplproblem")


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0014_remove_mcq_options_from_base"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # Step 1: Create EiplProblem table (DB only, don't touch state yet)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE IF NOT EXISTS problems_app_eiplproblem (
                            problem_ptr_id INTEGER PRIMARY KEY REFERENCES problems_app_problem(id) ON DELETE CASCADE,
                            reference_solution TEXT NOT NULL,
                            function_signature TEXT NOT NULL,
                            function_name VARCHAR(50) NOT NULL DEFAULT '',
                            memory_limit INTEGER NOT NULL DEFAULT 128,
                            llm_config JSONB NOT NULL DEFAULT '{}',
                            segmentation_config JSONB NOT NULL DEFAULT '{}',
                            segmentation_threshold INTEGER NOT NULL DEFAULT 2,
                            requires_highlevel_comprehension BOOLEAN NOT NULL DEFAULT true
                        )
                    """,
                    reverse_sql="DROP TABLE IF EXISTS problems_app_eiplproblem",
                ),
            ],
            state_operations=[],
        ),
        # Step 2: Create PromptProblem table (DB only)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE IF NOT EXISTS problems_app_promptproblem (
                            problem_ptr_id INTEGER PRIMARY KEY REFERENCES problems_app_problem(id) ON DELETE CASCADE,
                            reference_solution TEXT NOT NULL,
                            function_signature TEXT NOT NULL,
                            function_name VARCHAR(50) NOT NULL DEFAULT '',
                            memory_limit INTEGER NOT NULL DEFAULT 128,
                            llm_config JSONB NOT NULL DEFAULT '{}',
                            image_url VARCHAR(200) NOT NULL,
                            image_alt_text VARCHAR(500) NOT NULL DEFAULT '',
                            segmentation_config JSONB NOT NULL DEFAULT '{}',
                            segmentation_threshold INTEGER NOT NULL DEFAULT 2,
                            requires_highlevel_comprehension BOOLEAN NOT NULL DEFAULT true
                        )
                    """,
                    reverse_sql="DROP TABLE IF EXISTS problems_app_promptproblem",
                ),
            ],
            state_operations=[],
        ),
        # Step 3: Migrate data
        migrations.RunPython(
            migrate_eipl_prompt_data_forward, migrate_eipl_prompt_data_reverse
        ),
        # Step 4: Remove legacy fields from Problem (DB and state)
        migrations.RemoveField(model_name="problem", name="problem_type"),
        migrations.RemoveField(model_name="problem", name="description"),
        migrations.RemoveField(model_name="problem", name="function_name"),
        migrations.RemoveField(model_name="problem", name="function_signature"),
        migrations.RemoveField(model_name="problem", name="reference_solution"),
        migrations.RemoveField(model_name="problem", name="memory_limit"),
        migrations.RemoveField(model_name="problem", name="completion_criteria"),
        migrations.RemoveField(model_name="problem", name="segmentation_config"),
        migrations.RemoveField(model_name="problem", name="segmentation_threshold"),
        migrations.RemoveField(
            model_name="problem", name="requires_highlevel_comprehension"
        ),
        migrations.RemoveField(model_name="problem", name="prompt_config"),
        # Step 5: Register new models in state
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="EiplProblem",
                    fields=[
                        (
                            "problem_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="problems_app.problem",
                            ),
                        ),
                        ("reference_solution", models.TextField()),
                        ("function_signature", models.TextField()),
                        ("function_name", models.CharField(blank=True, max_length=50)),
                        ("memory_limit", models.PositiveIntegerField(default=128)),
                        ("llm_config", models.JSONField(blank=True, default=dict)),
                        (
                            "segmentation_config",
                            models.JSONField(blank=True, default=dict),
                        ),
                        (
                            "segmentation_threshold",
                            models.PositiveIntegerField(default=2),
                        ),
                        (
                            "requires_highlevel_comprehension",
                            models.BooleanField(default=True),
                        ),
                    ],
                    options={
                        "verbose_name": "EiPL Problem",
                        "verbose_name_plural": "EiPL Problems",
                    },
                    bases=("problems_app.problem",),
                ),
                migrations.CreateModel(
                    name="PromptProblem",
                    fields=[
                        (
                            "problem_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="problems_app.problem",
                            ),
                        ),
                        ("reference_solution", models.TextField()),
                        ("function_signature", models.TextField()),
                        ("function_name", models.CharField(blank=True, max_length=50)),
                        ("memory_limit", models.PositiveIntegerField(default=128)),
                        ("llm_config", models.JSONField(blank=True, default=dict)),
                        ("image_url", models.URLField()),
                        (
                            "image_alt_text",
                            models.CharField(blank=True, max_length=500),
                        ),
                        (
                            "segmentation_config",
                            models.JSONField(blank=True, default=dict),
                        ),
                        (
                            "segmentation_threshold",
                            models.PositiveIntegerField(default=2),
                        ),
                        (
                            "requires_highlevel_comprehension",
                            models.BooleanField(default=True),
                        ),
                    ],
                    options={
                        "verbose_name": "Prompt Problem",
                        "verbose_name_plural": "Prompt Problems",
                    },
                    bases=("problems_app.problem",),
                ),
            ],
        ),
    ]
