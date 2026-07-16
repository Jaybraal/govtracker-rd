from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.digest import build_digest


def _alert(severidad, titulo, monto=None, tipo=AlertType.CONTRATO_GRANDE):
    return Alert(tipo=tipo, severidad=severidad, titulo=titulo,
                 entidad_tipo="contrato", entidad_id=1, monto_involucrado=monto)


def test_lista_vacia_devuelve_string_vacio():
    assert build_digest([]) == ""


def test_agrupa_por_severidad_critica_primero():
    alertas = [
        _alert(AlertSeverity.MEDIA, "hallazgo medio"),
        _alert(AlertSeverity.CRITICA, "hallazgo critico"),
    ]
    texto = build_digest(alertas)

    assert texto.index("CRÍTICA") < texto.index("MEDIA")
    assert "hallazgo critico" in texto
    assert "hallazgo medio" in texto


def test_incluye_monto_formateado_cuando_existe():
    texto = build_digest([_alert(AlertSeverity.ALTA, "contrato grande", monto=150_000_000)])
    assert "RD$150,000,000" in texto


def test_trunca_a_20_por_severidad_y_avisa_cuantos_mas():
    alertas = [_alert(AlertSeverity.MEDIA, f"hallazgo {i}") for i in range(25)]
    texto = build_digest(alertas)

    assert "hallazgo 0" in texto
    assert "hallazgo 19" in texto
    assert "hallazgo 20" not in texto
    assert "y 5 más" in texto


def test_alertas_por_nombre_sin_cedula_incluyen_disclaimer():
    texto = build_digest([_alert(
        AlertSeverity.ALTA, "Posible doble cobro en nómina: Fulano de Tal",
        tipo=AlertType.NOMINA_DOBLE_COBRO,
    )])
    assert "Posible doble cobro en nómina: Fulano de Tal · sin verificar" in texto


def test_alertas_no_relacionadas_a_personas_no_incluyen_disclaimer():
    texto = build_digest([_alert(
        AlertSeverity.ALTA, "contrato grande", monto=150_000_000,
        tipo=AlertType.CONTRATO_GRANDE,
    )])
    assert "sin verificar" not in texto
