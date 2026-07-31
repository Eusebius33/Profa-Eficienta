# Known Issues & TODOs — 2026-07-31

Audit of the current codebase (post commit `6d42eb0`) to catalogue everything
confirmed broken, unfinished, or unverified, plus a TODO checklist. Each item
below was verified by reading the actual code paths involved (routes,
templates, and the generator functions they call), not just naming.

---

## 1. Confirmed bugs

### 1.1 Mode 5 "Lecții de omis" (avoid) is a dead field everywhere
`templates/menu.html` and `templates/modes/mode5.html` both collect an
"avoid" list of lessons to exclude, but **nothing in the backend ever reads
it**:
- `create_mode5` (`app.py:516-543`) never calls `request.form.get("avoid")`.
- `generate_bac` (`bac_generator/routes.py:10-54`) only reads
  `request.form.getlist("lessons")` — no `avoid` anywhere.
- `BACExamGenerator.generate_exam()` (`bac_generator/generator.py:70-84`) has
  no exclusion parameter at all — `selected_lessons`, `seed`,
  `duplicate_threshold` only.

The only place "avoid" is honored is the **Editor's** Mode 5 panel
(`secondary/document_editor.py:664-668`), which uses a separate, LLM-based
`ai.bac_generator(lessons, avoid)` — a second, different Mode 5
implementation from the deterministic `BACExamGenerator` used everywhere
else. So depending on where a user generates a BAC variant from, "avoid" is
either respected (Editor) or silently thrown away (`/menu` → Mode 5,
`/mode5/<id>` regenerate).

### 1.2 Mode 5's first-generation form also ignores "lessons"
Same root cause as 1.1: `create_mode5` never reads `request.form.get("lessons")`
either — the very first exam shown after clicking "Generator BAC" from `/menu`
always uses a hardcoded `default_lessons` list, even though the form's
"Lecții principale" textarea is marked `required`. Regenerating afterwards
from `/mode5/<id>` (checkbox form → `/generate-bac/<id>`) does correctly use
the checked lessons — it's only the initial creation step that's broken.

### 1.3 `flask_session/` — 19 session files committed to git history
`.gitignore` has had `flask_session/` since some point, but 19 files under
that directory were tracked *before* the rule was added and remain tracked
today (`git ls-files | grep flask_session`). Gitignore doesn't retroactively
untrack already-tracked files. These are serialized session payloads —
low sensitivity here, but it's bloating the repo and is bad practice to keep
carrying forward.

### 1.4 `templates/layout1.html` is dead code with inverted logic
Nothing extends it anymore (`grep -rl 'extends "layout1.html"' templates/`
returns nothing — every template was switched to `layout.html` in the
`UI-update-maria` merge). It's harmless as long as it stays unreferenced, but
if anyone resurrects it: it sends **logged-in** users to `/` and **guests**
to `/dashboard` (backwards), and uses `session["user_id"]` bracket access
instead of `.get()`, which raises `KeyError` for anonymous visitors.
Recommend deleting the file outright rather than leaving it as a trap.

### 1.5 Duplicate landing routes
`/` (`index()`, `app.py:215-217`) and `/landing` (`landing()`, `app.py:163-165`)
both render `landing.html`. Not broken, just redundant — pick one and redirect
the other.

---

## 2. Deployment / infra open items (not code bugs, but blocking verification)

### 2.1 Prod appears to be running stale code
Earlier in this session: navbar CTA (`Creează` → `/editor`) and the
`Conversație` link fix are committed locally (commit `6d42eb0`), but were
reported as not reflected in the deployed app. Root cause identified today:
`docker-compose.yml` has no bind-mount for the app source, and the
`Dockerfile` bakes code in via `COPY . .` at build time — restarting the
container without rebuilding the image (`docker compose restart` /
`docker compose up -d` without `--build`) will keep serving old code.
**Action**: always redeploy with `docker compose up -d --build` (or
`docker compose build --no-cache && docker compose up -d`).

### 2.2 Prod logo → "/" redirect — still unexplained
Reported once as "logo sends logged-in users to `/` instead of `/dashboard`,
only in prod." Traced as far as static analysis allows (`login_required`'s
`@wraps`, no stray `redirect("/")` anywhere, session persistence via the
`session_data` docker-compose volume) with no code-level cause found. Given
2.1, this may simply have been the same stale-deploy issue — needs
re-verification against a freshly rebuilt container before assuming it's
still an open bug.

---

## 3. New features this session — implemented but not live-QA'd

Both were verified via template rendering (`render_template` against a real
Postgres), `py_compile`, and `node --check` — **not** via an actual browser
session or a real Gemini API call. Recommend a manual pass before calling
these done:

- **First-run guide** (`secondary/accounts.py` register → `Conversation`
  titled "Ghid Website" → `secondary/model_route.py` → `ai.website_guide()`):
  never exercised against the live Gemini API — worth confirming the model
  actually follows the "always end with numbered navigation steps"
  instruction in practice, not just that the code path is reachable.
- **Editor quick-draft popup** (`templates/editor.html` /
  `static/editor.js` / `static/editor.css`): confirmed the overlay renders
  correctly for an empty document and is suppressed for a non-empty one, and
  that `openModePanel()` is reachable from the new code — not yet clicked
  through in a real browser (focus trap, Escape/backdrop close, stagger
  animation, and actual mode generation from the popup).

---

## 4. Hygiene / cleanup

- **Bare `#TODO` comments with no content** at `app.py:166, 297, 306, 388,
  443, 466, 515` — leftover markers from earlier development with nothing
  attached explaining what's pending. Either resolve or replace with a real
  note.
- `app.py:437-445` contains a fully commented-out, superseded `mode3(...)`
  function (replaced by `model_route.mode3_chat`) — dead code, safe to
  delete.

---

## TODO checklist

- [ ] Fix `create_mode5` to read `request.form.get("lessons")` /
      `request.form.get("avoid")` and pass them into the initial exam
      generation (app.py:516-543).
- [ ] Decide: give `BACExamGenerator.generate_exam()` a real
      exclude/"avoid" parameter, or drop the "Lecții de omis" field from
      `menu.html`/`modes/mode5.html` if it's not meant to be supported
      outside the Editor's LLM-based generator.
- [ ] Reconcile the two Mode 5 implementations (`BACExamGenerator` vs
      `ai.bac_generator`) so behavior is consistent between `/menu`, the
      standalone `/mode5/<id>` page, and the Editor panel — or document why
      they're intentionally different.
- [ ] `git rm --cached -r flask_session/` to stop tracking the 19 already-committed
      session files (keep the existing `.gitignore` entry so new ones stay untracked).
- [ ] Delete unused `templates/layout1.html`.
- [ ] Collapse `/` and `/landing` into a single route.
- [ ] Confirm prod is running the latest image (`docker compose up -d
      --build`) and re-check whether the logo/CTA issues persist.
- [ ] Manually QA the first-run "Ghid Website" flow end-to-end against the
      real Gemini API (register → intro question → guided reply → follow
      the given navigation steps).
- [ ] Manually QA the editor quick-draft popup end-to-end (all 5 modes,
      keyboard nav, Escape/backdrop close, reduced-motion).
- [ ] Resolve or remove the bare `#TODO` markers in `app.py`.
- [ ] Delete the dead commented-out `mode3(...)` block in `app.py`.
