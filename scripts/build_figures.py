"""Gera as figuras usadas no README (docs/img)."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from funnel import metrics as m, quality as q  # noqa: E402

IMG = ROOT / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

NAVY, AMBER, GREY, RED = "#1B2A41", "#F5A623", "#8A94A6", "#D64545"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
})

raw = m.load(ROOT / "data" / "synthetic_deals.csv")
df = m.dedupe(raw)

# 1. Funil
f = m.funnel(df)
fig, ax = plt.subplots(figsize=(9, 4.6))
bars = ax.barh(f["etapa"][::-1], f["negociacoes"][::-1], color=NAVY)
bars[0].set_color(AMBER)
for b, (_, r) in zip(bars, f[::-1].iterrows()):
    label = f"{int(r.negociacoes):,}".replace(",", ".") + f"  ({r.conv_acumulada:.0%})"
    ax.text(b.get_width() + 40, b.get_y() + b.get_height() / 2, label, va="center")
ax.set_title("Funil comercial — negociações que alcançaram cada etapa")
ax.set_xlim(0, f["negociacoes"].max() * 1.22)
ax.xaxis.set_visible(False)
ax.spines["bottom"].set_visible(False)
fig.tight_layout()
fig.savefig(IMG / "funil.png", dpi=160)

# 2. Taxa de ganho por canal
c = m.conversion_by(df, "canal").sort_values("taxa_ganho")
fig, ax = plt.subplots(figsize=(9, 3.8))
bars = ax.barh(c.index, c["taxa_ganho"], color=[GREY] * (len(c) - 1) + [AMBER])
for b, v in zip(bars, c["taxa_ganho"]):
    ax.text(v + 0.01, b.get_y() + b.get_height() / 2, f"{v:.0%}", va="center")
ax.axvline(m.win_rate(df), color=NAVY, ls="--", lw=1)
ax.text(m.win_rate(df) + 0.005, -0.62, f"média {m.win_rate(df):.0%}", color=NAVY, fontsize=9)
ax.set_title("Taxa de ganho por canal de aquisição")
ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.set_xlim(0, c["taxa_ganho"].max() * 1.2)
fig.tight_layout()
fig.savefig(IMG / "canal.png", dpi=160)

# 3. Evolução mensal
mo = m.monthly(df)
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(mo.index, mo["criadas"], color=GREY, lw=2, label="Criadas")
ax.plot(mo.index, mo["ganhas"], color=AMBER, lw=2.5, label="Ganhas")
ax.set_title("Evolução mensal de negociações")
ax.legend(frameon=False, loc="upper left")
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(IMG / "mensal.png", dpi=160)

# 4. Matriz de controles de qualidade
chk = q.run_checks(raw).sort_values("excecoes")
colors = [RED if s == "Alta" else AMBER if s == "Média" else GREY for s in chk["severidade"]]
fig, ax = plt.subplots(figsize=(9, 4.4))
bars = ax.barh(chk["codigo"] + "  " + chk["teste"], chk["excecoes"], color=colors)
for b, v in zip(bars, chk["excecoes"]):
    ax.text(v + 1.5, b.get_y() + b.get_height() / 2, str(v), va="center")
fig.suptitle("Testes de qualidade de dados — exceções por controle", x=0.02, ha="left", fontweight="bold", fontsize=13)
ax.set_xlim(0, chk["excecoes"].max() * 1.15)
from matplotlib.patches import Patch  # noqa: E402
ax.legend(handles=[Patch(color=RED, label="Alta"), Patch(color=AMBER, label="Média"),
                   Patch(color=GREY, label="Baixa")], title="Severidade",
          frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig(IMG / "qualidade.png", dpi=160)

print("Figuras geradas em", IMG)
