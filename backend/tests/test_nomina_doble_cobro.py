import sqlite3

from app.models.alert import Alert, AlertType
from app.services.alert_scanner import _scan_nomina_doble_cobro


def _crear_nominas_db(tmp_path):
    db_path = tmp_path / "nominas_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE empleados (
            id INTEGER PRIMARY KEY, institucion TEXT, nombre_raw TEXT,
            nombre TEXT, funcion TEXT, salario REAL, mes INTEGER, anio INTEGER, fuente TEXT
        )
    """)
    # Nombre largo (>22 chars normalizado) = confianza ALTA, cobrando en 2 instituciones el mismo mes
    conn.executemany(
        "INSERT INTO empleados (institucion, nombre_raw, nombre, funcion, salario, mes, anio, fuente) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("MINISTERIO DE SALUD", "Juan Carlos Perez Gonzalez", "JUAN CARLOS PEREZ GONZALEZ", "MEDICO", 80000, 6, 2026, "test"),
            ("MINISTERIO DE EDUCACION", "Juan Carlos Perez Gonzalez", "JUAN CARLOS PEREZ GONZALEZ", "PROFESOR", 60000, 6, 2026, "test"),
            # Nombre corto = confianza BAJA, no debe generar alerta
            ("MINISTERIO DE SALUD", "Ana Ruiz", "ANA RUIZ", "ENFERMERA", 40000, 6, 2026, "test"),
            ("MINISTERIO DE EDUCACION", "Ana Ruiz", "ANA RUIZ", "PROFESORA", 35000, 6, 2026, "test"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def test_genera_alerta_solo_para_confianza_alta(db_session, tmp_path):
    nominas_path = _crear_nominas_db(tmp_path)

    nuevas = _scan_nomina_doble_cobro(db_session, nominas_db_path=nominas_path)

    assert len(nuevas) == 1
    assert nuevas[0].tipo == AlertType.NOMINA_DOBLE_COBRO
    assert "JUAN CARLOS PEREZ GONZALEZ" in nuevas[0].titulo.upper() or "JUAN CARLOS PEREZ GONZALEZ" in nuevas[0].descripcion.upper()
    assert "sin cédula" in nuevas[0].descripcion.lower()


def test_no_falla_si_nominas_db_no_existe(db_session, tmp_path):
    ruta_inexistente = tmp_path / "no_existe.db"
    assert _scan_nomina_doble_cobro(db_session, nominas_db_path=ruta_inexistente) == []


def test_es_seguro_llamarlo_dos_veces_no_duplica(db_session, tmp_path):
    nominas_path = _crear_nominas_db(tmp_path)

    primera = _scan_nomina_doble_cobro(db_session, nominas_db_path=nominas_path)
    db_session.commit()
    segunda = _scan_nomina_doble_cobro(db_session, nominas_db_path=nominas_path)

    assert len(primera) == 1
    assert len(segunda) == 0
    assert db_session.query(Alert).filter(Alert.tipo == AlertType.NOMINA_DOBLE_COBRO).count() == 1


def test_no_falla_si_nominas_db_esta_corrupto(db_session, tmp_path):
    ruta_corrupta = tmp_path / "corrupto.db"
    ruta_corrupta.write_bytes(b"not a real sqlite file")

    assert _scan_nomina_doble_cobro(db_session, nominas_db_path=ruta_corrupta) == []
