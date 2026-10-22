from copy import deepcopy

import pytest

from modules.transformacion.domain.reprocessing_checkpoint import validate_checkpoint


def checkpoint():
    return {"version_checkpoint": 1, "background_job_id": 73, "forzar_reproceso": True,
            "max_raw_secop_id": 2500, "ultimo_raw_secop_id": 1000,
            "total_candidatos": 2500, "total_evaluados": 1000,
            "fecha_referencia_anomalias": "2026-10-04",
            "candidatos_verificados_en": "2026-10-04T23:00:00+00:00"}


def validate(universe, **kwargs):
    return validate_checkpoint(universe, job_id=73, rule_version="v1.0",
                              stored_rule_version=kwargs.get("version", "v1.0"),
                              counters={"total_evaluados": 1000, "procesados": 700,
                                        "omitidos": 300, "anomalias_registradas": 900})


def test_checkpoint_is_validated_without_database_dependencies():
    assert validate(checkpoint()) is True
    assert validate({}) is False


@pytest.mark.parametrize("field,value", [
    ("version_checkpoint", 2), ("version_checkpoint", True),
    ("background_job_id", 74), ("forzar_reproceso", False),
    ("ultimo_raw_secop_id", 2501), ("ultimo_raw_secop_id", -1),
    ("total_evaluados", 1001), ("total_candidatos", 999),
    ("max_raw_secop_id", True), ("fecha_referencia_anomalias", "2026-02-30"),
    ("candidatos_verificados_en", None),
])
def test_incompatible_checkpoint_cannot_silently_skip_rows(field, value):
    universe = deepcopy(checkpoint())
    universe[field] = value
    with pytest.raises(ValueError):
        validate(universe)


def test_checkpoint_cannot_resume_under_different_rules():
    with pytest.raises(ValueError):
        validate(checkpoint(), version="v2.0")
