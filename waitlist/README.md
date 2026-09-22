# Profa Eficientă — Waitlist

Pre-launch waitlist landing page for Profa Eficientă. Dark, "mysterious reveal"
design matching the main app's palette/typography, Romanian copy, built
mobile-first for traffic arriving from social links. Three signup paths:

- **Gratuit** — free waitlist, email only.
- **VIP** — email + phone, gated behind a real one-time **50 RON payment via
  Stripe Checkout** (with an auto-generated Stripe invoice).
- **Cancelaria de pe WhatsApp** — phone-only interest form for the teacher
  WhatsApp group, in the hero.

Every submission (free signup, confirmed VIP payment, WhatsApp request)
sends a formatted HTML notification email to the site owner.

## Integration

This used to be its own standalone Flask app/deploy (own repo history at
[github.com/Eusebius33/cadoul-matematic](https://github.com/Eusebius33/cadoul-matematic)).
It's now folded into the main Profa Eficientă project as a Flask
**blueprint** (`waitlist_bp` in `app.py`), registered from the root
`app.py` with `url_prefix="/cadoul-matematic"` — so in normal operation
this page is reached at `{main site}/cadoul-matematic` and its own
`app.run()` is never used. Everything below (Supabase/Stripe/Resend setup,
env vars, content editing) still works exactly the same either way; only
the deploy target and mount path changed. See the "Run locally" section
below for iterating on just this sub-app in isolation.

## Stack

- **Backend:** Flask (serves the page + a small JSON API).
- **Frontend:** React, loaded via CDN (`react`/`react-dom` UMD builds) and
  written with `React.createElement` instead of JSX — so there's no Babel
  transform in the browser and no Node build step. React only mounts the two
  interactive form islands (`#waitlist-root-free`, `#waitlist-root-vip`);
  everything else is plain server-rendered HTML for fast first paint and so
  it's crawlable without executing JS.
- **Styling:** hand-authored CSS in `static/css/styles.css`, using the exact
  color tokens (`slate-950/900/800`, `cyan-500` `#06b6d4`, Outfit + Inter)
  pulled from the real app's templates, rather than the `cdn.tailwindcss.com`
  runtime compiler. That CDN script is explicitly flagged by Tailwind as not
  meant for production (it recompiles styles in-browser on every load), which
  fights the "fast-loading, mobile-first, social-traffic" requirement here. If
  you'd rather have literal Tailwind utility classes, swap in a real Tailwind
  build (`npx tailwindcss -i ... -o ...`) — the design tokens in `:root` map
  1:1 to the Tailwind scale so the visual result is identical either way.
- **Storage:** Supabase (hosted Postgres). See [Storage](#storage--supabase)
  below for why, and the trade-offs of the alternatives.
- **Payment:** Stripe Checkout (hosted, redirect-based — card data never
  touches this server) for the VIP fee, confirmed via a Stripe webhook.
- **Email:** Resend (HTTP API), for both the owner-facing "you got a new
  signup" notifications and the customer-facing invoice/receipt email. Not
  SMTP — see [Email notifications](#email-notifications--resend) for why.
- **Deploy target:** deployed as part of the main Profa Eficientă app (see
  [Integration](#integration) above) — whatever platform that app runs on
  (Docker/Vercel/Procfile at the repo root), not its own Render service.

Every third-party integration (Supabase, Stripe, Resend) follows the same
pattern: fully wired and correct, but gracefully inactive — logging what it
would have done instead of crashing — until you add its real credentials.
That means the whole app runs and is testable end-to-end with zero external
accounts, and each integration goes live the moment you add its keys.

## Project structure

```
app.py                                 waitlist_bp: routes, Stripe/Supabase/Resend glue
requirements.txt
.env.example                           copy to .env for local dev
templates/waitlist/index.html          page shell, SEO/OG tags, static content
templates/waitlist/vip_success.html    post-payment thank-you page (Stripe redirects here)
templates/waitlist/legal.html          shared Termeni/Confidențialitate template
static/css/styles.css                  design tokens + all styling/animation
static/js/app.js                       reveal/parallax/tilt + React form islands
static/images/                         og-image.png, favicon.svg
content/testimonials.json              social-proof quotes — edit this, not the HTML
content/legal.json                     Terms/Privacy copy — edit this, not the HTML
supabase/schema.sql                    run once in the Supabase SQL editor
scripts/generate_og_image.py           regenerates static/images/og-image.png
```

Templates live under `templates/waitlist/` (not `templates/` directly) so
`render_template()` can't accidentally resolve to a same-named template
belonging to the main app once this blueprint is registered alongside it —
Flask checks the main app's own `templates/` first, and the root app
already ships its own `templates/index.html`.

## Run locally

Commands below assume you're inside this `waitlist/` folder (`cd waitlist`
from the repo root first). This spins up just the landing page, standalone,
for fast iteration — it does not need the main app's Postgres/session setup
at all:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # leave SUPABASE_* blank for now
python3 app.py                # http://localhost:5000
```

(To hit it through the main app instead, at its real mount point, just run
the main app normally — `python3 app.py` from the repo root — and open
`http://localhost:5000/cadoul-matematic`; no separate venv/install needed
there since `waitlist_bp` shares the main app's dependencies.)

With everything in `.env` left blank, the whole app runs in dry-run mode:
signups are appended to gitignored local `.jsonl` files instead of Supabase,
the VIP form shows a clean "payment not available yet" message instead of
calling Stripe, and notification emails are just logged to the console
(tagged `[DEV MODE - ...]`) instead of sent via Resend. Test the full flow
end-to-end before creating any of the three accounts.

## Storage — Supabase

You asked for a recommendation between a hosted form backend, Supabase, or a
serverless endpoint. Here's the trade-off, and why the build defaults to
Supabase:

| Option | Pros | Cons |
|---|---|---|
| **Supabase (chosen)** | Free tier, doesn't expire. Table Editor in the dashboard gives you a spreadsheet view of signups with zero admin UI to build. Real Postgres if you outgrow it. | Free projects **pause after ~7 days with no API activity** — mitigated here: `/health` pings Supabase too, and the keep-alive cron (below) hits `/health` every 10 minutes, so as long as the cron is running the project never goes idle long enough to pause. |
| Postgres via SQLAlchemy (your app's existing pattern) | Consistent with `models.py` in the main app. | Render's **free** Postgres expires after 90 days and must be recreated — a bad fit for a waitlist that might run longer than that. |
| Hosted form backend (Formspree etc.) | Zero backend code. | Submissions land in email/a spreadsheet, not a queryable table; hard to break down free vs. VIP counts; doesn't really use the Flask backend you asked for. |

**Setup:**

1. Create a free project at [supabase.com](https://supabase.com).
2. Project → SQL Editor → New query → paste and run `supabase/schema.sql`.
3. Project Settings → API → copy the **Project URL** and the **`service_role`
   secret key** (not the `anon`/`public` key).
4. Set them as `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (locally in `.env`,
   on Render as environment variables — see below).

The service role key only ever lives server-side in `app.py`; the browser
never sees it. Row Level Security is enabled on both tables with **no**
policies, so the `anon` key (if it ever leaked) can't read or write them
either — only the service role key, held by the backend, can.

`schema.sql` creates two tables: `waitlist_signups` (free + paid-VIP rows,
with `phone`, `stripe_session_id`, `amount_paid_ron` columns used only for
VIP) and `whatsapp_signups` (phone-only, for the "Cancelaria de pe WhatsApp"
form). If you already ran an earlier version of this file, re-running it is
safe — the new columns/table are added with `if not exists`, nothing existing
is touched.

## Payment — Stripe (VIP, 50 RON)

VIP access costs a one-time **50 RON**, collected via **Stripe Checkout**:
the browser is redirected to a Stripe-hosted payment page (card entry, 3D
Secure, and PCI compliance are entirely Stripe's problem, never touching this
server, checkout page in Romanian via `locale="ro"`), then back to
`/vip-success` for a thank-you page. Stripe also auto-generates an
**invoice** (`invoice_creation` is enabled on the Checkout Session, in
Romanian) — a genuine Stripe-issued invoice, not a fabricated one. If your
business needs full Romanian e-Factura/ANAF compliance beyond what Stripe
issues, that's a separate accounting integration outside what this build (or
Stripe alone) provides.

The actual signup is only recorded in Supabase — and both notification
emails only sent — once Stripe **confirms** payment via webhook. The
`/vip-success` redirect is just the user-facing thank-you page; it doesn't
depend on the visitor's browser successfully making it back to your site,
so a closed tab mid-redirect can't lose a paid signup.

**Invoice delivery — two independent paths, so it doesn't depend on a Stripe
Dashboard setting this app can't verify from here:**
- `send_email()` in `app.py` emails the payer directly (via the same Resend
  setup as the owner notifications) with a "Descarcă factura" button.
- `/vip-invoice/<session_id>` lets them download it straight from your site
  (also linked from `/vip-success`) — it redirects to Stripe's PDF, looked
  up live each time rather than stored, so there's no schema/DB entry for it
  and nothing to go stale.

**Setup:**

1. Create a [Stripe](https://stripe.com) account (Romania is supported).
2. Dashboard → Developers → API keys → copy the **test** secret key
   (`sk_test_...`) while you're testing. Set it as `STRIPE_SECRET_KEY`.
3. Dashboard → Developers → Webhooks → **Add endpoint** →
   `{SITE_URL}/api/stripe-webhook` → select event `checkout.session.completed`
   → copy the **Signing secret** → set as `STRIPE_WEBHOOK_SECRET`.
   (For local testing, use the [Stripe CLI](https://stripe.com/docs/stripe-cli):
   `stripe listen --forward-to localhost:5000/api/stripe-webhook` prints a
   local webhook secret you can use instead.)
4. Test the flow with Stripe's test card `4242 4242 4242 4242`, any future
   expiry date, any CVC, any postal code.
5. When ready to take real money: switch both keys to their `sk_live_...` /
   live-mode webhook equivalents. Nothing else in the code changes.

## Email notifications — Resend

Every email this app sends — the "new signup" notifications (free/WhatsApp/
VIP) and the customer-facing invoice/receipt email — goes through
**Resend's HTTP API**, not SMTP.

**Why not SMTP** (this app briefly used Gmail SMTP): Render's free web
services block outbound traffic to SMTP ports 25/465/587 entirely, as of
[a September 2025 platform change](https://render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports).
Confirmed here the hard way — a real deployed webhook call silently failed
to send (correct code, correct credentials, worked fine from a non-Render
environment) purely because the connection itself was blocked at the
network level. There's no code fix for that; only a paid Render instance or
a transport that isn't SMTP. Resend sends over plain HTTPS, which isn't
blocked on any tier.

**Setup:**

1. Free account at [resend.com](https://resend.com) → dashboard gives you a
   working API key immediately, no domain verification needed to start
   (uses their shared `onboarding@resend.dev` sender — fine for low volume).
2. Set `RESEND_API_KEY` to that key, and `NOTIFY_EMAIL` to the inbox that
   should receive signup notifications (yours).
3. Once you're sending real volume, verify your own domain in Resend and
   point `RESEND_FROM_EMAIL` at an address on it — the shared sender is
   rate-limited and less deliverable long-term. (This project uses a
   verified domain already: `RESEND_FROM_EMAIL=Cadoul Matematic
   <facturi@webcrew.tech>` — the "Display Name <email>" format is valid.)
4. `reply_to` is set to `NOTIFY_EMAIL` on every email `send_email()` sends
   (`app.py`), regardless of the `from` address — so if `facturi@webcrew.tech`
   isn't a real inbox anyone reads, a customer hitting Reply still lands
   somewhere you'll see it instead of bouncing silently.

**Free plan limits, worth knowing before they surprise you:** 3,000
emails/month, capped at **100/day**, one verified domain, 30-day log
retention. The daily cap is the one that bites first — a burst of VIP
signups past 100 in a day means later ones fail, not queue. That failure is
safe (see below), but silent: nothing shows it to you except Resend's own
dashboard logs, so if a day's numbers look off, check there before assuming
the code is wrong. Consider paid Resend tiers once volume is real.

**Failure handling:** `send_email()` wraps the actual Resend API call in its
own try/except and only logs on failure — verified against the installed
SDK's source (`resend/request.py`): it raises on any non-200 response
(auth errors, validation errors, the 100/day cap, all of it), and that
raise is caught right there and never propagates. Concretely: a failed
send can't turn into a non-2xx response from `/api/stripe-webhook`, so it
can't trigger a Stripe retry or put a paid signup's DB record at risk —
the payment and the notification email are already decoupled failure
domains by construction.

## Deployment

This sub-app no longer deploys on its own — it ships as part of the main
Profa Eficientă app (see [Integration](#integration)), on whatever platform
that app runs on (currently Docker / `Procfile` / Vercel at the repo root).
There's no separate build/start command, health check, or cold-start
concern to configure here: `/cadoul-matematic/health` is just a normal
route on the main app now, and it's warm exactly whenever the main app is.

Set `SITE_URL` (in `waitlist/.env`, or the main app's real production env
vars) to the **main app's** public URL — it's used for the canonical link,
Open Graph tags, and Stripe's success/cancel redirect URLs, all of which
now append `/cadoul-matematic` themselves (`url_for('waitlist.*')` in
`app.py`), so `SITE_URL` itself should stay a bare domain with no path.
Also double check the Stripe webhook endpoint (Dashboard → Developers →
Webhooks) points at `{SITE_URL}/cadoul-matematic/api/stripe-webhook`, not
the old bare `/api/stripe-webhook`.

The standalone Render deployment this originally used (own web service,
`render.yaml` Blueprint, UptimeRobot/GitHub Actions keep-alive cron to
dodge free-tier cold starts) has been retired along with those files —
none of it applies once this runs inside an always-mounted blueprint
instead of its own idle-able service. That history (and the reasoning
behind each piece) is preserved in this project's original repo,
[github.com/Eusebius33/cadoul-matematic](https://github.com/Eusebius33/cadoul-matematic),
if it's ever split back out on its own.

## Editing content

- **Testimonials:** edit `content/testimonials.json`. It ships with
  bracketed placeholders (`[Nume Prenume]`, etc.) on purpose — real quotes
  should read as genuine, not be invented. Add real ones there whenever
  you have them.
- **OG preview image:** `static/images/og-image.png`, regenerate via
  `python3 scripts/generate_og_image.py` after editing the script, or replace
  the PNG directly with a real screenshot/design (keep it 1200×630).
- **Copy/headline:** `templates/index.html` — all text is plain Romanian
  copy in the markup, no i18n system on this standalone page.

## Notes on the API

Paths below are the blueprint's own, as seen when running this app
standalone; add `/cadoul-matematic` in front of each when going through the
main app (e.g. `POST /cadoul-matematic/api/waitlist`).

All three POST routes validate server-side regardless of client-side checks,
have a hidden honeypot field (`hp_field` — deliberately not named `company`/
`website`, which browser autofill recognizes and can fill in on a real
visitor, silently dropping their signup) for basic bot resistance, and share
a simple in-memory per-IP rate limit (20 requests/minute) — good enough for
a single free-tier instance; it resets on redeploy and isn't meant to
survive a real attack.

- `POST /api/waitlist` — free tier only (`{"email", "tier": "free", "source"}`).
  A `tier: "vip"` here is rejected on purpose; VIP goes through checkout.
  Duplicate email → friendly "already on the list", not an error.
- `POST /api/vip-checkout` — `{"email", "phone", "source"}` → creates a
  Stripe Checkout Session, returns `{"url": "..."}` for the browser to
  redirect to. Nothing is recorded yet at this point.
- `POST /api/stripe-webhook` — Stripe calls this, not the browser. Verifies
  the signature, and on `checkout.session.completed` records the paid VIP
  signup and sends the notification email. This is the authoritative write.
- `POST /api/whatsapp` — `{"phone", "source"}` for the WhatsApp-group
  interest form. Phone numbers are normalized (accepts `07...`, `+407...`,
  `0040 7...`) before the uniqueness check, so formatting differences don't
  create duplicate rows.
- `GET /vip-success?session_id=...` — where Stripe redirects after payment;
  purely a thank-you page, re-verifies the session with Stripe to decide
  which message to show.
