from types import SimpleNamespace

from modules.ingesta.security import ENCRYPTED_PREFIX
from scripts import migrate_source_keys


class _Database:
    def __init__(self, sources):
        self.sources = sources
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

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def test_source_key_migration_dry_run_does_not_write(monkeypatch, capsys):
    sources = [
        SimpleNamespace(api_key="legacy-plaintext"),
        SimpleNamespace(api_key=f"{ENCRYPTED_PREFIX}already-encrypted"),
        SimpleNamespace(api_key=None),
    ]
    database = _Database(sources)
    monkeypatch.setattr(migrate_source_keys, "SessionLocal", lambda: database)
    monkeypatch.setattr("sys.argv", ["migrate_source_keys.py"])

    migrate_source_keys.main()

    assert "Legacy plaintext keys: 1" in capsys.readouterr().out
    assert sources[0].api_key == "legacy-plaintext"
    assert database.commits == 0
    assert database.rollbacks == 0
    assert database.closed is True


def test_source_key_migration_encrypts_only_legacy_values(monkeypatch, capsys):
    sources = [
        SimpleNamespace(api_key="legacy-plaintext"),
        SimpleNamespace(api_key=f"{ENCRYPTED_PREFIX}already-encrypted"),
    ]
    database = _Database(sources)
    monkeypatch.setattr(migrate_source_keys, "SessionLocal", lambda: database)
    monkeypatch.setattr(migrate_source_keys, "encrypt_api_key", lambda value: f"{ENCRYPTED_PREFIX}new:{value}")
    monkeypatch.setattr("sys.argv", ["migrate_source_keys.py", "--apply"])

    migrate_source_keys.main()

    assert sources[0].api_key == f"{ENCRYPTED_PREFIX}new:legacy-plaintext"
    assert sources[1].api_key == f"{ENCRYPTED_PREFIX}already-encrypted"
    assert "Encrypted keys: 1" in capsys.readouterr().out
    assert database.commits == 1
    assert database.rollbacks == 0
    assert database.closed is True
