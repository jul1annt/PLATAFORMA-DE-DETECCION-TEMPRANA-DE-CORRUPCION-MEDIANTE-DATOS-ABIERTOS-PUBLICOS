from types import SimpleNamespace

from cryptography.fernet import Fernet

from core.config import settings
from modules.ingesta.security import ENCRYPTED_PREFIX, decrypt_api_key, encrypt_api_key
from scripts import rotate_source_keys


class _Database:
    def __init__(self, sources, fail_commit=False):
        self.sources = sources
        self.fail_commit = fail_commit
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def query(self, _model):
        database = self

        class Query:
            def filter(self, *_args, **_kwargs):
                return self

            def all(self):
                return database.sources

        return Query()

    def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("commit failed")

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _configure_keys(monkeypatch):
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", new_key)
    monkeypatch.setattr(settings, "ENCRYPTION_KEY_PREVIOUS", old_key)
    monkeypatch.setenv("ENCRYPTION_KEY_OLD", old_key)
    return old_key, new_key


def test_rotation_dry_run_reads_old_key_but_does_not_write(monkeypatch, capsys):
    old_key, _new_key = _configure_keys(monkeypatch)
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", old_key)
    old_ciphertext = encrypt_api_key("source-secret")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    # Restore the previous key for the decrypt fallback during dry-run.
    monkeypatch.setattr(settings, "ENCRYPTION_KEY_PREVIOUS", old_key)
    source = SimpleNamespace(api_key=old_ciphertext)
    database = _Database([source])
    monkeypatch.setattr(rotate_source_keys, "SessionLocal", lambda: database)
    monkeypatch.setattr("sys.argv", ["rotate_source_keys.py"])

    rotate_source_keys.main()

    assert "Cifradas con clave anterior: 1" in capsys.readouterr().out
    assert source.api_key == old_ciphertext
    assert database.commits == database.rollbacks == 0
    assert database.closed


def test_rotation_applies_new_and_legacy_values_and_is_resumable(monkeypatch, capsys):
    old_key, new_key = _configure_keys(monkeypatch)
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", old_key)
    old_ciphertext = encrypt_api_key("old-secret")
    current_ciphertext = None
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", new_key)
    current_ciphertext = encrypt_api_key("current-secret")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY_PREVIOUS", old_key)
    old_source = SimpleNamespace(api_key=old_ciphertext)
    current_source = SimpleNamespace(api_key=current_ciphertext)
    legacy_source = SimpleNamespace(api_key="legacy-secret")
    database = _Database([old_source, current_source, legacy_source])
    monkeypatch.setattr(rotate_source_keys, "SessionLocal", lambda: database)
    monkeypatch.setattr("sys.argv", ["rotate_source_keys.py", "--apply"])

    rotate_source_keys.main()

    assert decrypt_api_key(old_source.api_key) == "old-secret"
    assert decrypt_api_key(current_source.api_key) == "current-secret"
    assert decrypt_api_key(legacy_source.api_key) == "legacy-secret"
    assert old_source.api_key.startswith(ENCRYPTED_PREFIX)
    assert old_source.api_key != old_ciphertext
    assert current_source.api_key == current_ciphertext
    assert "Credenciales actualizadas: 2" in capsys.readouterr().out
    assert database.commits == 1
    assert database.rollbacks == 0
    assert database.closed


def test_rotation_with_wrong_previous_key_does_not_mutate_and_rolls_back(monkeypatch):
    old_key, new_key = _configure_keys(monkeypatch)
    ciphertext_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", ciphertext_key)
    ciphertext = encrypt_api_key("secret-encrypted-with-an-unknown-key")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", new_key)
    monkeypatch.setattr(settings, "ENCRYPTION_KEY_PREVIOUS", old_key)
    monkeypatch.setenv("ENCRYPTION_KEY_OLD", Fernet.generate_key().decode("ascii"))
    source = SimpleNamespace(api_key=ciphertext)
    database = _Database([source])
    monkeypatch.setattr(rotate_source_keys, "SessionLocal", lambda: database)
    monkeypatch.setattr("sys.argv", ["rotate_source_keys.py", "--apply"])

    try:
        rotate_source_keys.main()
    except RuntimeError as exc:
        assert "No fue posible descifrar" in str(exc)
    else:
        raise AssertionError("expected invalid ciphertext to abort rotation")

    assert source.api_key == ciphertext
    assert database.commits == 0
    assert database.rollbacks == 1
    assert database.closed


def test_decrypt_accepts_ciphertexts_from_previous_key(monkeypatch):
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", old_key)
    ciphertext = encrypt_api_key("overlap-secret")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", new_key)
    monkeypatch.setattr(settings, "ENCRYPTION_KEY_PREVIOUS", old_key)

    assert decrypt_api_key(ciphertext) == "overlap-secret"
