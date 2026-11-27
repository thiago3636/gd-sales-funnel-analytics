import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "data"))

from funnel import metrics as m, quality as q  # noqa: E402
from generate_synthetic import generate  # noqa: E402


@pytest.fixture(scope="module")
def raw():
    return generate(n=1500, seed=1)


@pytest.fixture(scope="module")
def df(raw):
    return m.dedupe(raw)


def test_gerador_e_deterministico():
    a, b = generate(300, seed=9), generate(300, seed=9)
    pd.testing.assert_frame_equal(a, b)


def test_funil_e_monotonicamente_decrescente(df):
    f = m.funnel(df)
    assert f["negociacoes"].is_monotonic_decreasing
    assert f["conv_acumulada"].iloc[0] == 1.0


def test_taxa_de_ganho_entre_0_e_1(df):
    assert 0 < m.win_rate(df) < 1


def test_dedupe_remove_duplicidades(raw, df):
    assert raw["deal_id"].duplicated().any()
    assert not df["deal_id"].duplicated().any()


def test_ciclo_ignora_datas_invalidas(df):
    assert (m.cycle_time(df) >= 0).all()


def test_controles_detectam_falhas_injetadas(raw):
    res = q.run_checks(raw).set_index("codigo")
    for code in ["QD-01", "QD-02", "QD-04", "QD-05", "QD-06"]:
        assert res.loc[code, "excecoes"] > 0, code


def test_controle_passa_em_base_limpa():
    clean = pd.DataFrame({
        "deal_id": ["D1", "D2"], "distribuidora": ["CEMIG", "Copel"],
        "kwh_declarado": [500, 800], "kwh_calculado": [510, 790],
        "status": ["Ganho", "Perdido"], "contrato_assinado": ["Sim", "Não"],
        "criado_em": pd.to_datetime(["2026-01-01", "2026-01-05"]),
        "fechado_em": pd.to_datetime(["2026-02-01", "2026-01-20"]),
        "motivo_perda": [None, "Sem interesse"],
        "etapa": ["Ganho", "Proposta"], "status_credito": ["Aprovado", None],
    })
    assert (q.run_checks(clean)["excecoes"] == 0).all()
