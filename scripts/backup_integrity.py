"""Authenticate encrypted backups before permitting decryption (stdlib HMAC)."""
import hashlib
import hmac
import os
from pathlib import Path
import tempfile

MAGIC = b"MEALFORGE-BACKUP-1\n"
ITERATIONS = 200_000


def key_for(password: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, b"mealforge-auth-v1" + salt, ITERATIONS)


def seal(ciphertext: Path, destination: Path, password: bytes) -> None:
    salt = os.urandom(32)
    digest = hmac.new(key_for(password, salt), MAGIC + salt, "sha256")
    with ciphertext.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    with destination.open("xb") as output, ciphertext.open("rb") as source:
        output.write(MAGIC + salt + digest.digest())
        while block := source.read(1024 * 1024):
            output.write(block)
    destination.chmod(0o600)


def verified_ciphertext(source: Path, destination: Path, password: bytes) -> None:
    # Verification operates on an immutable private spool before creating output.
    with source.open("rb") as input_file, tempfile.TemporaryFile() as spool:
        magic = input_file.read(len(MAGIC))
        salt = input_file.read(32)
        expected = input_file.read(32)
        if magic != MAGIC or len(salt) != 32 or len(expected) != 32:
            raise ValueError("Nieprawidłowy format backupu.")
        digest = hmac.new(key_for(password, salt), MAGIC + salt, "sha256")
        while block := input_file.read(1024 * 1024):
            digest.update(block)
            spool.write(block)
        if not hmac.compare_digest(expected, digest.digest()):
            raise ValueError("Backup uszkodzony lub hasło nieprawidłowe.")
        spool.seek(0)
        with destination.open("xb") as output:
            while block := spool.read(1024 * 1024):
                output.write(block)
        destination.chmod(0o600)
