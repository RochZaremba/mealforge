"""Verify and decrypt into an explicitly selected new local file, mode 0600."""
import argparse
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from backup_integrity import verified_ciphertext

parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
secret = os.environ.get("BACKUP_PASSPHRASE_FILE")
if not secret:
    raise SystemExit("Ustaw BACKUP_PASSPHRASE_FILE.")
secret_path = Path(secret).resolve()
if not secret_path.is_file() or stat.S_IMODE(secret_path.stat().st_mode) & 0o077:
    raise SystemExit("Plik hasła wymaga prywatnych uprawnień.")
password_lines = secret_path.read_bytes().splitlines()
if not password_lines or not password_lines[0]:
    raise SystemExit("Plik hasła nie może być pusty.")
password = password_lines[0]
os.umask(0o077)
try:
    with tempfile.TemporaryDirectory() as directory:
        ciphertext = Path(directory) / "verified.enc"
        verified_ciphertext(args.input, ciphertext, password)
        with args.output.open("xb") as output:
            result = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "file:" + str(secret_path)], stdin=ciphertext.open("rb"), stdout=output, check=False)
        if result.returncode:
            args.output.unlink(missing_ok=True)
            raise SystemExit("Odszyfrowanie nie powiodło się.")
except ValueError as error:
    raise SystemExit(str(error)) from None
print("Backup zweryfikowano i odszyfrowano:", args.output)
