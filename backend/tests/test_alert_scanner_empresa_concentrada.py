from app.models.company import Company
from app.models.contract import Contract, ContractStatus
from app.models.alert import Alert, AlertType
from app.services.alert_scanner import run_alert_scan


def _seed_empresa_concentrada(db, *, n_contratos, monto_cada_uno, institution_id=1):
    comp = Company(nombre="Constructora Concentrada SRL", rnc="111111111")
    db.add(comp)
    db.commit()
    for i in range(n_contratos):
        db.add(Contract(
            numero_contrato=f"CC-{i}", company_id=comp.id, institution_id=institution_id,
            modalidad="comparacion_precios", monto_original=monto_cada_uno,
            moneda="DOP", estado=ContractStatus.ACTIVO,
        ))
    db.commit()
    return comp


def test_no_genera_alerta_si_monto_total_es_bajo(db_session):
    # 25 contratos (cruza cnt>=20) pero de RD$100K cada uno = RD$2.5M total,
    # muy por debajo del umbral de materialidad RD$20M
    _seed_empresa_concentrada(db_session, n_contratos=25, monto_cada_uno=100_000)

    nuevas = run_alert_scan(db_session)

    assert not any(a.tipo == AlertType.EMPRESA_CONCENTRADA for a in nuevas)


def test_genera_una_sola_alerta_con_monto_material(db_session):
    # 25 contratos de RD$1M = RD$25M total, cruza cnt>=20 Y monto>=20M
    _seed_empresa_concentrada(db_session, n_contratos=25, monto_cada_uno=1_000_000)

    nuevas = run_alert_scan(db_session)

    concentradas = [a for a in nuevas if a.tipo == AlertType.EMPRESA_CONCENTRADA]
    assert len(concentradas) == 1


def test_correr_dos_veces_no_duplica(db_session):
    _seed_empresa_concentrada(db_session, n_contratos=25, monto_cada_uno=1_000_000)

    run_alert_scan(db_session)
    segunda = run_alert_scan(db_session)

    assert not any(a.tipo == AlertType.EMPRESA_CONCENTRADA for a in segunda)
    assert db_session.query(Alert).filter(Alert.tipo == AlertType.EMPRESA_CONCENTRADA).count() == 1
