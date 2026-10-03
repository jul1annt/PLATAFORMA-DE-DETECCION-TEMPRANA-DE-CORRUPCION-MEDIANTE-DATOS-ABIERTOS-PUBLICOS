from cryptography.fernet import Fernet

from core.config import settings
from modules.ingesta.security import ENCRYPTED_PREFIX, decrypt_api_key, encrypt_api_key


def test_api_key_with_version_prefix_is_still_encrypted(monkeypatch):
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    secret = "enc:v1:provider-secret-value"

    stored = encrypt_api_key(secret)

    assert stored.startswith(ENCRYPTED_PREFIX)
    assert stored != secret
    assert decrypt_api_key(stored) == secret
