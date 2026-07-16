from app.models.institution import Institution


def test_db_session_crea_tablas_y_persiste(db_session):
    inst = Institution(nombre="Ministerio de Prueba", siglas="MDP")
    db_session.add(inst)
    db_session.commit()
    assert db_session.query(Institution).count() == 1
