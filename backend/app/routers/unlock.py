"""
Unlock endpoint — serves a password form and decrypts the vault.

When the app is in vault mode (a .vault file exists), all other routes
return 503 until the master password is entered here.
"""

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.vault import vault_manager

router = APIRouter()

UNLOCK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unlock - Signup Manager</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f172a; color: #e2e8f0;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh;
        }}
        .card {{
            background: #1e293b; border-radius: 12px; padding: 2.5rem;
            width: 100%; max-width: 400px;
            box-shadow: 0 25px 50px rgba(0,0,0,.3);
        }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
        .subtitle {{ color: #94a3b8; font-size: 0.875rem; margin-bottom: 1.5rem; }}
        label {{ display: block; font-size: 0.875rem; margin-bottom: 0.5rem; color: #cbd5e1; }}
        input[type="password"] {{
            width: 100%; padding: 0.75rem 1rem; border-radius: 8px;
            border: 1px solid #334155; background: #0f172a; color: #e2e8f0;
            font-size: 1rem; margin-bottom: 1.25rem; outline: none;
        }}
        input:focus {{ border-color: #3b82f6; }}
        button {{
            width: 100%; padding: 0.75rem; border-radius: 8px; border: none;
            background: #3b82f6; color: white; font-size: 1rem; font-weight: 600;
            cursor: pointer; transition: background 0.2s;
        }}
        button:hover {{ background: #2563eb; }}
        .error {{ color: #f87171; font-size: 0.875rem; margin-bottom: 1rem; }}
        .lock-icon {{ font-size: 2.5rem; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="lock-icon">&#x1f512;</div>
        <h1>Unlock Application</h1>
        <p class="subtitle">Enter the master password to decrypt secrets and start the application.</p>
        {error}
        <form method="post" action="/api/unlock">
            <label for="password">Master Password</label>
            <input type="password" id="password" name="password" required autofocus
                   autocomplete="current-password">
            <button type="submit">Unlock</button>
        </form>
    </div>
</body>
</html>"""


@router.get("/unlock", response_class=HTMLResponse)
async def unlock_page():
    """Serve the unlock form, or redirect to home if already unlocked."""
    if vault_manager.is_unlocked:
        return RedirectResponse(url="/", status_code=302)
    return UNLOCK_HTML.format(error="")


@router.post("/unlock")
async def unlock(password: str = Form(...)):
    """Decrypt the vault and initialize the application."""
    if vault_manager.is_unlocked:
        return RedirectResponse(url="/", status_code=303)

    try:
        success = vault_manager.unlock(password)
    except FileNotFoundError:
        return HTMLResponse(
            UNLOCK_HTML.format(
                error='<div class="error">Vault file not found. Run: python vault.py create</div>'
            ),
            status_code=500,
        )

    if not success:
        return HTMLResponse(
            UNLOCK_HTML.format(
                error='<div class="error">Invalid master password.</div>'
            ),
            status_code=401,
        )

    # Load secrets into settings and initialize the app
    from app.config import load_secrets_from_vault
    from app.services.encryption import encryption_service
    from app.database import engine, Base, SessionLocal
    from app.utils.db_init import create_first_admin

    secrets = vault_manager.secrets
    load_secrets_from_vault(secrets)

    from app.config import settings
    encryption_service.initialize(settings.ENCRYPTION_KEY)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_first_admin(db)
    finally:
        db.close()

    # 303 See Other — browser follows redirect with GET
    return RedirectResponse(url="/", status_code=303)
