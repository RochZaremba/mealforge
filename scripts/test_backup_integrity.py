import tempfile
from pathlib import Path
import unittest
from backup_integrity import seal, verified_ciphertext


class BackupIntegrityTests(unittest.TestCase):
    def test_valid_and_tampered_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            original = base / "source"
            original.write_bytes(b"ciphertext-content" * 1000)
            sealed = base / "sealed"
            seal(original, sealed, b"test-only")
            output = base / "restored"
            verified_ciphertext(sealed, output, b"test-only")
            self.assertEqual(output.read_bytes(), original.read_bytes())
            with self.assertRaises(ValueError):
                verified_ciphertext(sealed, base / "wrong", b"wrong-password")
            self.assertFalse((base / "wrong").exists())
            payload = bytearray(sealed.read_bytes())
            payload[-1] ^= 1
            sealed.write_bytes(payload)
            with self.assertRaises(ValueError):
                verified_ciphertext(sealed, base / "tampered", b"test-only")
            self.assertFalse((base / "tampered").exists())


if __name__ == "__main__":
    unittest.main()
