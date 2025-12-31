"""
Data migration to fix Problem records with NULL polymorphic_ctype_id.

When problems are created without properly using django-polymorphic's model
inheritance (e.g., via raw SQL or migrations that skip the polymorphic setup),
the polymorphic_ctype_id field may be NULL. This causes PolymorphicTypeUndefined
errors when Django tries to load these records.

This migration:
1. Finds all Problem records with NULL polymorphic_ctype_id
2. Checks which polymorphic subclass table contains the record
3. Sets the correct ContentType ID for that subclass
"""

from django.db import migrations


def fix_polymorphic_ctype_ids(apps, schema_editor):
    """Fix Problem records with NULL polymorphic_ctype_id."""
    Problem = apps.get_model("problems_app", "Problem")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Get all problem records with NULL polymorphic_ctype_id
    null_ctype_problems = Problem.objects.filter(polymorphic_ctype_id__isnull=True)
    count = null_ctype_problems.count()

    if count == 0:
        print("  No problems with NULL polymorphic_ctype_id found.")
        return

    print(f"  Found {count} problems with NULL polymorphic_ctype_id")

    # Map of subclass table names to their model names for ContentType lookup
    subclass_tables = [
        ("problems_app_eiplproblem", "eiplproblem"),
        ("problems_app_mcqproblem", "mcqproblem"),
        ("problems_app_debugfixproblem", "debugfixproblem"),
        ("problems_app_probeablecodeproblem", "probeablecodeproblem"),
        ("problems_app_probeablespecproblem", "probeablespecproblem"),
        ("problems_app_promptproblem", "promptproblem"),
        ("problems_app_refuteproblem", "refuteproblem"),
    ]

    # Cache content types
    ct_cache = {}
    for table_name, model_name in subclass_tables:
        try:
            ct = ContentType.objects.get(app_label="problems_app", model=model_name)
            ct_cache[model_name] = ct.id
        except ContentType.DoesNotExist:
            pass  # Some subclasses may not exist yet

    # For each problem with NULL ctype, check which subclass table has it
    from django.db import connection

    fixed = 0
    for problem in null_ctype_problems:
        problem_id = problem.id
        found_type = None

        # Check each subclass table
        for table_name, model_name in subclass_tables:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT 1 FROM {table_name} WHERE problem_ptr_id = %s LIMIT 1",
                    [problem_id],
                )
                if cursor.fetchone():
                    found_type = model_name
                    break

        if found_type and found_type in ct_cache:
            problem.polymorphic_ctype_id = ct_cache[found_type]
            problem.save(update_fields=["polymorphic_ctype_id"])
            fixed += 1
            print(f"    Fixed Problem #{problem_id} -> {found_type}")
        else:
            print(f"    WARNING: Could not determine type for Problem #{problem_id}")

    print(f"  Fixed {fixed} of {count} problems")


def reverse_noop(apps, schema_editor):
    """No reverse operation - we can't unset the ctype_id safely."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("problems_app", "0024_add_deadline_enforcement"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(fix_polymorphic_ctype_ids, reverse_noop),
    ]
