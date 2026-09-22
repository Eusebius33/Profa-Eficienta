import html
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

load_dotenv()

# Registered on the main app (see app.py) with url_prefix="/cadoul-matematic",
# so every route below is reachable at /cadoul-matematic/... . Templates live
# under templates/waitlist/ (not templates/ directly) so render_template()
# can never accidentally resolve to a same-named template belonging to the
# main app (the root app already ships its own templates/index.html) — see
# the "waitlist/xxx.html" render_template() calls below.
#
# Run standalone (python waitlist/app.py) for isolated iteration on the
# landing page: the __main__ block below mounts this same blueprint with no
# prefix, so all routes fall back to their bare paths (/, /api/waitlist, ...)
# exactly like before this app was folded into the main project.
waitlist_bp = Blueprint(
    "waitlist", __name__, template_folder="templates", static_folder="static"
)

SITE_NAME = "Profa Eficientă"
SITE_URL = os.environ.get("SITE_URL", "https://profa-eficienta.onrender.com").rstrip("/")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_CONFIGURED = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
STRIPE_CONFIGURED = bool(STRIPE_SECRET_KEY)
VIP_PRICE_RON = 50

# Email via Resend's HTTP API, not SMTP: Render's free tier blocks outbound
# SMTP ports (25/465/587) entirely as of Sept 2025 — confirmed via Render's
# own changelog after a real deployed webhook silently failed to send while
# the identical call worked fine from a non-Render environment. An HTTPS
# API call isn't subject to that block. NOTIFY_EMAIL falls back to the old
# SMTP_TO var name so an existing .env/Render env doesn't need renaming.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL") or os.environ.get("SMTP_TO")
RESEND_CONFIGURED = bool(RESEND_API_KEY and NOTIFY_EMAIL)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^0\d{9}$")
VALID_TIERS = {"free", "vip"}

# Local fallback store used only when Supabase env vars are not set (local dev
# without a Supabase project yet). Never used when SUPABASE_URL/KEY are present.
LOCAL_FALLBACK_FILE = Path(__file__).parent / "waitlist_local.jsonl"
WHATSAPP_LOCAL_FALLBACK_FILE = Path(__file__).parent / "whatsapp_local.jsonl"

_supabase_client = None
_supabase_init_attempted = False


def get_supabase():
    """Lazily creates the Supabase client.

    Returns None either when Supabase isn't configured at all (local dev,
    handled by SUPABASE_CONFIGURED / dry-run mode) or when it's configured
    but the client failed to initialize (bad URL/key). Callers must check
    SUPABASE_CONFIGURED to tell those two cases apart — a broken production
    config should surface as a clean error, never silently fall back to
    writing real signups into the local dry-run file.
    """
    global _supabase_client, _supabase_init_attempted
    if _supabase_init_attempted:
        return _supabase_client
    _supabase_init_attempted = True
    if SUPABASE_CONFIGURED:
        from supabase import create_client

        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        except Exception as exc:
            current_app.logger.error(
                "Supabase client init failed — check SUPABASE_URL/SUPABASE_SERVICE_KEY: %s", exc
            )
            _supabase_client = None
    return _supabase_client


# Extremely small in-memory per-IP throttle. Good enough to blunt a script
# hammering the endpoint on a single free-tier instance; resets on restart/deploy.
# Shared across all three forms + retries after validation errors, so this
# needs to be generous enough for one person testing free/VIP/WhatsApp back
# to back without tripping it — 5/min turned out to do exactly that.
_rate_limit_hits = {}
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20


def is_rate_limited(ip):
    now = time.time()
    hits = [t for t in _rate_limit_hits.get(ip, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
    hits.append(now)
    _rate_limit_hits[ip] = hits
    return len(hits) > RATE_LIMIT_MAX_REQUESTS


def client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


def normalize_phone(raw):
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("+40"):
        digits = "0" + digits[3:]
    elif digits.startswith("0040"):
        digits = "0" + digits[4:]
    elif digits.startswith("40") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def is_valid_phone(raw):
    return bool(PHONE_RE.match(normalize_phone(raw)))


def load_testimonials():
    path = Path(__file__).parent / "content" / "testimonials.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_legal(key):
    path = Path(__file__).parent / "content" / "legal.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)[key]


# ==========================================================================
# Local-file / Supabase storage helpers, shared by every form endpoint.
# ==========================================================================
def _read_local_keys(path, key):
    keys = set()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    keys.add(json.loads(line)[key])
    return keys


def _append_local(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def insert_waitlist_signup(record):
    """Returns ('inserted' | 'duplicate' | 'error', detail)."""
    if not SUPABASE_CONFIGURED:
        existing = _read_local_keys(LOCAL_FALLBACK_FILE, "email")
        if record["email"] in existing:
            return "duplicate", None
        _append_local(LOCAL_FALLBACK_FILE, record)
        current_app.logger.info("[DEV MODE - no Supabase configured] stored waitlist signup: %s", record)
        return "inserted", None

    supabase = get_supabase()
    if supabase is None:
        return "error", "Supabase client not initialized"

    try:
        supabase.table("waitlist_signups").insert(record).execute()
        return "inserted", None
    except Exception as exc:  # supabase-py raises postgrest.APIError on constraint violations
        message = str(exc)
        if "duplicate key" in message or "23505" in message:
            return "duplicate", None
        current_app.logger.error("Supabase waitlist insert failed: %s", message)
        return "error", message


def insert_whatsapp_signup(record):
    """Returns ('inserted' | 'duplicate' | 'error', detail)."""
    if not SUPABASE_CONFIGURED:
        existing = _read_local_keys(WHATSAPP_LOCAL_FALLBACK_FILE, "phone")
        if record["phone"] in existing:
            return "duplicate", None
        _append_local(WHATSAPP_LOCAL_FALLBACK_FILE, record)
        current_app.logger.info("[DEV MODE - no Supabase configured] stored whatsapp signup: %s", record)
        return "inserted", None

    supabase = get_supabase()
    if supabase is None:
        return "error", "Supabase client not initialized"

    try:
        supabase.table("whatsapp_signups").insert(record).execute()
        return "inserted", None
    except Exception as exc:
        message = str(exc)
        if "duplicate key" in message or "23505" in message:
            return "duplicate", None
        current_app.logger.error("Supabase whatsapp insert failed: %s", message)
        return "error", message


# ==========================================================================
# Email — via Resend's HTTP API (see the RESEND_* comment above for why
# not SMTP). Dry-run (log only) when RESEND_API_KEY/NOTIFY_EMAIL aren't
# set, same defensive pattern as Supabase/Stripe. send_email() is the
# general primitive (send to anyone — used for the customer-facing invoice
# email); send_notification_email() is the thin "to the site owner" wrapper
# used everywhere else.
# ==========================================================================
def send_email(to_addr, subject, html_body):
    if not RESEND_CONFIGURED:
        current_app.logger.info("[DEV MODE - no Resend configured] would send email to %s: %s", to_addr, subject)
        return

    import resend

    resend.api_key = RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": RESEND_FROM_EMAIL,
            "to": [to_addr],
            "subject": subject,
            "html": html_body,
            # If RESEND_FROM_EMAIL is a from-address nobody reads (e.g. a
            # "facturi@" alias with no real mailbox), a customer hitting
            # Reply would otherwise bounce silently and we'd never see it.
            "reply_to": NOTIFY_EMAIL,
        })
    except Exception as exc:
        current_app.logger.error("Failed to send email to %s (%s): %s", to_addr, subject, exc)


def send_notification_email(subject, html_body):
    send_email(NOTIFY_EMAIL, subject, html_body)


def _email_shell(title, rows, header_bg="linear-gradient(90deg,#06b6d4,#3b82f6)", cta=None):
    rows_html = "".join(
        '<tr><td style="padding:8px 14px;color:#64748b;font-size:13px;font-weight:600;'
        'white-space:nowrap;vertical-align:top;">{}</td>'
        '<td style="padding:8px 14px;color:#0f172a;font-size:14px;">{}</td></tr>'.format(
            html.escape(str(label)), html.escape(str(value))
        )
        for label, value in rows
    )
    cta_html = ""
    if cta:
        cta_label, cta_url = cta
        cta_html = (
            '<div style="padding:4px 24px 24px;">'
            '<a href="{url}" style="display:inline-block;background:#06b6d4;color:#020617;'
            'font-weight:700;font-size:14px;text-decoration:none;padding:12px 22px;border-radius:10px;">'
            '{label}</a></div>'
        ).format(url=html.escape(cta_url), label=html.escape(cta_label))
    return (
        '<div style="background:#0f172a;padding:32px 16px;font-family:-apple-system,Segoe UI,Inter,sans-serif;">'
        '<div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:20px;overflow:hidden;'
        'box-shadow:0 20px 45px -20px rgba(2,6,23,0.5);">'
        '<div style="background:{header_bg};padding:20px 24px;">'
        '<div style="color:#020617;font-weight:800;font-size:18px;">{title}</div>'
        '</div>'
        '<table style="width:100%;border-collapse:collapse;">{rows}</table>'
        '{cta}'
        '<div style="padding:14px 24px;color:#94a3b8;font-size:12px;border-top:1px solid #e2e8f0;">'
        'Profa Eficientă — notificare automată de pe pagina de listă de așteptare.'
        '</div></div></div>'
    ).format(header_bg=header_bg, title=html.escape(title), rows=rows_html, cta=cta_html)


def build_signup_email_html(kind, record):
    if kind == "free":
        subject = "Înscriere nouă (Gratuit) — Profa Eficientă"
        body = _email_shell("Înscriere nouă — Gratuit", [
            ("Email", record.get("email", "")),
            ("Sursă", record.get("source") or "—"),
        ])
    elif kind == "vip_paid":
        subject = "Plată VIP confirmată — Profa Eficientă"
        amount = record.get("amount_paid_ron")
        body = _email_shell(
            "Plată VIP confirmată",
            [
                ("Email", record.get("email", "")),
                ("Telefon", record.get("phone") or "—"),
                ("Sumă", "{:.2f} RON".format(amount) if amount is not None else "—"),
                ("Sursă", record.get("source") or "—"),
                ("Stripe session", record.get("stripe_session_id") or "—"),
            ],
            header_bg="linear-gradient(90deg,#22d3ee,#3b82f6)",
        )
    elif kind == "whatsapp":
        subject = "Cerere nouă — Cancelaria WhatsApp"
        body = _email_shell(
            "Cerere nouă — Cancelaria WhatsApp",
            [
                ("Telefon", record.get("phone", "")),
                ("Sursă", record.get("source") or "—"),
            ],
            header_bg="linear-gradient(90deg,#25d366,#128c7e)",
        )
    else:
        subject = "Notificare — Profa Eficientă"
        body = _email_shell("Notificare", [(k, v) for k, v in record.items()])
    return subject, body


def build_customer_invoice_email_html(record, invoice_link):
    """The email sent to the *payer* (not the site owner) after a confirmed
    VIP payment: confirms the charge and links to the downloadable invoice
    hosted on our own domain (/vip-invoice/<session_id>, which redirects to
    Stripe's PDF live rather than storing a URL that could go stale)."""
    subject = "Factura ta VIP — Profa Eficientă"
    amount = record.get("amount_paid_ron") or VIP_PRICE_RON
    body = _email_shell(
        "Plata ta VIP a fost confirmată",
        [
            ("Sumă plătită", "{:.2f} RON".format(amount)),
            ("Acces", "Anticipat, 1 lună gratuită, suport telefonic 24/7"),
        ],
        header_bg="linear-gradient(90deg,#22d3ee,#3b82f6)",
        cta=("Descarcă factura (PDF)", invoice_link),
    )
    return subject, body


def get_stripe_invoice_pdf_url(session_id):
    """Looks up the invoice PDF URL for a completed Checkout Session, live
    from Stripe each time rather than caching it — invoice_pdf links are
    long-lived, but this avoids ever needing a schema change or worrying
    about a stored URL going stale."""
    if not STRIPE_CONFIGURED:
        return None
    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    try:
        session_obj = stripe.checkout.Session.retrieve(session_id, expand=["invoice"])
        invoice = session_obj.get("invoice")
        if isinstance(invoice, dict):
            return invoice.get("invoice_pdf")
    except Exception as exc:
        current_app.logger.warning("Could not retrieve invoice for session %s: %s", session_id, exc)
    return None


def get_stripe_receipt_url(session_id):
    """Looks up Stripe's hosted payment receipt (proof of charge: amount,
    date, card last 4) for a completed Checkout Session. This is Stripe's
    "receipt" object, not the Romanian legal "bon fiscal" cash-register
    document — no online payment processor issues that; it's a different
    regulatory system (in-person fiscal cash registers)."""
    if not STRIPE_CONFIGURED:
        return None
    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    try:
        session_obj = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent.latest_charge"])
        payment_intent = session_obj.get("payment_intent")
        if isinstance(payment_intent, dict):
            charge = payment_intent.get("latest_charge")
            if isinstance(charge, dict):
                return charge.get("receipt_url")
    except Exception as exc:
        current_app.logger.warning("Could not retrieve receipt for session %s: %s", session_id, exc)
    return None


@waitlist_bp.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@waitlist_bp.route("/")
def index():
    return render_template(
        "waitlist/index.html",
        site_name=SITE_NAME,
        site_url=SITE_URL,
        testimonials=load_testimonials(),
    )


@waitlist_bp.route("/termeni")
def terms():
    return render_template("waitlist/legal.html", site_name=SITE_NAME, page=load_legal("terms"))


@waitlist_bp.route("/confidentialitate")
def privacy():
    return render_template("waitlist/legal.html", site_name=SITE_NAME, page=load_legal("privacy"))


@waitlist_bp.route("/vip-success")
def vip_success():
    """Thank-you page Stripe redirects to after a successful VIP payment.

    This is purely the user-facing confirmation. The Stripe webhook below is
    the authoritative place that records the paid signup and sends the
    notification email — it doesn't depend on the visitor's browser
    successfully completing this redirect.
    """
    session_id = request.args.get("session_id")
    verified = False
    invoice_url = None
    receipt_url = None
    if STRIPE_CONFIGURED and session_id:
        import stripe

        stripe.api_key = STRIPE_SECRET_KEY
        try:
            session_obj = stripe.checkout.Session.retrieve(session_id, expand=["invoice"])
            verified = session_obj.get("payment_status") == "paid"
            invoice = session_obj.get("invoice")
            if verified and isinstance(invoice, dict) and invoice.get("invoice_pdf"):
                invoice_url = url_for("waitlist.vip_invoice", session_id=session_id)
            if verified and get_stripe_receipt_url(session_id):
                receipt_url = url_for("waitlist.vip_receipt", session_id=session_id)
        except Exception as exc:
            current_app.logger.warning("Could not verify VIP checkout session %s: %s", session_id, exc)
    return render_template(
        "waitlist/vip_success.html", site_name=SITE_NAME, verified=verified,
        invoice_url=invoice_url, receipt_url=receipt_url,
    )


@waitlist_bp.route("/vip-invoice/<session_id>")
def vip_invoice(session_id):
    """Lets a VIP payer download their invoice straight from our site
    instead of only through the email — redirects to Stripe's PDF, looked
    up live so there's nothing to keep in sync if Stripe ever rotates it."""
    pdf_url = get_stripe_invoice_pdf_url(session_id)
    if not pdf_url:
        return apology_document_not_found()
    return redirect(pdf_url)


@waitlist_bp.route("/vip-receipt/<session_id>")
def vip_receipt(session_id):
    """Stripe's payment receipt (proof of charge) — a separate document
    from the invoice above, and not the Romanian legal 'bon fiscal'
    cash-register document (see get_stripe_receipt_url)."""
    receipt_url = get_stripe_receipt_url(session_id)
    if not receipt_url:
        return apology_document_not_found()
    return redirect(receipt_url)


def apology_document_not_found():
    return (
        "<div style=\"font-family:sans-serif;max-width:32rem;margin:4rem auto;text-align:center;color:#334155;\">"
        "<h1>Documentul nu a fost găsit</h1>"
        "<p>Fie plata nu s-a finalizat încă, fie linkul este greșit. "
        "Verifică emailul de confirmare sau scrie-ne la adresa din pagina de confidențialitate.</p>"
        "</div>",
        404,
    )


@waitlist_bp.route("/health")
def health():
    """Lightweight readiness check for this blueprint (Supabase/Stripe/Resend
    config status), reachable at /cadoul-matematic/health once mounted.

    When Supabase is configured this also makes a trivial read against it.
    Supabase's free tier pauses a project after ~7 days with no API
    activity — if this app is ever pinged by an uptime/keep-alive monitor
    again (it was, back when this ran as its own standalone Render service;
    see waitlist/README.md), hitting this route keeps Supabase warm too,
    instead of needing a separate keep-alive job just for the database.
    """
    if not SUPABASE_CONFIGURED:
        supabase_status = "not_configured"
    else:
        supabase = get_supabase()
        if supabase is None:
            supabase_status = "error"
        else:
            try:
                supabase.table("waitlist_signups").select("id").limit(1).execute()
                supabase_status = "ok"
            except Exception as exc:
                current_app.logger.warning("Supabase health ping failed: %s", exc)
                supabase_status = "error"
    return jsonify({
        "status": "ok",
        "supabase": supabase_status,
        "stripe": "configured" if STRIPE_CONFIGURED else "not_configured",
        "email": "configured" if RESEND_CONFIGURED else "not_configured",
    })


@waitlist_bp.route("/api/waitlist", methods=["POST"])
def api_waitlist():
    if is_rate_limited(client_ip()):
        return jsonify({"ok": False, "error": "rate_limited", "message": "Prea multe încercări. Mai încearcă în puțin timp."}), 429

    data = request.get_json(silent=True) or {}

    # Honeypot: a hidden field real users never fill in. Named away from
    # common autofill tokens ("company", "website", ...) so password
    # managers/browser autofill don't fill it in on a real visitor by
    # mistake — that would look like a bot and silently drop the signup.
    # Bots that fill in every field trip it and get an accepted-looking
    # (200) response so they don't learn to avoid the check, but nothing
    # is stored.
    if (data.get("hp_field") or "").strip():
        return jsonify({"ok": True, "message": "Te-ai înscris cu succes."}), 201

    email = (data.get("email") or "").strip().lower()
    tier = (data.get("tier") or "").strip().lower()
    source = (data.get("source") or "").strip()[:100]

    if not email or not EMAIL_RE.match(email) or len(email) > 254:
        return jsonify({"ok": False, "error": "invalid_email", "message": "Adresa de email nu este validă."}), 400

    if tier not in VALID_TIERS:
        return jsonify({"ok": False, "error": "invalid_tier", "message": "Opțiune de înscriere invalidă."}), 400

    if tier == "vip":
        # VIP now requires payment — the client should be calling
        # /api/vip-checkout instead. This is just a defensive guard.
        return jsonify({"ok": False, "error": "use_checkout", "message": "Accesul VIP necesită plată — folosește formularul VIP."}), 400

    record = {"email": email, "tier": "free", "source": source or None}
    status, detail = insert_waitlist_signup(record)

    if status == "duplicate":
        return jsonify({"ok": True, "already_registered": True, "message": "Ești deja pe listă."}), 200
    if status == "error":
        return jsonify({"ok": False, "error": "server_error", "message": "A apărut o eroare. Mai încearcă o dată."}), 500

    subject, body = build_signup_email_html("free", record)
    send_notification_email(subject, body)
    return jsonify({"ok": True, "message": "Te-ai înscris cu succes."}), 201


@waitlist_bp.route("/api/vip-checkout", methods=["POST"])
def api_vip_checkout():
    """Creates a Stripe Checkout Session for the one-time 50 RON VIP fee and
    hands the browser a redirect URL. Nothing is written to Supabase here —
    the signup is only recorded once Stripe confirms payment via webhook."""
    if is_rate_limited(client_ip()):
        return jsonify({"ok": False, "error": "rate_limited", "message": "Prea multe încercări. Mai încearcă în puțin timp."}), 429

    data = request.get_json(silent=True) or {}

    if (data.get("hp_field") or "").strip():
        return jsonify({"ok": True, "message": "OK"}), 200

    email = (data.get("email") or "").strip().lower()
    phone_raw = (data.get("phone") or "").strip()
    source = (data.get("source") or "").strip()[:100]

    if not email or not EMAIL_RE.match(email) or len(email) > 254:
        return jsonify({"ok": False, "error": "invalid_email", "message": "Adresa de email nu este validă."}), 400
    if not is_valid_phone(phone_raw):
        return jsonify({"ok": False, "error": "invalid_phone", "message": "Numărul de telefon nu este valid."}), 400

    if not STRIPE_CONFIGURED:
        return jsonify({"ok": False, "error": "payment_not_configured", "message": "Plata nu este încă disponibilă. Încearcă din nou mai târziu."}), 503

    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    try:
        session_obj = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=email,
            locale="ro",  # Checkout page language + the auto-generated invoice's language
            line_items=[{
                "price_data": {
                    "currency": "ron",
                    "unit_amount": VIP_PRICE_RON * 100,
                    "product_data": {
                        "name": "Acces VIP — Profa Eficientă",
                        "description": "Acces anticipat, o lună gratuită și suport telefonic 24/7.",
                    },
                },
                "quantity": 1,
            }],
            invoice_creation={"enabled": True},
            metadata={"phone": normalize_phone(phone_raw), "source": source or "", "tier": "vip"},
            success_url=SITE_URL + url_for("waitlist.vip_success") + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=SITE_URL + url_for("waitlist.index") + "#waitlist",
        )
    except Exception as exc:
        current_app.logger.error("Stripe checkout session creation failed: %s", exc)
        return jsonify({"ok": False, "error": "server_error", "message": "A apărut o eroare la inițierea plății. Mai încearcă o dată."}), 500

    return jsonify({"ok": True, "url": session_obj.url}), 200


@waitlist_bp.route("/api/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """Authoritative source of truth for VIP signups: Stripe calls this
    server-to-server once payment actually completes, independent of
    whether the visitor's browser makes it back to /vip-success."""
    if not STRIPE_CONFIGURED or not STRIPE_WEBHOOK_SECRET:
        return jsonify({"ok": False, "error": "not_configured"}), 503

    import stripe

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        current_app.logger.warning("Stripe webhook rejected (bad signature/payload): %s", exc)
        return jsonify({"ok": False, "error": "invalid_signature"}), 400

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        email = (
            (session_obj.get("customer_details") or {}).get("email")
            or session_obj.get("customer_email")
            or ""
        ).strip().lower()
        metadata = session_obj.get("metadata") or {}
        amount_total = session_obj.get("amount_total")

        if email:
            record = {
                "email": email,
                "tier": "vip",
                "phone": metadata.get("phone") or None,
                "source": metadata.get("source") or None,
                "stripe_session_id": session_obj.get("id"),
                "amount_paid_ron": (amount_total / 100.0) if amount_total else None,
            }
            status, detail = insert_waitlist_signup(record)
            if status == "inserted":
                subject, body = build_signup_email_html("vip_paid", record)
                send_notification_email(subject, body)

                # Customer-facing invoice email — sent regardless of whether
                # Stripe's own dashboard "email finalized invoices" setting
                # is on, so delivery doesn't depend on an account setting we
                # can't verify from here.
                invoice_link = SITE_URL + url_for("waitlist.vip_invoice", session_id=session_obj.get("id"))
                customer_subject, customer_body = build_customer_invoice_email_html(record, invoice_link)
                send_email(email, customer_subject, customer_body)
            elif status == "error":
                current_app.logger.error("Failed to record VIP payment for %s: %s", email, detail)
        else:
            current_app.logger.warning("Stripe checkout.session.completed with no email; session=%s", session_obj.get("id"))

    return jsonify({"received": True}), 200


@waitlist_bp.route("/api/whatsapp", methods=["POST"])
def api_whatsapp():
    if is_rate_limited(client_ip()):
        return jsonify({"ok": False, "error": "rate_limited", "message": "Prea multe încercări. Mai încearcă în puțin timp."}), 429

    data = request.get_json(silent=True) or {}

    if (data.get("hp_field") or "").strip():
        return jsonify({"ok": True, "message": "Te-ai alăturat grupului."}), 201

    phone_raw = (data.get("phone") or "").strip()
    source = (data.get("source") or "").strip()[:100]

    if not is_valid_phone(phone_raw):
        return jsonify({"ok": False, "error": "invalid_phone", "message": "Numărul de telefon nu este valid."}), 400

    record = {"phone": normalize_phone(phone_raw), "source": source or None}
    status, detail = insert_whatsapp_signup(record)

    if status == "duplicate":
        return jsonify({"ok": True, "already_registered": True, "message": "Numărul tău e deja înscris."}), 200
    if status == "error":
        return jsonify({"ok": False, "error": "server_error", "message": "A apărut o eroare. Mai încearcă o dată."}), 500

    subject, body = build_signup_email_html("whatsapp", record)
    send_notification_email(subject, body)
    return jsonify({"ok": True, "message": "Te-ai alăturat grupului."}), 201


if __name__ == "__main__":
    # Standalone dev server: mounts this blueprint with no url_prefix, so it
    # behaves exactly like the old standalone app (routes at /, /api/waitlist,
    # etc.) for isolated iteration on the landing page. When imported by the
    # main project (app.py at the repo root) this blueprint is registered
    # with url_prefix="/cadoul-matematic" instead — see that file.
    from flask import Flask

    standalone_app = Flask(__name__)
    standalone_app.register_blueprint(waitlist_bp)
    standalone_app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
