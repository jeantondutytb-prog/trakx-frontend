"""
Email de relance pour les comptes en essai (trial) qui n'ont pas encore pris
d'abonnement payant.

Cible : table `subscriptions` du backend (Postgres via DATABASE_URL), status
= 'trial'. Met en avant la fin d'essai imminente + code -20% RETOUR20 pour
pousser vers un abonnement payant.

Usage:
    pip install httpx pg8000
    SUPABASE_SERVICE_ROLE_KEY=xxx RESEND_API_KEY=re_xxx DATABASE_URL=postgresql://... python3 send_trial_email.py

    # Mode test (envoie uniquement à TOI) :
    SUPABASE_SERVICE_ROLE_KEY=xxx RESEND_API_KEY=re_xxx python3 send_trial_email.py --test
"""

import os, sys, time, httpx
from datetime import datetime, timezone

SUPABASE_URL = "https://apwedqsklyzroeyrokqb.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
RESEND_KEY   = os.environ.get("RESEND_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
FROM_EMAIL   = "Jean de Trakx <jean@trakx.fr>"
TEST_EMAIL   = "jeantondut@gmail.com"
TEST_MODE    = "--test" in sys.argv

if not SUPABASE_KEY or not RESEND_KEY or (not TEST_MODE and not DATABASE_URL):
    print("❌ Variables manquantes. Lance avec:")
    print("   SUPABASE_SERVICE_ROLE_KEY=xxx RESEND_API_KEY=re_xxx DATABASE_URL=postgresql://... python3 send_trial_email.py")
    sys.exit(1)


def get_all_users():
    """Récupère tous les users Supabase (paginé par 1000)."""
    users, page = [], 1
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    while True:
        r = httpx.get(
            f"{SUPABASE_URL}/auth/v1/admin/users?page={page}&per_page=1000",
            headers=headers, timeout=30
        )
        r.raise_for_status()
        batch = r.json().get("users", [])
        users.extend(batch)
        if len(batch) < 1000:
            break
        page += 1
    return users


def get_trial_users() -> dict[str, str]:
    """Emails en essai actif (status='trial'), mappés à leur trial_expires_at."""
    import pg8000.native

    url = DATABASE_URL.replace("postgresql://", "").replace("postgres://", "")
    user_pass, rest = url.split("@", 1)
    user, password = user_pass.split(":", 1)
    host_db = rest.split("/", 1)
    host_port = host_db[0]
    db = host_db[1].split("?")[0]
    port = 5432
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port

    conn = pg8000.native.Connection(
        user=user, password=password, host=host,
        port=port, database=db, ssl_context=True
    )
    rows = conn.run("SELECT user_email, trial_expires_at FROM subscriptions WHERE status = 'trial'")
    return {row[0].strip().lower(): row[1] for row in rows if row[0]}


def extract_name(user: dict) -> str:
    meta = user.get("user_metadata") or {}
    for key in ("full_name", "name", "first_name", "given_name"):
        val = meta.get(key)
        if val and isinstance(val, str):
            candidate = val.strip().split(" ")[0]
            if candidate.isalpha() and len(candidate) >= 2:
                return candidate.capitalize()
    email = user.get("email", "") or ""
    local = email.split("@")[0].split(".")[0].split("+")[0]
    if local.isalpha() and 2 <= len(local) <= 15:
        return local.capitalize()
    return ""


def days_left(trial_expires_at) -> int | None:
    if not trial_expires_at:
        return None
    try:
        if isinstance(trial_expires_at, str):
            dt = datetime.fromisoformat(trial_expires_at.replace("Z", "+00:00"))
        else:
            dt = trial_expires_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = dt - datetime.now(timezone.utc)
        return max(0, delta.days)
    except Exception:
        return None


SUBJECT = "Ton essai Trakx se termine bientôt — garde l'accès avec -20%"
PREHEADER = "Code RETOUR20, valable cette semaine."

def email_html(first_name: str, days: int | None) -> str:
    greeting = f"Yo {first_name}" if first_name else "Yo"
    if days is None:
        urgency = "Ton essai gratuit touche à sa fin."
    elif days <= 0:
        urgency = "Ton essai gratuit se termine aujourd'hui."
    elif days == 1:
        urgency = "Ton essai gratuit se termine demain."
    else:
        urgency = f"Ton essai gratuit se termine dans {days} jours."
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{SUBJECT}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">

<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{PREHEADER}&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;</div>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f4;">
  <tr><td align="center" style="padding:32px 16px;">
    <table width="540" cellpadding="0" cellspacing="0" style="max-width:540px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;">

      <!-- Header -->
      <tr><td style="padding:28px 32px 0;">
        <span style="font-size:18px;font-weight:800;color:#111111;letter-spacing:-0.3px;">Trakx</span>
      </td></tr>

      <!-- Intro -->
      <tr><td style="padding:20px 32px 0;font-size:16px;line-height:1.6;color:#111111;">
        <p style="margin:0 0 14px;">{greeting} 👋</p>
        <p style="margin:0 0 14px;"><strong style="color:#111111;">{urgency}</strong></p>
        <p style="margin:0;color:#52525b;">Pendant cet essai, t'as eu accès au feed temps réel sur <strong style="color:#111111;">450 000+ annonces Vinted/mois</strong>. Passe au payant maintenant pour ne rien perdre — et garder une longueur d'avance sur les bonnes affaires.</p>
      </td></tr>

      <!-- Discount card -->
      <tr><td style="padding:24px 32px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;">
          <tr><td align="center" style="padding:24px 16px;">
            <div style="font-size:32px;font-weight:800;color:#f97316;line-height:1;">-20%</div>
            <div style="font-size:13px;color:#78716c;margin-top:4px;">sur ton premier mois, n'importe quel plan</div>
            <div style="margin-top:14px;display:inline-block;background:#111111;color:#ffffff;font-weight:700;font-size:14px;letter-spacing:1px;padding:8px 18px;border-radius:8px;">RETOUR20</div>
          </td></tr>
        </table>
      </td></tr>

      <!-- CTA button -->
      <tr><td align="center" style="padding:24px 32px 0;">
        <table cellpadding="0" cellspacing="0">
          <tr><td style="background:#f97316;border-radius:10px;">
            <a href="https://trakx.fr/app/?promo=RETOUR20" style="display:block;padding:14px 36px;font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;">Garder l'accès →</a>
          </td></tr>
        </table>
      </td></tr>

      <!-- Sign-off -->
      <tr><td style="padding:24px 32px 28px;font-size:14px;line-height:1.6;color:#52525b;">
        <p style="margin:0 0 10px;">Une question avant de te lancer ? Réponds à ce mail, je réponds perso.</p>
        <p style="margin:0;">À ton succès (sur Vinted),<br/><strong style="color:#111111;">Jean</strong></p>
      </td></tr>
    </table>

    <table width="540" cellpadding="0" cellspacing="0" style="max-width:540px;width:100%;">
      <tr><td style="padding:16px 32px;" align="center">
        <p style="margin:0;font-size:11px;color:#a1a1aa;">
          Tu reçois cet email car tu as démarré un essai sur <a href="https://trakx.fr" style="color:#a1a1aa;">trakx.fr</a>.
          &nbsp;·&nbsp;
          <a href="https://trakx.fr/app/" style="color:#a1a1aa;">Se désabonner</a>
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def send_email(to: str, html: str) -> bool:
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
        json={"from": FROM_EMAIL, "to": [to], "subject": SUBJECT, "html": html},
        timeout=15
    )
    return r.status_code == 200


def main():
    if TEST_MODE:
        print(f"🧪 MODE TEST — envoi uniquement à {TEST_EMAIL}")
        ok = send_email(TEST_EMAIL, email_html("Jean", 2))
        print("✅ Envoyé !" if ok else "❌ Échec")
        return

    print("📥 Récupération des utilisateurs Supabase…")
    users = get_all_users()
    print("📥 Récupération des essais en cours (Postgres backend)…")
    trial_map = get_trial_users()

    confirmed = [u for u in users if u.get("email") and u.get("email_confirmed_at")]
    targets = [u for u in confirmed if u["email"].strip().lower() in trial_map]

    print(f"📊 Détail : {len(users)} comptes au total")
    print(f"   ✅ {len(confirmed)} confirmés")
    print(f"   ⏳ {len(trial_map)} en essai (status='trial')")
    print(f"   🎯 {len(targets)} ciblé(s) (en essai + confirmés)")
    print()

    if not targets:
        print("Aucun utilisateur à contacter.")
        return

    confirm = input(f"Envoyer l'email à {len(targets)} personnes ? (oui/non) : ").strip().lower()
    if confirm != "oui":
        print("Annulé.")
        return

    ok_count, fail_count = 0, 0
    for i, user in enumerate(targets, 1):
        email = user["email"]
        days = days_left(trial_map.get(email.strip().lower()))
        success = send_email(email, email_html(extract_name(user), days))
        status = "✅" if success else "❌"
        print(f"  {status} [{i}/{len(targets)}] {email}")
        if success:
            ok_count += 1
        else:
            fail_count += 1
        time.sleep(0.2)  # Resend rate limit : 10 req/s

    print()
    print(f"✅ {ok_count} envoyés  ❌ {fail_count} échecs")


if __name__ == "__main__":
    main()
