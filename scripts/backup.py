"""Encrypted development DB backup; no passphrases in process arguments."""
import os
from pathlib import Path
import re
import stat
import subprocess
from datetime import datetime, timezone
from backup_integrity import seal

root = Path(__file__).resolve().parents[1]
secret = os.environ.get("BACKUP_PASSPHRASE_FILE")
if not secret:
    raise SystemExit("Ustaw BACKUP_PASSPHRASE_FILE na prywatny plik hasła szyfrowania (chmod 600).")
secret_path = Path(secret).resolve()
if not secret_path.is_file() or stat.S_IMODE(secret_path.stat().st_mode) & 0o077:
    raise SystemExit("Plik hasła musi istnieć i być dostępny tylko dla właściciela.")
password_lines = secret_path.read_bytes().splitlines()
if not password_lines or not password_lines[0]:
    raise SystemExit("Plik hasła nie może być pusty.")
password = password_lines[0]
os.umask(0o077)
directory = root / "backups"
directory.mkdir(exist_ok=True, mode=0o700)
output = directory / (datetime.now(timezone.utc).strftime("mealforge-%Y%m%dT%H%M%S-%fZ.dump.enc"))
snapshot = os.environ.get("BACKUP_SNAPSHOT")
if snapshot and not re.fullmatch(r"[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+", snapshot):
    raise SystemExit("Nieprawidłowy identyfikator snapshotu PostgreSQL.")
command = ["docker", "compose", "--env-file", ".env", "-f", "compose.dev.yml", "exec", "-T", "postgres", "sh", "-c", 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc "$@"', "backup"]
if snapshot:
    command += ["--snapshot", snapshot]
ciphertext = output.with_suffix(".partial")
with ciphertext.open("xb") as destination:
    dump = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE)
    assert dump.stdout is not None
    encryption = subprocess.Popen(["openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "200000", "-pass", "file:" + str(secret_path)], stdin=dump.stdout, stdout=destination)
    dump.stdout.close()
    encrypt_status = encryption.wait()
    dump_status = dump.wait()
if dump_status or encrypt_status:
    ciphertext.unlink(missing_ok=True)
    raise SystemExit("Backup nie powiódł się — usunięto niekompletny plik.")
try:
    seal(ciphertext, output, password)
finally:
    ciphertext.unlink(missing_ok=True)
print("Zapisano szyfrowany i uwierzytelniony backup:", output)
