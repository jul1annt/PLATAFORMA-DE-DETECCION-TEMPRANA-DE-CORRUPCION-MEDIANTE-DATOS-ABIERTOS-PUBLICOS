from sqlalchemy import text

from modules.transformacion.repository.transformacion import TransformacionRepository


def test_incremental_comparison_work_mem_is_transaction_local(postgres_test_session):
    session = postgres_test_session
    before = session.execute(text('SHOW work_mem')).scalar_one()
    repo = TransformacionRepository(session)
    # The real candidate-count path applies the transaction-local setting.
    universe = repo.obtener_universo_reprocesamiento(False)
    assert universe['total_candidatos'] == 0
    assert session.execute(text('SHOW work_mem')).scalar_one() == '32MB'
    session.rollback()
    assert session.execute(text('SHOW work_mem')).scalar_one() == before
