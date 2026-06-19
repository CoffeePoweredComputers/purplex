# Contributing to Purplex

Welcome! 👋 This guide is for contributors who are **new to Git, forks, and pull
requests**. It walks through everything step by step — nothing you do here can
break the real project.

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

You **do not** have write access to the main Purplex repository, and that's by
design — it keeps `master` and production safe. Instead you'll work on **your own
copy** (a "fork") and propose changes through **pull requests**. This is the
standard, professional open-source workflow. The worst case is your pull request
gets feedback before it's merged.

> The project's default branch is **`master`** (not `main`). Every command in
> this guide uses `master` — that's intentional.

---

## Found a bug or have an idea? (no code required)

Not every contribution is code. To **report a bug**, first check the
[existing issues](../../issues); if it's new, [open an issue](../../issues/new)
with a clear title, steps to reproduce, expected vs. actual behavior, your
environment (OS, Python/Node versions, browser), and any error logs. To
**suggest a feature**, [open an issue](../../issues/new) with the `enhancement`
label describing the problem it solves, your proposed solution, and alternatives
you considered.

For code changes, read on.

---

## 1. The mental model (read this first)

After setup you'll have the same project in **three places**:

```
  CoffeePoweredComputers/purplex   ← the real repo. You CAN'T push here.
            (on GitHub)               You call this remote "upstream".
                  │
                  │  (you click "Fork" once)
                  ▼
   YOUR-USERNAME/purplex            ← your personal copy on GitHub.
            (on GitHub)               You CAN push here. Called "origin".
                  │
                  │  (you "git clone" it once)
                  ▼
       purplex/  (on your laptop)   ← where you actually edit code.
```

Almost every confusion a beginner hits ("how do I update my fork?", "why is my
branch behind?") comes down to forgetting there are **two remotes**:

| Remote     | Points to                          | Can you push? | You use it to…                |
| ---------- | ---------------------------------- | ------------- | ----------------------------- |
| `origin`   | **your** fork (`YOU/purplex`)      | ✅ Yes        | push your branches, open PRs  |
| `upstream` | the real repo (`Coffee…/purplex`)  | ❌ No         | **pull in** the latest code   |

Keep that table in your head and the rest of this guide is just typing.

---

## 2. One-time setup

You only do this **once per machine**.

### Easy path — using the GitHub CLI (recommended)

If you have the [GitHub CLI](https://cli.github.com/) installed and logged in
(`gh auth login`), this single command forks the repo, clones **your** fork, and
wires up `upstream` for you automatically:

```bash
gh repo fork CoffeePoweredComputers/purplex --clone
cd purplex
```

That's it — skip to "Verify your setup".

### Manual path — point-and-click + git

1. **Fork it.** Go to <https://github.com/CoffeePoweredComputers/purplex> and
   click the **Fork** button (top-right). GitHub creates `YOUR-USERNAME/purplex`.

2. **Clone your fork** to your laptop (use *your* username):

   ```bash
   git clone https://github.com/YOUR-USERNAME/purplex.git
   cd purplex
   ```

3. **Add the `upstream` remote** so you can pull in future changes from the real
   repo:

   ```bash
   git remote add upstream https://github.com/CoffeePoweredComputers/purplex.git
   ```

### Verify your setup

```bash
git remote -v
```

You should see **four lines** — `origin` pointing at *your* fork, and `upstream`
pointing at `CoffeePoweredComputers/purplex`:

```
origin    https://github.com/YOUR-USERNAME/purplex.git (fetch)
origin    https://github.com/YOUR-USERNAME/purplex.git (push)
upstream  https://github.com/CoffeePoweredComputers/purplex.git (fetch)
upstream  https://github.com/CoffeePoweredComputers/purplex.git (push)
```

If `upstream` is missing, re-run the `git remote add upstream …` line above.

### Get the app running

Follow the [README quick-start](README.md#quick-start). In short, `./start.sh`
boots every service (PostgreSQL, Redis, Django, Celery, Vue). Confirm you can
open <http://localhost:5173> before you start changing code.

---

## 3. The everyday workflow (the loop you'll repeat)

For **every** piece of work, follow these five steps in order. Step 1 is the one
beginners skip — don't skip it.

### Step 1 — Sync, so you start from the latest code

Always begin a new task from an up-to-date `master`. (Full details in
[§4](#4-keeping-your-fork-up-to-date).)

```bash
git checkout master
git fetch upstream
git merge upstream/master
git push origin master      # keeps your fork's master current too
```

### Step 2 — Create a branch for your work

**Never** work directly on `master`. Make a branch named for what you're doing:

```bash
git checkout -b feature/add-hint-tooltip
#                 ^ pick a short, descriptive name
```

Conventional prefixes: `feature/…`, `fix/…`, `docs/…`.

### Step 3 — Make changes and commit them

Edit code, then save your progress in small, logical commits:

```bash
git add path/to/the/file.py        # stage specific files (avoid "git add ." )
git commit -m "Add tooltip to Variable Fade hint"
```

Before you push, run the same checks CI will run (see [§6](#6-make-ci-pass)):

```bash
make format     # auto-format your code
make lint       # check style
make test-unit  # run the fast tests
```

### Step 4 — Push your branch to your fork

```bash
git push origin feature/add-hint-tooltip
```

### Step 5 — Open a pull request

Go to your fork on GitHub. You'll see a banner: **"Compare & pull request"** —
click it. Make sure the PR targets `CoffeePoweredComputers/purplex` `master` ←
`YOUR-USERNAME/purplex` `feature/...`. Fill in the
[PR template](.github/pull_request_template.md), reference the issue you're
solving (`Closes #123`), and submit.

A maintainer reviews and merges it — **you don't merge your own PRs.** If they
ask for changes, just commit more to the **same branch** and `git push origin
feature/add-hint-tooltip` again; the PR updates automatically.

### After it's merged — clean up

```bash
git checkout master
git fetch upstream && git merge upstream/master   # pull in your now-merged work
git branch -d feature/add-hint-tooltip            # delete the local branch
git push origin --delete feature/add-hint-tooltip # delete it from your fork
```

---

## 4. Keeping your fork up to date

Your fork does **not** update itself. While you work, other people's PRs get
merged into the real repo, and your fork silently falls behind. GitHub will show
your fork as *"This branch is N commits behind CoffeePoweredComputers:master."*
Syncing regularly is the single best habit for avoiding painful merge conflicts.

There are two ways to sync. Use whichever you like — they do the same thing.

### Way A — the GitHub website (easiest)

1. Open **your** fork: `https://github.com/YOUR-USERNAME/purplex`
2. Click the **Sync fork** button near the top, then **Update branch**.

That updates your fork's `master` **on GitHub**. To bring those updates **down to
your laptop**, run:

```bash
git checkout master
git pull origin master
```

### Way B — the command line (do it all from your terminal)

```bash
git checkout master          # 1. be on your local master
git fetch upstream           # 2. download the latest from the real repo
git merge upstream/master    # 3. fast-forward your local master to match
git push origin master       # 4. push those updates up to your fork on GitHub
```

> **Why `merge upstream/master` and not `git pull`?** `git pull` defaults to
> pulling from `origin` (your fork) — but the *new* code lives in `upstream`. So
> you `fetch upstream` and `merge upstream/master` to grab the real updates. As
> long as you never commit directly to `master`, this merge is always a clean
> "fast-forward" (no conflicts).

### Updating a feature branch you're in the middle of

Sometimes a task takes a few days and `master` moves underneath you. To pull the
latest changes **into your in-progress branch**:

```bash
git checkout feature/add-hint-tooltip
git fetch upstream
git merge upstream/master          # bring master's new commits into your branch
# ...resolve any conflicts git reports, then:
git push origin feature/add-hint-tooltip
```

(Advanced users prefer `git rebase upstream/master` here for a cleaner history.
If "rebase" doesn't mean anything to you yet, **use `merge`** — it's safer and the
result is fine.)

---

## 5. When something goes wrong (don't panic)

Git problems are almost always recoverable. Here are the four a beginner hits most.

### "I accidentally made commits on `master`"

Move them onto a branch, then reset `master` back to match upstream:

```bash
git branch feature/my-work       # save your commits onto a new branch
git fetch upstream
git reset --hard upstream/master # rewind master to the real repo's state
git checkout feature/my-work     # continue working on the branch
```

### "Git says I have merge conflicts"

A conflict means two changes touched the same lines. Git marks them in the file
like this:

```
<<<<<<< HEAD
your version
=======
the other version
>>>>>>> upstream/master
```

Open each marked file, decide which lines to keep (or combine them), **delete the
`<<<<<<<`, `=======`, `>>>>>>>` marker lines**, then:

```bash
git add the-file-you-fixed.py
git commit          # finishes the merge
```

When unsure which side to keep, ask your mentor before committing — don't guess on
code you don't understand.

### "GitHub says my branch is N commits behind"

That's normal and just means it's time to sync — see [§4](#4-keeping-your-fork-up-to-date).

### "I want to throw away my local changes and start over"

```bash
git checkout master
git fetch upstream
git reset --hard upstream/master   # ⚠️ discards ALL uncommitted local changes
```

---

## 6. Make CI pass

When you open a PR, automated checks ("CI") run on it. **Your PR can't be merged
until they're green.** Save yourself a round-trip by running them locally first:

```bash
make format       # black + isort + prettier
make lint         # flake8 + eslint
make test         # full test suite
```

Purplex also enforces some **architecture rules** that trip up newcomers. The big
ones:

- **Three-layer separation:** Views call Services, Services call Repositories,
  and **only Repositories touch the database** (`Model.objects…`, `.save()`,
  `.delete()`). Don't query the ORM from a view or service.
- **Tests use factories**, never `Model.objects.create()`. Use the factories in
  `tests/factories/__init__.py`.
- **No bare `except Exception` in views.**

These are checked by `pytest -m architecture` and a reviewer bot. For the full
list and examples, read:

- [`docs/development/STANDARDS.md`](docs/development/STANDARDS.md) — coding standards & naming
- [`docs/development/PATTERNS.md`](docs/development/PATTERNS.md) — copy-paste code templates
- [`docs/development/TESTING_QUICK_REFERENCE.md`](docs/development/TESTING_QUICK_REFERENCE.md) — how to write tests

---

## 7. Golden rules (the "never do this" list)

- ❌ **Never commit secrets.** No passwords, API keys, `.env` files, or SSH/deploy
  keys — ever. This is a **public** repository; anything you commit is visible to
  the world and stays in history even after deletion. If you think you committed a
  secret, **stop and tell a maintainer immediately**.
- ❌ **Never work directly on `master`.** Always branch (Step 2).
- ❌ **Don't run `git add .` or `git add -A`.** Stage specific files so you don't
  accidentally commit junk (build artifacts, local config, that deploy key).
- ❌ **Don't force-push (`git push --force`)** to a branch others might be using.
- ✅ **Do sync your fork often** ([§4](#4-keeping-your-fork-up-to-date)).
- ✅ **Do ask questions early.** A two-minute question beats a two-hour wrong turn.

---

## 8. Cheat sheet

```bash
# --- One-time setup ---
gh repo fork CoffeePoweredComputers/purplex --clone   # fork + clone + upstream
# (or manual: git clone YOUR fork, then
#  git remote add upstream https://github.com/CoffeePoweredComputers/purplex.git)

# --- Start every new task ---
git checkout master
git fetch upstream && git merge upstream/master       # sync
git push origin master
git checkout -b feature/short-name                    # branch

# --- While working ---
git add path/to/file
git commit -m "Clear message"
make format && make lint && make test-unit
git push origin feature/short-name

# --- Open the PR on GitHub, then respond to review by pushing more commits ---

# --- Keep your fork current any time ---
git checkout master
git fetch upstream && git merge upstream/master && git push origin master
```

Questions? Open a [GitHub issue](../../issues) or ask your mentor. Happy
contributing! 🎉
