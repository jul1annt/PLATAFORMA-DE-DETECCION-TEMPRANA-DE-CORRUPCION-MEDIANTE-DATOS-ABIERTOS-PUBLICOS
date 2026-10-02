from types import SimpleNamespace

import pytest

from scripts import reconcile_transformation as command


def test_checkpoint_round_trip_and_database_guard(tmp_path, monkeypatch):
    path = tmp_path / "reconcile.json"
    monkeypatch.setattr(command, "_database_identity", lambda: {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
    })
    checkpoint = {
        "checkpoint_version": command.CHECKPOINT_VERSION,
        "database": command._database_identity(),
        "version_reglas": command.VERSION_REGLAS,
        "status": "RUNNING",
    }

    command._write_checkpoint(path, checkpoint)

    assert command._read_checkpoint(path) == checkpoint
    monkeypatch.setattr(command, "_database_identity", lambda: {
        "host": "localhost",
        "port": 5432,
        "database": "other_db",
    })
    with pytest.raises(ValueError, match="otra base de datos"):
        command._read_checkpoint(path)


def test_diagnostic_mode_does_not_create_or_overwrite_checkpoint(tmp_path):
    checkpoint = tmp_path / "already-there.json"
    checkpoint.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="checkpoint ya existe"):
        command.reconcile(
            apply=True,
            batch_size=10,
            checkpoint_path=checkpoint,
            resume=False,
        )


def test_reconciliation_signatures_compare_legacy_type_fallback():
    expected = SimpleNamespace(
        motivo="CAMPO_FALTANTE",
        valor_detectado=None,
        tipo_anomalia="CAMPO_FALTANTE",
        valor_original=None,
        descripcion="Falta entidad",
        campo_afectado="entidad",
    )
    legacy_row = SimpleNamespace(
        motivo="CAMPO_FALTANTE",
        valor_detectado=None,
        tipo_anomalia=None,
        valor_original=None,
        descripcion="Falta entidad",
        campo_afectado="entidad",
    )

    assert command._finding_signature(expected) == command._row_signature(legacy_row)
