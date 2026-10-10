"""Create local-only secrets once, without printing them."""
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    print(".env istnieje — zachowano konfigurację.")
else:
    password = secrets.token_urlsafe(32)
    content = (root / ".env.example").read_text().replace("CHANGE_ME_DEV_ONLY", password).replace("CHANGE_ME_GENERATE_WITH_CSPRNG", secrets.token_urlsafe(48))
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write(content)
    print("Utworzono prywatny .env do lokalnego developmentu.")
