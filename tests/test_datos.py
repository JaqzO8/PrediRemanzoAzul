import pytest
from pathlib import Path
from src.datos.repository import VisitasRepository
from src.datos.models import FiltroVisitas


@pytest.fixture
def repo():
    return VisitasRepository()


def test_carga_historico(repo):
    df = repo.dataframe
    assert not df.empty
    assert len(df) >= 1000
    assert "cantidad_visitantes" in df.columns
    assert "clima_estado" in df.columns


def test_filtro_por_clima(repo):
    filtro = FiltroVisitas(clima_estado="soleado", limit=20)
    res = repo.obtener_todos(filtro)
    assert res.total > 0
    assert len(res.registros) <= 20
    assert all(r.clima_estado == "soleado" for r in res.registros)


def test_filtro_por_fin_de_semana(repo):
    filtro = FiltroVisitas(es_fin_de_semana=True, limit=15)
    res = repo.obtener_todos(filtro)
    assert res.total > 0
    assert all(r.es_fin_de_semana is True for r in res.registros)


def test_obtener_similares(repo):
    similares = repo.obtener_similares(
        clima_estado="soleado",
        es_fin_de_semana=True,
        temperatura_c=28.0,
        probabilidad_lluvia_pct=5.0,
        limit=10,
    )
    assert len(similares) == 10
    assert all("cantidad_visitantes" in r for r in similares)
    assert all("distancia" in r for r in similares)


def test_estadisticas_historicas(repo):
    stats = repo.obtener_estadisticas()
    assert stats.total_registros >= 1000
    assert stats.promedio_visitantes > 0
    assert stats.promedio_fin_de_semana > stats.promedio_dia_semana
    assert "soleado" in stats.promedio_por_clima
