from datetime import date, datetime
from decimal import Decimal

from modules.transformacion.services.normalization_service import detect_anomalies


def _complete_contract(**changes):
    values = {
        "entidad": "Entidad pública",
        "nombre_del_proveedor": "Proveedor",
        "valor_total_adjudicacion": Decimal("10"),
        "fecha_de_publicacion_del": date(2025, 1, 1),
        "tipo_de_contrato": "Servicios",
        "fecha_adjudicacion": date(2025, 1, 2),
        "fecha_de_ultima_publicaci": None,
        "fecha_de_apertura_efectiva": None,
        "precio_base": Decimal("12"),
    }
    return {**values, **changes}


def test_anomaly_detection_is_repeatable_and_returns_data_without_persisting():
    findings = detect_anomalies(
        _complete_contract(), raw_secop_id=9, current_date=date(2026, 9, 26)
    )

    assert findings == []
    assert detect_anomalies(
        _complete_contract(), raw_secop_id=9, current_date=date(2026, 9, 26)
    ) == findings


def test_anomaly_detection_returns_findings_for_missing_future_and_negative_values():
    findings = detect_anomalies(
        _complete_contract(
            entidad=" ",
            fecha_adjudicacion=datetime(2026, 9, 27, 12),
            precio_base=Decimal("-1"),
        ),
        raw_secop_id=17,
        current_date=date(2026, 9, 26),
    )

    assert [(item.tipo_anomalia, item.campo_afectado) for item in findings] == [
        ("CAMPO_FALTANTE", "entidad"),
        ("FECHA_FUTURA", "fecha_adjudicacion"),
        ("MONTO_NEGATIVO", "precio_base"),
    ]
    assert all(item.raw_secop_id == 17 for item in findings)
