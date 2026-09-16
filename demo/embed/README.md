# SPLICE Embed — Live Demo

A click-through demo of the LMS embed work. Purplex problems run inside an
iframe on a host LMS page, speaking the SPLICE postMessage protocol: the host
hands back saved work on launch, the embed reports a score and state when the
learner submits, and the host grows the frame as content changes.

There are two tiers. **Tier 1 runs against the real Django stack** — real seeded
problems, real submissions in Postgres, real Docker code execution, real scores.
That is the demo to lead with. **Tier 2** swaps in a stub backend so the same
walkthrough runs with nothing but Node and the Vite dev server.

In both tiers everything inside the iframe is the production embed, unmodified:
the SPLICE bridge, the submit → SSE → completion orchestration, the four
per-type adapters, and the same input and feedback components the main SPA uses.

---

# Tier 1 — against the real stack

## What is real, and what is not

Real: problem fetch, authentication, the submit pipeline, Celery, Docker
execution in the `purplex/python-sandbox` container, `Submission` rows with real
scores and completion status, segmentation analysis, progress records, and the
SSE stream that carries the result back.

Mocked: the LLM (`USE_MOCK_OPENAI=true`, because the repo has no API key) and
Firebase (`USE_MOCK_FIREBASE=true`, the standard dev setting). With a real
`OPENAI_API_KEY` in the environment the LLM round-trip is real too.

Two things about auth are worth saying out loud, because they are what the
backend track exists to fix:

- The launch token is a **mock-Firebase JWT**, passed as `?token=` and attached
  as a bearer token by `embed-main.ts`. B2 (#139) replaces it with a real embed
  JWT minted from an LTI launch. The token expires after one hour — re-run the
  setup script to mint a fresh one.
- The launch carries `?problem_set=`. `Submission.problem_set` is a **non-null
  FK**, so the submit endpoint cannot record a bare single-problem attempt; it
  fails at the database. Until B1–B5 resolves the problem set from the LTI
  context, the host has to name it. See "Known gaps" below.

## Running Tier 1

```bash
# 1. datastores
docker run -d --name purplex_demo_pg \
  -e POSTGRES_DB=purplex_dev -e POSTGRES_USER=purplex -e POSTGRES_PASSWORD=purplex \
  -p 5432:5432 postgres:15-alpine
docker run -d --name purplex_demo_redis -p 6379:6379 redis:7-alpine

# 2. environment (every process below needs these)
export PURPLEX_ENV=development
export DJANGO_SECRET_KEY='demo-only-secret-key-change-me'
export DATABASE_URL='postgresql://purplex:purplex@localhost:5432/purplex_dev'
export REDIS_URL='redis://localhost:6379/0'
export USE_MOCK_FIREBASE=true
export USE_MOCK_OPENAI=true
export PYTHONIOENCODING=utf-8          # the settings banner prints a "checkmark"
# Must be fixed and shared, or a token minted in one process will not verify in
# another: MockFirebaseAuth.get_mock_secret() invents a random per-process
# secret when this is unset.
export MOCK_JWT_SECRET='demo-fixed-mock-jwt-secret'

# 3. schema, users, and real problems
python manage.py migrate
python manage.py create_test_users
python manage.py seed_demo_set_data           # EiPL + Prompt
python manage.py seed_probeable_demo_courses  # Probeable

# 4. grant consent and mint a launch token — prints ready-made launch URLs
python manage.py shell -c "exec(open('demo/embed/tier1_setup.py').read())"

# 5. services (separate terminals)
python manage.py runserver 0.0.0.0:8000 --noreload
python -m celery -A purplex.celery_simple worker -l info --pool=solo \
  --without-mingle --without-gossip --without-heartbeat
cd purplex/client && npx vite --mode development
```

On Windows the Celery worker needs `--pool=solo` and the `--without-*` flags —
with the defaults it hangs during startup and silently never consumes the queue.
The first submission is slow (~20s) because Docker builds the sandbox image;
later ones are quick. Build it ahead of the demo by submitting once.

Then open **http://localhost:5173/embed-mockhost.html**:

1. Paste the token from step 4 into **Launch token**.
2. Pick a problem from the **Tier 1 — real backend** group.
3. Press **Load iframe**.

The picker composes the launch URL from the selected problem, its problem set,
and whatever is in the token box, so a fresh token only has to be pasted once.

The walkthrough below applies to both tiers — only the slugs differ.

## Running both tiers at once

The embed always calls the one API origin it was built with, so by default only
one backend can be live and picking from the other group gives a 404. To avoid
switching mid-demo, put the stub in front of Django and let it forward anything
it does not own:

```bash
# Django moves aside
python manage.py runserver 0.0.0.0:8001 --noreload

# the stub takes the port the embed calls, and proxies the rest
node demo/embed/stub-api.js --upstream http://localhost:8001
```

The stub answers for its own `demo-*` slugs and streams everything else through
untouched — real problems, submissions, probes and SSE all still come from
Django. Both groups in the picker then work without restarting anything.

---

# Tier 2 — against a stub backend

Use this when Docker, Postgres or a Python environment are not available, or
when you want a deterministic run. `stub-api.js` stands in for exactly the
endpoints the embed calls — problem fetch, submit, the SSE task stream, the
probe oracle — on the port the client already expects.

Faked here: problem storage, the LLM round-trip, Docker execution, and scoring.
Scores are keyword-derived so they respond to what you type instead of being a
fixed number. Say this out loud when presenting — the protocol is what is being
demonstrated, not the grader.

## Running Tier 2

Two terminals, from the repo root:

```bash
# 1. the stub backend (no Django, Celery, Redis, Docker or LLM key needed)
node demo/embed/stub-api.js

# 2. the Vite dev server
cd purplex/client && npx vite --mode development
```

Then open **http://localhost:5173/embed-mockhost.html**.

The stub keeps probe history in memory, and the app disables the probe button
for inputs already tried — correct behaviour, but it means a rehearsal leaves
the probeable demos pre-probed. Restart `stub-api.js` for a clean slate.

The left pane is the mock LMS host. It frames the embed, logs every postMessage
in both directions, and answers `SPLICE.getState` with whatever JSON sits in the
prefill box — which is how a real LMS hands back saved work.

## The walkthrough

**1. Launch — the handshake.**
The picker is already on *EiPL — explain: sum a list*. Press **Load iframe**.

Watch the log: the embed sends `SPLICE.getState` the moment it boots (that
doubles as its "I'm ready" signal), the host replies `SPLICE.getState.response`
with `state: null` — a first launch, no saved work — plus the learner identity
the host knows. Then `lti.frameResize` fires as the problem renders and the
iframe grows to fit. No scrollbar inside the frame: the host owns the height.

**2. Answer and submit — the streaming path.**
Type an explanation, e.g.

> Keep a running total starting at zero. For each number in the list, add it to
> the total. Return the total at the end.

Press **Submit Solution**. The embed posts the submission, gets a task id back,
opens an SSE stream, and shows progress while the "LLM and test run" proceed —
the same submit → stream → complete flow the main SPA uses, re-implemented
without router, Vuex or toast dependencies.

**3. Completion — what the host receives.**
Two messages arrive:

- `SPLICE.sendEvent` — a telemetry event describing the attempt (`eipl.attempt`,
  with variation and test tallies). This is the hook for study instrumentation.
- `SPLICE.reportScoreAndState` — `score` normalized to SPLICE's 0..1 range, and
  a `state` payload: the verbatim answer, the score, completion status,
  submission id, attempt count, and per-type details.

Feedback renders in the frame — generated variations, per-test results, and for
EiPL the segmentation (comprehension) analysis.

**4. Relaunch — the round-trip that matters to an LMS.**
Press **Adopt last reported state**, then **Load iframe** again.

The host now answers `getState` with the saved state instead of `null`, and the
learner's answer is back in the editor. That is the full persistence loop a real
LMS performs between sessions, with no Purplex-side account involved.

**5. The other activity types.**
Switch the picker and reload:

- *Prompt — count the words*: same flow, no segmentation.
- *Probeable code — safe divide*: probe the hidden oracle first (try `a=7, b=0`),
  then implement it. One code body instead of LLM variations, so the state
  payload carries a flat test tally.
- *Probeable spec — clamp*: probe, then specify in words; an LLM implements it.

Each type has its own adapter deciding what goes in the state payload and how
feedback is shaped — the bridge and orchestration stay type-agnostic.

**6. The refusal path.**
Pick *MCQ — unsupported type*. The embed refuses to render it and tells the host
why, rather than showing an input that could never report a score. Only the four
types above have adapters.

## Talking points

- **Origin validation.** The embed derives the expected host origin from
  `document.referrer` and drops SPLICE messages from anywhere else. A forged
  `getState` reply from another origin is ignored (covered by E2E).
- **State is validated, not trusted.** A host may hand back anything. State with
  the wrong version, or saved against a different problem, is refused rather than
  loaded into the editor.
- **Size cap.** State is capped at 32KB and must be structured-cloneable;
  oversized or uncloneable payloads are refused rather than silently dropped.
- **No Firebase in the bundle.** The embed entry keeps Firebase, vue-router and
  Vuex out of its import graph — it is a separate Vite entry, not the SPA.

## Test evidence

```bash
# 46 frontend unit tests — bridge, orchestration, adapters
cd purplex/client && npx vitest run \
  src/composables/__tests__/useSpliceBridge.test.ts \
  src/composables/__tests__/useEmbedSubmission.test.ts \
  src/embed/__tests__/adapters.test.ts

# 9 protocol E2E tests against the real embed in a real cross-document iframe
# (needs only the Vite dev server; the API is stubbed at the network boundary)
npx playwright test --project=embed

# 7 backend tests — handler configs on the single-problem endpoint
pytest tests/unit/test_problem_detail_handler_configs.py
```

## Files

| Path | What it is |
| --- | --- |
| `demo/embed/tier1_setup.py` | Tier 1: grants consent, mints a token, prints launch URLs |
| `demo/embed/stub-api.js` | Tier 2 stub backend: problems, submit, SSE stream, probe oracle |
| `demo/embed/problems.js` | The five Tier 2 demo problems and their test cases |
| `purplex/client/embed-mockhost.html` | Mock LMS host page with the protocol log |
| `purplex/client/src/composables/useSpliceBridge.ts` | All postMessage I/O with the host |
| `purplex/client/src/composables/useEmbedSubmission.ts` | Submit → SSE → completion |
| `purplex/client/src/embed/adapters.ts` | Per-type state, feedback and telemetry |
| `purplex/client/src/EmbedApp.vue` | Chromeless single-problem shell |
| `e2e/embed/splice-protocol.spec.ts` | Protocol E2E |

## Known gaps

Things Tier 1 surfaced by running against the real stack. These are the honest
answers to "what is left?".

**1. `Submission.problem_set` is a non-null FK, but the submit view treats it as
optional.** `submissions/models.py` declares `problem_set` without
`null=True`, while `problems_app/views/submission_views.py` builds the
submission with `problem_set.id if problem_set else None`. Any submission with
no problem set — exactly what a bare single-problem embed launch produces —
fails with a not-null violation at the database, for every activity type.

The embed currently works around this by taking a `problem_set` launch param and
forwarding it as `problem_set_slug`. That is a stopgap: it assumes the host
knows the problem set, and it is a parameter B1–B5 should be deriving from the
LTI context instead. The alternative is to make the column nullable, which is a
data-model change and belongs in review (`.github/instructions/data-models.instructions.md`).
Either way this needs a real decision before an LMS pilot.

**2. AI consent is not handled for external learners.** The gate is on by
default (`PRIVACY_ENABLE_AI_CONSENT_GATE`), and only `eipl` pre-gates it in its
handler. `prompt` and `probeable_spec` have no pre-gate, so an un-consented
learner gets a failure part-way through the Celery pipeline and an orphan
`Submission` row. `tier1_setup.py` grants consent up front so the demo does not
hit this, but an LTI-provisioned learner arrives with no consent records at all.
Consent propagation is listed under the backend track; this is what it has to
solve.

**3. `/api/problems/<slug>/` still serializes `reference_solution` to students.**
*(Half of this gap is now fixed — see below.)*

`getEmbedProblem` calls `/api/problems/<slug>/` (`ProblemDetailView`). That
endpoint used to return only model fields, so the embed had no
`display_config` (no stimulus could render) and no `feedback_config` (
segmentation never displayed even when the pipeline computed it).

**Fixed:** `StudentService.get_problem_handler_configs()` now supplies the same
handler configs the problem-set payload carries, and the view merges them in.
Prompt problems render their function-call table again and EiPL shows
segmentation.

**Still open:** the payload includes `reference_solution` for *every* activity
type, including the probeable ones where that string *is* the hidden function.
Nothing server-side withholds it. The embed defends itself by deciding the
stimulus per type in the adapters (`EmbedStimulus`) rather than trusting the
payload, but that is a client-side guard on data the client should never have
received. B3 should withhold it at the serializer for types that must not see
it — anyone can still read it out of the network tab.

**4. No embed backend module yet.** There is no `purplex/embed/`, no
`/api/embed/launch/`, and no embed-scoped authorization. The embed authenticates
with a mock-Firebase token in dev, which works but grants ordinary user access:
there is no problem/problem-set scoping, so the launch token is not restricted
to the problem it was issued for.

**5. Framing is blocked in production.** Dev sets `X_FRAME_OPTIONS =
"SAMEORIGIN"` and the iframe document is served by Vite, so framing is a
non-issue locally. Production sets `X_FRAME_OPTIONS = "DENY"` and will need CSP
`frame-ancestors` plus `SameSite=None; Secure` cookies before any real LMS can
frame it.

**6. Probe budgets are keyed on `user.id`** in Redis with a 7-day TTL. The
LTI → Django user mapping must be deterministic or a learner's probe budget
resets on every launch.
