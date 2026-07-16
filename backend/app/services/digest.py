"""Formatea una lista de alertas en texto plano agrupado por severidad,
listo para enviar por Telegram o correo."""
from ..models.alert import Alert, AlertSeverity, AlertType

_ORDEN = [AlertSeverity.CRITICA, AlertSeverity.ALTA, AlertSeverity.MEDIA, AlertSeverity.BAJA]
_ETIQUETA = {
    AlertSeverity.CRITICA: "🔴 CRÍTICA",
    AlertSeverity.ALTA: "🟠 ALTA",
    AlertSeverity.MEDIA: "🟡 MEDIA",
    AlertSeverity.BAJA: "⚪ BAJA",
}
_MAX_POR_SEVERIDAD = 20

# Tipos de alerta cuya detección es una coincidencia POR NOMBRE sin cédula
# que confirme identidad (ver alert_scanner.py) — el digest imprime solo
# titulo+monto, así que sin este marcador se enviaría por Telegram/correo
# una acusación implícita a una persona real sin ninguna indicación de que
# es un match sin verificar.
_TIPOS_SIN_VERIFICAR = {AlertType.NOMINA_DOBLE_COBRO, AlertType.POSIBLE_CONFLICTO}
_DISCLAIMER = " · sin verificar"


def build_digest(alerts: list[Alert]) -> str:
    """Cadena vacía si no hay alertas — el llamador decide no enviar nada
    en ese caso (un digest de '0 hallazgos' a diario entrena a ignorarlo)."""
    if not alerts:
        return ""

    por_severidad: dict[AlertSeverity, list[Alert]] = {s: [] for s in _ORDEN}
    for a in alerts:
        por_severidad.setdefault(a.severidad, []).append(a)

    lineas = [f"Investigador GovTracker — {len(alerts)} hallazgo(s) nuevo(s)", ""]
    for severidad in _ORDEN:
        grupo = por_severidad.get(severidad, [])
        if not grupo:
            continue
        lineas.append(f"{_ETIQUETA[severidad]} ({len(grupo)})")
        for a in grupo[:_MAX_POR_SEVERIDAD]:
            monto = f" — RD${a.monto_involucrado:,.0f}" if a.monto_involucrado else ""
            disclaimer = _DISCLAIMER if a.tipo in _TIPOS_SIN_VERIFICAR else ""
            lineas.append(f"  • {a.titulo}{monto}{disclaimer}")
        if len(grupo) > _MAX_POR_SEVERIDAD:
            lineas.append(f"  … y {len(grupo) - _MAX_POR_SEVERIDAD} más")
        lineas.append("")
    return "\n".join(lineas).strip()
