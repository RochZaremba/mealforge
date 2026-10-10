"""Prove PostgreSQL records the error, without recording its private bound value."""
import argparse
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configure-ci", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    url = make_url(os.environ["DATABASE_URL"])
    container = os.environ.get("POSTGRES_LOG_CONTAINER")
    if not container:
        result = subprocess.run([
            "docker", "compose", "--env-file", ".env", "-f", "compose.dev.yml",
            "ps", "-q", "postgres",
        ], cwd=root, check=True, capture_output=True, text=True, timeout=10)
        container = result.stdout.strip()
    if not container:
        raise SystemExit("Brak kontenera PostgreSQL do testu prywatności logów.")
    configuration = {
        "log_error_verbosity": "terse",
        "log_min_error_statement": "panic",
        "log_parameter_max_length_on_error": "0",
    }
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True)
    database = "mealforge_log_test_" + uuid4().hex
    engine = create_engine(url.set(database=database), hide_parameters=True)
    created = False
    try:
        with admin.connect() as connection:
            if arguments.configure_ci:
                if (os.environ.get("APP_ENV") != "test" or url.database != "mealforge_ci"
                        or not os.environ.get("POSTGRES_LOG_CONTAINER")):
                    raise SystemExit("Zmiana logowania jest dozwolona wyłącznie dla jawnego serwisu CI.")
                for setting, value in configuration.items():
                    connection.execute(text(f"ALTER SYSTEM SET {setting} = '{value}'"))
                connection.execute(text("SELECT pg_reload_conf()"))
                # Reload is asynchronous; new connections inherit the updated settings.
                time.sleep(0.5)
            connection.execute(text(f'CREATE DATABASE "{database}"'))
            created = True
        with engine.connect() as connection:
            actual = dict(connection.execute(text(
                "SELECT name, setting FROM pg_settings WHERE name IN "
                "('log_error_verbosity', 'log_min_error_statement', 'log_parameter_max_length_on_error')"
            )).all())
        if actual != configuration:
            raise SystemExit("Konfiguracja PostgreSQL może ujawniać dane prywatne w logach.")
        table = "privacy_probe_" + uuid4().hex
        marker = table + "_email_key"
        sentinel = "private-" + uuid4().hex + "@example.invalid"
        rejected = False
        try:
            with engine.begin() as connection:
                connection.execute(text(f'CREATE TEMP TABLE "{table}" (email text UNIQUE)'))
                insert = text(f'INSERT INTO "{table}" (email) VALUES (:email)')
                connection.execute(insert, {"email": sentinel})
                connection.execute(insert, {"email": sentinel})
        except IntegrityError:
            rejected = True
        if not rejected:
            raise SystemExit("Nie wykonano rzeczywistego błędu constraintu PostgreSQL.")
        found_error = False
        for _ in range(30):
            result = subprocess.run(["docker", "logs", container], check=True, capture_output=True, text=True, timeout=10)
            logs = result.stdout + result.stderr
            if sentinel in logs:
                raise SystemExit("FAIL: prywatna wartość parametru trafiła do logu PostgreSQL.")
            if marker in logs:
                found_error = True
                break
            time.sleep(0.1)
        if not found_error:
            raise SystemExit("Nie potwierdzono zapisu błędu; wynik testu nie jest wiarygodny.")
        print("PASS: rzeczywisty błąd UNIQUE zapisany; prywatny parametr nie pojawia się w logach.")
    finally:
        engine.dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:name AND pid<>pg_backend_pid()"
                ), {"name": database})
                connection.execute(text(f'DROP DATABASE "{database}"'))
        admin.dispose()


if __name__ == "__main__":
    main()
