"""Real development pg_dump/encrypted-backup/pg_restore on a disposable DB."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
url = make_url(os.environ["DATABASE_URL"])
admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True)
source = create_engine(url, hide_parameters=True)
database = "mealforge_restore_test_" + uuid.uuid4().hex
restored = create_engine(url.set(database=database), hide_parameters=True)
compose = ["docker", "compose", "--env-file", ".env", "-f", "compose.dev.yml", "exec", "-T", "postgres"]
created = False
backup = None
try:
    with source.connect() as connection:
        expected = connection.execute(text("SELECT code, display_name, position FROM meal_slot_definitions ORDER BY code")).all()
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        password = base / "passphrase"
        password.write_text(secrets.token_urlsafe(48))
        password.chmod(0o600)
        environment = dict(os.environ, BACKUP_PASSPHRASE_FILE=str(password))
        before = set((root / "backups").glob("*.dump.enc"))
        subprocess.run([sys.executable, "scripts/backup.py"], cwd=root, env=environment, check=True)
        new_files = set((root / "backups").glob("*.dump.enc")) - before
        if len(new_files) != 1:
            raise RuntimeError("Expected one backup from current test")
        backup = new_files.pop()
        dump = base / "restore.dump"
        subprocess.run([sys.executable, "scripts/decrypt_backup.py", str(backup), str(dump)], cwd=root, env=environment, check=True)
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database}"'))
        created = True
        with dump.open("rb") as input_file:
            subprocess.run(compose + ["sh", "-c", 'pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error --no-owner --no-privileges', "restore", database], cwd=root, stdin=input_file, check=True)
        with restored.connect() as connection:
            actual = connection.execute(text("SELECT code, display_name, position FROM meal_slot_definitions ORDER BY code")).all()
        if expected != actual:
            raise RuntimeError("Restored reference rows differ")
        print("PASS: real pg_dump → authenticated encryption → verified decrypt → disposable pg_restore; reference rows match")
finally:
    source.dispose()
    restored.dispose()
    if created:
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"), {"name": database})
            connection.execute(text(f'DROP DATABASE "{database}"'))
    admin.dispose()
    if backup:
        backup.unlink(missing_ok=True)
