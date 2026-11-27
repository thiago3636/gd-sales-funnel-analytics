"""
Testes de controle de qualidade de dados (abordagem de auditoria: 100% da população).

Cada teste retorna as linhas em exceção. `run_checks` consolida o resultado
numa matriz de controles: o que foi testado, quantas exceções e a severidade.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

KWH_TOLERANCE = 0.30  # divergência aceitável entre kWh declarado e calculado


@dataclass
class Check:
    codigo: str
    descricao: str
    severidade: str  # Alta | Média | Baixa
    regra: Callable[[pd.DataFrame], pd.Series]


CHECKS = [
    Check("QD-01", "Negociação duplicada (deal_id repetido)", "Alta",
          lambda d: d["deal_id"].duplicated(keep="first")),
    Check("QD-02", "Distribuidora não informada", "Média",
          lambda d: d["distribuidora"].isna()),
    Check("QD-03", "kWh calculado ausente", "Média",
          lambda d: d["kwh_calculado"].isna()),
    Check("QD-04", f"Divergência kWh declarado × calculado > {KWH_TOLERANCE:.0%}", "Alta",
          lambda d: ((d["kwh_calculado"] - d["kwh_declarado"]).abs()
                     / d["kwh_declarado"]) > KWH_TOLERANCE),
    Check("QD-05", "Venda ganha sem contrato assinado", "Alta",
          lambda d: (d["status"] == "Ganho") & (d["contrato_assinado"] != "Sim")),
    Check("QD-06", "Data de fechamento anterior à criação", "Alta",
          lambda d: d["fechado_em"].notna() & (d["fechado_em"] < d["criado_em"])),
    Check("QD-07", "Perda sem motivo registrado", "Baixa",
          lambda d: (d["status"] == "Perdido") & d["motivo_perda"].isna()),
    Check("QD-08", "Etapa de contrato/ganho sem crédito aprovado", "Alta",
          lambda d: d["etapa"].isin(["Contrato", "Ganho"]) & (d["status_credito"] != "Aprovado")),
]


def run_checks(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in CHECKS:
        mask = c.regra(df).fillna(False)
        n = int(mask.sum())
        rows.append({
            "codigo": c.codigo,
            "teste": c.descricao,
            "severidade": c.severidade,
            "populacao": len(df),
            "excecoes": n,
            "pct": n / len(df) if len(df) else 0.0,
            "resultado": "OK" if n == 0 else "Exceção",
        })
    return pd.DataFrame(rows)


def exceptions(df: pd.DataFrame, codigo: str) -> pd.DataFrame:
    check = next(c for c in CHECKS if c.codigo == codigo)
    return df[check.regra(df).fillna(False)]
