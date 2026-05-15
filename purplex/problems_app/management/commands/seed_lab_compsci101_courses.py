"""
Management command to seed the six COMPSCI101A-F lab courses.

Designed for Kaitlin Riegel / Andrew Luxton-Reilly / Paul Denny's
Auckland Compsci101 hint-mechanism study, week of 2026-05-18.

The experiment uses a Latin square across three hint mechanisms
(Variable Fade, Subgoal Highlighting, Suggested Trace) on Tasks 2-4.
CodeRunner randomly assigns each student to one of COMPSCI101A..F;
the student joins that course on purplex.org and sees five problems with
the hint ordering dictated by their condition.

The five source problems are the EiPL problems used in the previous
trial (anagram-checker, count-lowercase-vowels, palindrome-checker,
valid-parentheses, reverse-words-in-a-string). All use metasyntactic
names (foo, x, y, z, ...) so the function name doesn't give the
behaviour away.

Since ProblemHint is keyed globally per problem with no per-course
config, the command clones the five sources into a fresh lab-* namespace:
two shared clones for Tasks 1 (warm-up) and 5 (free choice) carrying
all three hints, plus nine per-mechanism clones for Tasks 2-4 each
carrying exactly one hint. Hint content and segmentation examples are
copied verbatim from the sources - no fresh authoring.

Idempotent via get_or_create, wrapped in transaction.atomic.
"""

from django.core.management.base import BaseCommand

from purplex.config.environment import config

# ----------------------------------------------------------------------
# Latin-square assignment (Tasks 2-4 only)
# ----------------------------------------------------------------------
# Each row is (task2_mechanism, task3_mechanism, task4_mechanism).
# Each (task, mechanism) pair appears in exactly two of the six courses.
LATIN_SQUARE = {
    "A": ("vf", "sh", "st"),
    "B": ("vf", "st", "sh"),
    "C": ("sh", "vf", "st"),
    "D": ("sh", "st", "vf"),
    "E": ("st", "vf", "sh"),
    "F": ("st", "sh", "vf"),
}

MECHANISM_TO_HINT_TYPE = {
    "vf": "variable_fade",
    "sh": "subgoal_highlight",
    "st": "suggested_trace",
}

MECHANISM_DISPLAY = {
    "vf": "VF",
    "sh": "SH",
    "st": "ST",
}

# ----------------------------------------------------------------------
# Source-to-task mapping (the five EiPL problems from the previous trial)
# ----------------------------------------------------------------------
TASK_SOURCES = {
    1: "anagram-checker",  # warm-up,        no hints
    2: "count-lowercase-vowels",  # variable hint,  1 of 3 mechanisms
    3: "palindrome-checker",  # variable hint,  1 of 3 mechanisms
    4: "valid-parentheses",  # variable hint,  1 of 3 mechanisms
    5: "reverse-words-in-a-string",  # free choice,    all hints on
}

NO_HINT_TASKS = {1}  # warm-up — no hints offered
VARIABLE_HINT_TASKS = {2, 3, 4}  # one assigned mechanism per course
FREE_CHOICE_TASKS = {5}  # all three hints offered

# Docstring injections for sources that don't ship one in their
# reference_solution. We replace the blank line at line 2 in place so existing
# line-number refs (segmentation examples, subgoal_highlight line_start/end)
# stay valid. The other three sources already have docstrings in the form
# `""" Assume that <param> is a <type> ... """` and are left untouched.
DOCSTRING_INJECTIONS = {
    "anagram-checker": '    """ Assume that a and b are strings """',
    "palindrome-checker": '    """ Assume that x is a string """',
}


class Command(BaseCommand):
    help = (
        "Seeds six COMPSCI101A-F lab courses with Latin-squared hint mechanisms "
        "on Tasks 2-4. Sources from the five EiPL problems in demo-problem-set."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation even in non-development environment",
        )
        parser.add_argument(
            "--instructor",
            default="instructor",
            help="Username of the primary instructor for all six courses",
        )
        parser.add_argument(
            "--co-instructor",
            action="append",
            default=[],
            metavar="USERNAME",
            help=(
                "Additional username to add as primary instructor on all six "
                "courses. Repeatable. Skipped with a warning if user is missing."
            ),
        )

    def handle(self, *args, **options):
        if not config.is_development and not options["force"]:
            self.stdout.write(
                self.style.ERROR(
                    "Lab seed data can only be created in development "
                    "environment.\nUse --force to override this check."
                )
            )
            return

        if not config.is_development:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: Seeding lab data in non-development environment!"
                )
            )

        from datetime import datetime

        from django.contrib.auth.models import User
        from django.db import transaction
        from django.utils import timezone

        from purplex.problems_app.models import (
            Course,
            CourseInstructor,
            CourseInstructorRole,
            CourseProblemSet,
            EiplProblem,
            Problem,
            ProblemHint,
            ProblemSet,
            ProblemSetMembership,
            TestCase,
        )

        # ------------------------------------------------------------------
        # Look up primary instructor
        # ------------------------------------------------------------------
        try:
            instructor = User.objects.get(username=options["instructor"])
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"User '{options['instructor']}' not found. "
                    "Create the user first or pass --instructor <username>."
                )
            )
            return

        # ------------------------------------------------------------------
        # Look up co-instructors (optional, repeatable)
        # ------------------------------------------------------------------
        co_instructors = []
        missing_co_instructors = []
        for username in options["co_instructor"]:
            try:
                co_instructors.append(User.objects.get(username=username))
            except User.DoesNotExist:
                missing_co_instructors.append(username)
                self.stdout.write(
                    self.style.WARNING(
                        f"  Co-instructor '{username}' not found - skipping. "
                        "Create the user later and re-run to add them."
                    )
                )

        # ------------------------------------------------------------------
        # Sanity-check that all five source problems exist as EiPL with hints
        # ------------------------------------------------------------------
        source_problems: dict[int, EiplProblem] = {}
        for task_num, source_slug in TASK_SOURCES.items():
            try:
                source = EiplProblem.objects.get(slug=source_slug)
            except EiplProblem.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"Source EiPL problem '{source_slug}' (Task {task_num}) "
                        "not found. Check demo-problem-set is loaded."
                    )
                )
                return

            # Every source must have all three hint types defined so we can copy
            # them. Verify upfront so we fail loudly before mutating anything.
            present = set(source.hints.values_list("hint_type", flat=True))
            missing = set(MECHANISM_TO_HINT_TYPE.values()) - present
            if missing:
                self.stdout.write(
                    self.style.ERROR(
                        f"Source '{source_slug}' is missing hint type(s): "
                        f"{sorted(missing)}. Cannot clone."
                    )
                )
                return
            source_problems[task_num] = source

        # All mutations run inside one transaction so a partial failure
        # leaves no half-built state behind.
        with transaction.atomic():
            self._seed(
                instructor=instructor,
                co_instructors=co_instructors,
                source_problems=source_problems,
                Course=Course,
                CourseInstructor=CourseInstructor,
                CourseInstructorRole=CourseInstructorRole,
                CourseProblemSet=CourseProblemSet,
                EiplProblem=EiplProblem,
                Problem=Problem,
                ProblemHint=ProblemHint,
                ProblemSet=ProblemSet,
                ProblemSetMembership=ProblemSetMembership,
                TestCase=TestCase,
                timezone=timezone,
                datetime=datetime,
            )

        self._print_summary(instructor, co_instructors, missing_co_instructors)

    def _seed(
        self,
        *,
        instructor,
        co_instructors,
        source_problems,
        Course,
        CourseInstructor,
        CourseInstructorRole,
        CourseProblemSet,
        EiplProblem,
        Problem,
        ProblemHint,
        ProblemSet,
        ProblemSetMembership,
        TestCase,
        timezone,
        datetime,
    ):
        """Mutating work — runs inside transaction.atomic()."""
        # ------------------------------------------------------------------
        # 1. Clone problems
        # ------------------------------------------------------------------
        # task_clones[(task_num, mechanism_or_None)] -> cloned Problem
        # Shared tasks key mechanism as None; variable tasks key by "vf"/"sh"/"st".
        task_clones = {}

        for task_num, source in source_problems.items():
            if task_num in VARIABLE_HINT_TASKS:
                for mechanism in ("vf", "sh", "st"):
                    clone = self._clone_problem(
                        source=source,
                        slug=f"lab-task{task_num}-{mechanism}",
                        title_suffix=f" ({MECHANISM_DISPLAY[mechanism]})",
                        instructor=instructor,
                        EiplProblem=EiplProblem,
                    )
                    task_clones[(task_num, mechanism)] = clone
                    self._copy_test_cases(source, clone, TestCase)
                    self._copy_single_hint(source, clone, mechanism, ProblemHint)
            else:
                clone = self._clone_problem(
                    source=source,
                    slug=f"lab-task{task_num}",
                    title_suffix="",
                    instructor=instructor,
                    EiplProblem=EiplProblem,
                )
                task_clones[(task_num, None)] = clone
                self._copy_test_cases(source, clone, TestCase)
                if task_num in FREE_CHOICE_TASKS:
                    self._copy_all_hints(source, clone, ProblemHint)
                # NO_HINT_TASKS: deliberately no hint rows created.

        # ------------------------------------------------------------------
        # 2. Build six problem sets + memberships (5 problems each, in task order)
        # ------------------------------------------------------------------
        problem_sets: dict[str, ProblemSet] = {}
        for letter, (m2, m3, m4) in LATIN_SQUARE.items():
            slug = f"lab-compsci101-{letter.lower()}"
            ps, created = ProblemSet.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": f"COMPSCI101 Lab (Group {letter})",
                    "description": (
                        "Auckland Compsci101 hint-mechanism study lab. "
                        f"Group {letter}: Task 2 = {MECHANISM_DISPLAY[m2]}, "
                        f"Task 3 = {MECHANISM_DISPLAY[m3]}, "
                        f"Task 4 = {MECHANISM_DISPLAY[m4]}."
                    ),
                    "is_public": True,
                    "created_by": instructor,
                },
            )
            self._report("ProblemSet", slug, created)
            problem_sets[letter] = ps

            ordered_clones = [
                task_clones[(1, None)],
                task_clones[(2, m2)],
                task_clones[(3, m3)],
                task_clones[(4, m4)],
                task_clones[(5, None)],
            ]
            for idx, clone in enumerate(ordered_clones):
                _, m_created = ProblemSetMembership.objects.get_or_create(
                    problem_set=ps,
                    problem=clone,
                    defaults={"order": idx},
                )
                self._report(
                    "ProblemSetMembership", f"{slug} -> {clone.slug}", m_created
                )

        # ------------------------------------------------------------------
        # 3. Six courses + instructor + problem set link
        # ------------------------------------------------------------------
        # Due date: week after the planned 2026-05-18 lab.
        due_date = timezone.make_aware(datetime(2026, 5, 25, 23, 59, 59))

        for letter, ps in problem_sets.items():
            course_id = f"COMPSCI101{letter}"
            course, created = Course.all_objects.get_or_create(
                course_id=course_id,
                defaults={
                    "name": f"COMPSCI101 (Lab Group {letter})",
                    "description": (
                        "Compsci101 hint-mechanism study lab. Auckland 2026-05-18."
                    ),
                    "is_active": True,
                    "enrollment_open": True,
                },
            )
            self._report("Course", course_id, created)

            # If a previously soft-deleted course of this id exists, revive it.
            # `defaults` only applies on create, so a stale soft-deleted row
            # would otherwise stay hidden after get_or_create returns it.
            if not created and course.is_deleted:
                course.is_deleted = False
                course.deleted_at = None
                course.is_active = True
                course.enrollment_open = True
                course.save(
                    update_fields=[
                        "is_deleted",
                        "deleted_at",
                        "is_active",
                        "enrollment_open",
                        "updated_at",
                    ]
                )
                self.stdout.write(
                    self.style.WARNING(f"  Revived soft-deleted Course: {course_id}")
                )

            # Primary instructor
            _, ci_created = CourseInstructor.objects.get_or_create(
                course=course,
                user=instructor,
                defaults={
                    "role": CourseInstructorRole.PRIMARY,
                    "added_by": instructor,
                },
            )
            self._report(
                "CourseInstructor",
                f"{instructor.username} -> {course_id}",
                ci_created,
            )

            for co in co_instructors:
                _, co_created = CourseInstructor.objects.get_or_create(
                    course=course,
                    user=co,
                    defaults={
                        "role": CourseInstructorRole.PRIMARY,
                        "added_by": instructor,
                    },
                )
                self._report(
                    "CourseInstructor",
                    f"{co.username} -> {course_id}",
                    co_created,
                )

            # get_or_create preserves any manual edits (due_date, deadline_type)
            # between runs; update_or_create would silently revert them.
            _, cps_created = CourseProblemSet.objects.get_or_create(
                course=course,
                problem_set=ps,
                defaults={
                    "order": 1,
                    "due_date": due_date,
                    "deadline_type": "soft",
                    "is_required": True,
                },
            )
            self._report("CourseProblemSet", f"{ps.slug} -> {course_id}", cps_created)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _clone_problem(self, source, slug, title_suffix, instructor, EiplProblem):
        """Create an EiPL lab clone of an EiPL source. Idempotent via slug."""
        existing = EiplProblem.objects.filter(slug=slug).first()
        if existing:
            self._report("EiplProblem", slug, False)
            return existing

        # Inject a docstring at line 2 for sources that lack one. The blank
        # line at index 1 is replaced in place so segmentation/hint line refs
        # downstream stay valid (no shift).
        ref_sol = source.reference_solution
        if source.slug in DOCSTRING_INJECTIONS:
            lines = ref_sol.splitlines()
            if len(lines) > 1 and not lines[1].strip():
                lines[1] = DOCSTRING_INJECTIONS[source.slug]
                ref_sol = "\n".join(lines)

        clone = EiplProblem.objects.create(
            slug=slug,
            title=source.title + title_suffix,
            description=source.description,
            function_signature=source.function_signature,
            function_name=source.function_name,
            reference_solution=ref_sol,
            difficulty=source.difficulty,
            memory_limit=source.memory_limit,
            llm_config=dict(source.llm_config) if source.llm_config else {},
            completion_threshold=source.completion_threshold,
            max_attempts=source.max_attempts,
            tags=list(source.tags) if source.tags else [],
            is_active=True,
            created_by=instructor,
            # Copy segmentation verbatim from source (it already has examples,
            # threshold, enabled flag tuned for this code).
            requires_highlevel_comprehension=source.requires_highlevel_comprehension,
            segmentation_config=dict(source.segmentation_config)
            if source.segmentation_config
            else {},
            segmentation_threshold=source.segmentation_threshold,
        )
        self._report("EiplProblem", slug, True)
        clone.categories.set(source.categories.all())
        clone.prerequisites.set(source.prerequisites.all())
        return clone

    def _copy_test_cases(self, source, clone, TestCase):
        """Copy every TestCase row from source to clone. Idempotent."""
        for tc in source.test_cases.all():
            _, created = TestCase.objects.get_or_create(
                problem=clone,
                inputs=tc.inputs,
                expected_output=tc.expected_output,
                defaults={
                    "is_sample": tc.is_sample,
                    "is_hidden": tc.is_hidden,
                    "order": tc.order,
                    "description": tc.description,
                },
            )
            self._report("TestCase", f"{clone.slug}: {tc.description}", created)

    def _copy_all_hints(self, source, clone, ProblemHint):
        """Copy all three hint rows verbatim onto a shared-task clone."""
        for hint_type in MECHANISM_TO_HINT_TYPE.values():
            self._copy_hint(source, clone, hint_type, ProblemHint)

    def _copy_single_hint(self, source, clone, mechanism, ProblemHint):
        """Copy exactly one hint row onto a per-mechanism clone."""
        hint_type = MECHANISM_TO_HINT_TYPE[mechanism]
        self._copy_hint(source, clone, hint_type, ProblemHint)

    def _copy_hint(self, source, clone, hint_type, ProblemHint):
        source_hint = source.hints.get(hint_type=hint_type)
        # min_attempts=1: hints unlock after the student's first submission.
        # Overrides whatever the source had — the lab needs uniform gating.
        _, created = ProblemHint.objects.get_or_create(
            problem=clone,
            hint_type=hint_type,
            defaults={
                "is_enabled": True,
                "min_attempts": 1,
                "content": dict(source_hint.content),
            },
        )
        self._report("ProblemHint", f"{hint_type} for {clone.slug}", created)

    def _print_summary(self, instructor, co_instructors, missing_co_instructors):
        """Render the human-readable summary after the seed transaction commits."""
        course_ids = [f"COMPSCI101{letter}" for letter in LATIN_SQUARE]
        shared_task_count = len(NO_HINT_TASKS) + len(FREE_CHOICE_TASKS)
        clone_count = shared_task_count + len(VARIABLE_HINT_TASKS) * 3
        ps_count = len(LATIN_SQUARE)
        summary_lines = [
            "\nLab seed data ready!",
            f"  Courses:        {', '.join(course_ids)}",
            f"  Problem clones: {clone_count} "
            f"({shared_task_count} shared + "
            f"{len(VARIABLE_HINT_TASKS) * 3} per-mechanism)",
            f"  Problem sets:   {ps_count} (lab-compsci101-a through -f)",
            f"  Primary inst.:  {instructor.username}",
        ]
        if co_instructors:
            summary_lines.append(
                f"  Co-instructors: {', '.join(c.username for c in co_instructors)}"
            )
        if missing_co_instructors:
            summary_lines.append(
                self.style.WARNING(
                    f"  Missing users:  {', '.join(missing_co_instructors)} "
                    "(re-run after creating them)"
                )
            )
        summary_lines.append("  Due date:       2026-05-25 23:59:59")
        summary_lines.append("")
        summary_lines.append("  Sources (all EiPL, all use metasyntactic names):")
        for task_num, source_slug in TASK_SOURCES.items():
            if task_num in NO_HINT_TASKS:
                label = "warm-up, no hints"
            elif task_num in FREE_CHOICE_TASKS:
                label = "free choice, all hints"
            else:
                label = "variable hint"
            summary_lines.append(f"    Task {task_num} ({label}): {source_slug}")
        summary_lines.append("")
        summary_lines.append("  Latin square (Task 2 / Task 3 / Task 4):")
        for letter, (m2, m3, m4) in LATIN_SQUARE.items():
            summary_lines.append(
                f"    COMPSCI101{letter}: "
                f"{MECHANISM_DISPLAY[m2]} / "
                f"{MECHANISM_DISPLAY[m3]} / "
                f"{MECHANISM_DISPLAY[m4]}"
            )
        self.stdout.write(self.style.SUCCESS("\n".join(summary_lines)))

    def _report(self, model_name, identifier, created):
        """Print whether an object was created or already existed."""
        if created:
            self.stdout.write(f"  Created {model_name}: {identifier}")
        else:
            self.stdout.write(f"  Skipped {model_name}: {identifier} (already exists)")
