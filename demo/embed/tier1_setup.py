"""
Tier 1 demo setup: prepare a learner the embed can launch as, against the real stack.

Run it through the Django shell from the repo root:

    python manage.py shell < demo/embed/tier1_setup.py

It does two things and prints the launch URLs:

1. Grants AI_PROCESSING and BEHAVIORAL_TRACKING consent to the demo user.
   This is the step that is easy to forget and ugly to hit live. The AI consent
   gate is on by default (settings/base.py: PRIVACY_ENABLE_AI_CONSENT_GATE),
   and only `eipl` pre-gates it in its handler. `prompt` and `probeable_spec`
   have no pre-gate, so without consent they fail part-way through the Celery
   pipeline (tasks/pipeline.py) and leave orphan Submission rows behind.
   Consent is recorded as INSTITUTIONAL, which is what an LTI launch under a
   site licence would use.

2. Mints a mock-Firebase token for that user, which the embed sends as a bearer
   token (embed-main.ts reads ?token= off the launch URL). This is the
   provisional auth that B2 (#139) replaces with a real embed JWT.

MOCK_JWT_SECRET must be set and identical for this process and the Django
server, otherwise the token will not verify: MockFirebaseAuth.get_mock_secret()
generates a random per-process secret when the variable is unset.
"""

import os

from django.contrib.auth.models import User

from purplex.problems_app.models import Problem
from purplex.users_app.mock_firebase import create_test_token
from purplex.users_app.models import ConsentMethod, ConsentType
from purplex.users_app.services.consent_service import ConsentService

DEMO_EMAIL = "student@test.local"
EMBEDDABLE_TYPES = ["eipl", "prompt", "probeable_code", "probeable_spec"]

if not os.environ.get("MOCK_JWT_SECRET"):
    raise SystemExit(
        "MOCK_JWT_SECRET is not set. Set the same value here and for the Django "
        "server, or the minted token will not verify."
    )

user = User.objects.get(email=DEMO_EMAIL)

for consent_type in (ConsentType.AI_PROCESSING, ConsentType.BEHAVIORAL_TRACKING):
    if ConsentService.has_active_consent(user, consent_type):
        print(f"  consent already active: {consent_type}")
        continue
    ConsentService.grant_consent(
        user=user,
        consent_type=consent_type,
        ip_address="127.0.0.1",
        consent_method=ConsentMethod.INSTITUTIONAL,
    )
    print(f"  granted: {consent_type}")

token = create_test_token(DEMO_EMAIL)

print(f"\nDemo learner: {user.username} <{user.email}> (id={user.id})")
print(f"\nToken:\n{token}")

# Problem is polymorphic: problem_type is a property on each subclass, not a
# DB column, so pick the first of each type in Python rather than in a filter().
first_of_type: dict[str, Problem] = {}
for problem in Problem.objects.filter(is_active=True).order_by("id"):
    first_of_type.setdefault(problem.problem_type, problem)

print("\nLaunch URLs (paste into the mock host's 'Iframe URL' field):\n")
for problem_type in EMBEDDABLE_TYPES:
    problem = first_of_type.get(problem_type)
    if not problem:
        print(f"  {problem_type:16} (no seeded problem found)")
        continue

    # problem_set is required: Submission.problem_set is a non-null FK, so a
    # launch without one fails at the database rather than in validation.
    problem_set = problem.problem_sets.first()
    if not problem_set:
        print(f"  {problem_type:16} {problem.slug} — SKIPPED, in no problem set")
        continue

    print(f"  {problem_type:16} {problem.slug}  (set: {problem_set.slug})")
    print(
        f"    http://localhost:5173/embed.html"
        f"?problem={problem.slug}"
        f"&problem_set={problem_set.slug}"
        f"&token={token}\n"
    )
