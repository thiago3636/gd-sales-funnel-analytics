"""Métricas do funil comercial."""
from __future__ import annotations

import pandas as pd

STAGES = ["Novo", "Qualificação", "Proposta", "Análise de Crédito", "Contrato", "Ganho"]


def load(path: str) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["criado_em", "fechado_em"])


def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset="deal_id", keep="first")


def funnel(df: pd.DataFrame) -> pd.DataFrame:
    """Quantidade de negociações que ALCANÇARAM cada etapa e conversão etapa a etapa."""
    order = {s: i for i, s in enumerate(STAGES)}
    reached = df["etapa"].map(order)
    counts = [int((reached >= i).sum()) for i in range(len(STAGES))]
    out = pd.DataFrame({"etapa": STAGES, "negociacoes": counts})
    out["conv_etapa_anterior"] = out["negociacoes"] / out["negociacoes"].shift(1)
    out["conv_acumulada"] = out["negociacoes"] / out["negociacoes"].iloc[0]
    return out


def win_rate(df: pd.DataFrame) -> float:
    """Taxa de ganho sobre negociações encerradas (ganhas + perdidas)."""
    closed = df[df["status"].isin(["Ganho", "Perdido"])]
    return float((closed["status"] == "Ganho").mean()) if len(closed) else 0.0


def conversion_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    closed = df[df["status"].isin(["Ganho", "Perdido"])]
    g = closed.groupby(col)["status"]
    out = pd.DataFrame(
        {"encerradas": g.size(), "ganhas": g.apply(lambda s: (s == "Ganho").sum())}
    )
    out["taxa_ganho"] = out["ganhas"] / out["encerradas"]
    return out.sort_values("taxa_ganho", ascending=False)


def cycle_time(df: pd.DataFrame) -> pd.Series:
    won = df[(df["status"] == "Ganho") & (df["fechado_em"] >= df["criado_em"])]
    return (won["fechado_em"] - won["criado_em"]).dt.days


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    m = df.assign(mes=df["criado_em"].dt.to_period("M").dt.to_timestamp())
    out = m.groupby("mes").agg(
        criadas=("deal_id", "count"),
        ganhas=("status", lambda s: (s == "Ganho").sum()),
        kwh_ganho=("kwh_declarado", lambda s: s[m.loc[s.index, "status"] == "Ganho"].sum()),
    )
    return out


def loss_reasons(df: pd.DataFrame) -> pd.Series:
    lost = df[df["status"] == "Perdido"]
    return lost["motivo_perda"].fillna("(não informado)").value_counts()
