"""Real development pg_dump/encrypted-backup/pg_restore on a disposable DB."""
import os
from hashlib import sha256
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
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
snapshot_connection = None


def fingerprints(connection: Connection) -> dict[str, tuple[int, str]]:
    """Compare every public table without printing credentials or health values."""
    tables = connection.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )).scalars().all()
    result = {}
    for table in tables:
        identifier = connection.dialect.identifier_preparer.quote_identifier(table)
        rows = connection.execute(text(f"SELECT row_to_json(t)::text FROM public.{identifier} AS t")).scalars().all()
        digest = sha256()
        for row in sorted(rows):
            encoded = row.encode()
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
        result[table] = (len(rows), digest.hexdigest())
    return result


try:
    snapshot_connection = source.connect().execution_options(isolation_level="REPEATABLE READ")
    snapshot = snapshot_connection.scalar(text("SELECT pg_export_snapshot()"))
    expected = fingerprints(snapshot_connection)
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        password = base / "passphrase"
        password.write_text(secrets.token_urlsafe(48))
        password.chmod(0o600)
        environment = dict(os.environ, BACKUP_PASSPHRASE_FILE=str(password), BACKUP_SNAPSHOT=snapshot)
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
            actual = fingerprints(connection)
        if expected != actual:
            raise RuntimeError("Restored table fingerprints differ")
        print(f"PASS: real pg_dump → authenticated encryption → verified decrypt → disposable pg_restore; {len(actual)} tables / {sum(item[0] for item in actual.values())} rows match (private values not logged)")
finally:
    if snapshot_connection is not None:
        snapshot_connection.close()
    source.dispose()
    restored.dispose()
    if created:
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"), {"name": database})
            connection.execute(text(f'DROP DATABASE "{database}"'))
    admin.dispose()
    if backup:
        backup.unlink(missing_ok=True)
