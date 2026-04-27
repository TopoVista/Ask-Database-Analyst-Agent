from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import get_settings


def _local_key() -> bytes:
    digest = hashlib.sha256(b"decision-intelligence-agent-local-key").digest()
    return base64.urlsafe_b64encode(digest)


class EncryptionService:
    def __init__(self) -> None:
        settings = get_settings()
        key = settings.encryption_key.encode("utf-8") if settings.encryption_key else _local_key()
        try:
            self.cipher = Fernet(key)
        except Exception:
            self.cipher = Fernet(_local_key())

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

