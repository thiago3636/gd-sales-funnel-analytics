"""Dashboard interativo — rode com: streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from funnel import metrics as m, quality as q  # noqa: E402

st.set_page_config(page_title="Funil Comercial GD", page_icon="☀️", layout="wide")

NAVY, AMBER = "#1B2A41", "#F5A623"


@st.cache_data
def load():
    return m.load(ROOT / "data" / "synthetic_deals.csv")


raw = load()

st.title("☀️ Funil Comercial — Geração Distribuída")
st.caption("Empresa fictícia **Helios GD** · dados 100% sintéticos")

with st.sidebar:
    st.header("Filtros")
    canais = st.multiselect("Canal", sorted(raw["canal"].unique()), default=sorted(raw["canal"].unique()))
    segs = st.multiselect("Segmento", sorted(raw["segmento"].unique()), default=sorted(raw["segmento"].unique()))
    dmin, dmax = raw["criado_em"].min().date(), raw["criado_em"].max().date()
    periodo = st.date_input("Período de criação", (dmin, dmax), min_value=dmin, max_value=dmax)

flt = raw[raw["canal"].isin(canais) & raw["segmento"].isin(segs)]
if isinstance(periodo, tuple) and len(periodo) == 2:
    flt = flt[(flt["criado_em"].dt.date >= periodo[0]) & (flt["criado_em"].dt.date <= periodo[1])]
df = m.dedupe(flt)

if df.empty:
    st.warning("Nenhuma negociação para os filtros selecionados.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Negociações", f"{len(df):,}".replace(",", "."))
k2.metric("Taxa de ganho", f"{m.win_rate(df):.1%}")
k3.metric("Ciclo mediano (dias)", f"{m.cycle_time(df).median():.0f}")
k4.metric("MWh/mês contratados", f"{df.loc[df.status == 'Ganho', 'kwh_declarado'].sum() / 1000:,.0f}".replace(",", "."))

tab1, tab2, tab3 = st.tabs(["📊 Funil", "📈 Canais e evolução", "🛡️ Qualidade de dados"])

with tab1:
    f = m.funnel(df)
    fig = px.funnel(f, x="negociacoes", y="etapa", color_discrete_sequence=[NAVY])
    st.plotly_chart(fig, width="stretch")
    lr = m.loss_reasons(df).reset_index()
    lr.columns = ["motivo", "qtd"]
    st.subheader("Motivos de perda")
    st.plotly_chart(px.bar(lr, x="qtd", y="motivo", orientation="h",
                           color_discrete_sequence=[AMBER]).update_yaxes(autorange="reversed"),
                    width="stretch")

with tab2:
    c1, c2 = st.columns(2)
    for col, by in [(c1, "canal"), (c2, "distribuidora")]:
        conv = m.conversion_by(df, by).reset_index()
        col.subheader(f"Taxa de ganho por {by}")
        col.plotly_chart(px.bar(conv, x=by, y="taxa_ganho", text_auto=".0%",
                                color_discrete_sequence=[NAVY]).update_yaxes(tickformat=".0%"),
                         width="stretch")
    mo = m.monthly(df).reset_index()
    st.subheader("Evolução mensal")
    st.plotly_chart(px.line(mo, x="mes", y=["criadas", "ganhas"],
                            color_discrete_sequence=["#8A94A6", AMBER]), width="stretch")

with tab3:
    st.markdown("Testes aplicados sobre **100% da população** (antes da deduplicação).")
    res = q.run_checks(flt)
    st.dataframe(res.style.format({"pct": "{:.2%}"}), width="stretch", hide_index=True)
    code = st.selectbox("Ver exceções do teste", res["codigo"])
    st.dataframe(q.exceptions(flt, code), width="stretch", hide_index=True)
