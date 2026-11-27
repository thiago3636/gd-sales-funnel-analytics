"""
Gerador de dados 100% sintéticos para um funil comercial de Geração Distribuída (GD).

Nenhum dado real é utilizado. A empresa "Helios GD" é fictícia e todas as
distribuições foram arbitradas apenas para produzir um cenário plausível.
Falhas de qualidade são injetadas de propósito para exercitar os testes de controle.

Uso:
    python data/generate_synthetic.py --n 5000 --seed 42
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

STAGES = ["Novo", "Qualificação", "Proposta", "Análise de Crédito", "Contrato", "Ganho"]

CHANNELS = {
    # canal: (peso, multiplicador de avanço no funil)
    "Inbound": (0.30, 1.00),
    "Parceiro": (0.35, 1.10),
    "Indicação": (0.15, 1.25),
    "Outbound": (0.20, 0.85),
}

UTILITIES = ["CEMIG", "CPFL Paulista", "Enel SP", "Light", "Coelba", "Copel", "Celesc", "RGE"]

SEGMENTS = {
    # segmento: (peso, média log kWh, desvio log kWh)
    "Residencial": (0.60, np.log(450), 0.45),
    "Comercial": (0.30, np.log(2500), 0.60),
    "Industrial": (0.10, np.log(15000), 0.70),
}

# probabilidade base de avançar de STAGES[i] para STAGES[i+1]
BASE_ADVANCE = [0.78, 0.62, 0.70, 0.80, 0.88]

LOSS_REASONS = {
    "Novo": ["Sem retorno do lead", "Fora da área de concessão"],
    "Qualificação": ["Consumo abaixo do mínimo", "Sem interesse", "Sem retorno do lead"],
    "Proposta": ["Desconto insuficiente", "Optou por concorrente", "Sem interesse"],
    "Análise de Crédito": ["Crédito reprovado"],
    "Contrato": ["Desistiu antes da assinatura", "Divergência contratual"],
}


def generate(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    channels = list(CHANNELS)
    channel = rng.choice(channels, n, p=[CHANNELS[c][0] for c in channels])
    segs = list(SEGMENTS)
    segment = rng.choice(segs, n, p=[SEGMENTS[s][0] for s in segs])
    utility = rng.choice(UTILITIES, n, p=[0.20, 0.16, 0.15, 0.10, 0.10, 0.11, 0.09, 0.09])

    created = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 669, n), unit="D")

    kwh_declared = np.array(
        [rng.lognormal(SEGMENTS[s][1], SEGMENTS[s][2]) for s in segment]
    ).round(0)
    kwh_calculated = (kwh_declared * rng.normal(1.0, 0.08, n)).round(0)

    discount = rng.choice([10, 12, 15, 18, 20, 25], n, p=[0.10, 0.20, 0.30, 0.20, 0.15, 0.05])
    loyalty = rng.choice([0, 12, 24, 36], n, p=[0.15, 0.40, 0.30, 0.15])

    stage, status, loss_reason, credit_status, closed = [], [], [], [], []
    today = pd.Timestamp("2026-11-01")

    for i in range(n):
        mult = CHANNELS[channel[i]][1]
        # desconto maior ajuda a avançar da proposta
        disc_boost = 1 + (discount[i] - 15) / 100
        age_days = (today - created[i]).days
        idx = 0
        lost = False
        while idx < len(STAGES) - 1:
            p = min(BASE_ADVANCE[idx] * mult * (disc_boost if idx == 2 else 1), 0.97)
            if rng.random() < p:
                idx += 1
            else:
                lost = True
                break

        cur = STAGES[idx]
        credit = None
        if idx >= 4:
            credit = "Aprovado"
        elif idx == 3:
            credit = "Reprovado" if lost else "Pendente"

        # deals recentes ainda podem estar em andamento
        if idx == len(STAGES) - 1:
            st = "Ganho"
        elif lost and age_days > 20:
            st = "Perdido"
        else:
            st = "Em andamento"
            if credit == "Reprovado":
                credit = "Pendente"

        reason = rng.choice(LOSS_REASONS[cur]) if st == "Perdido" else None
        cycle = int(rng.gamma(2.2, 9) + idx * 4)
        close_dt = created[i] + pd.Timedelta(days=cycle) if st != "Em andamento" else pd.NaT
        if pd.notna(close_dt) and close_dt > today:
            if st == "Ganho":
                close_dt = today
            else:
                close_dt, st, reason = pd.NaT, "Em andamento", None

        stage.append(cur)
        status.append(st)
        loss_reason.append(reason)
        credit_status.append(credit)
        closed.append(close_dt)

    df = pd.DataFrame(
        {
            "deal_id": [f"D{100000 + i}" for i in range(n)],
            "cliente_id": [f"C{rng.integers(10000, 99999)}" for _ in range(n)],
            "canal": channel,
            "segmento": segment,
            "distribuidora": utility,
            "etapa": stage,
            "status": status,
            "status_credito": credit_status,
            "kwh_declarado": kwh_declared,
            "kwh_calculado": kwh_calculated,
            "desconto_pct": discount,
            "fidelidade_meses": loyalty,
            "motivo_perda": loss_reason,
            "criado_em": created,
            "fechado_em": closed,
        }
    )
    df["contrato_assinado"] = np.where(df["status"] == "Ganho", "Sim", "Não")

    return _inject_quality_issues(df, rng)


def _inject_quality_issues(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Injeta falhas controladas para que os testes de qualidade tenham o que detectar."""
    n = len(df)
    pick = lambda frac: rng.choice(df.index, int(n * frac), replace=False)  # noqa: E731

    df.loc[pick(0.020), "distribuidora"] = None                     # campo obrigatório vazio
    df.loc[pick(0.015), "kwh_calculado"] = None                     # cálculo não realizado
    idx = pick(0.030)
    df.loc[idx, "kwh_calculado"] = (df.loc[idx, "kwh_declarado"] * 1.6).round(0)  # divergência
    won = df.index[df["status"] == "Ganho"]
    df.loc[rng.choice(won, int(len(won) * 0.02), replace=False), "contrato_assinado"] = "Não"
    closed = df.index[df["fechado_em"].notna()]
    bad = rng.choice(closed, int(len(closed) * 0.005), replace=False)
    df.loc[bad, "fechado_em"] = df.loc[bad, "criado_em"] - pd.Timedelta(days=3)
    lost = df.index[df["status"] == "Perdido"]
    df.loc[rng.choice(lost, int(len(lost) * 0.03), replace=False), "motivo_perda"] = None

    adv = df.index[df["etapa"].isin(["Contrato", "Ganho"])]
    df.loc[rng.choice(adv, int(len(adv) * 0.01), replace=False), "status_credito"] = "Pendente"

    dups = df.sample(int(n * 0.01), random_state=7).copy()           # duplicidades
    return pd.concat([df, dups], ignore_index=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).parent / "synthetic_deals.csv"))
    args = ap.parse_args()
    data = generate(args.n, args.seed)
    data.to_csv(args.out, index=False)
    print(f"{len(data):,} linhas geradas em {args.out}")
