# ui_puerto.py
import streamlit as st
import pandas as pd
from sim_puerto import run_sim

st.set_page_config(page_title="Simulación Puerto", page_icon="🚢", layout="wide")
st.title("🚢 Simulación logística de descarga (Puerto)")
st.markdown(
    "Ajusta los **parámetros** y pulsa **Simular** para evaluar cada escenario."
)

# --- 1 · Panel de entradas ------------------------------------------------
with st.sidebar:
    st.header("Parámetros del escenario")
    años = st.number_input("Años a simular", 1, 10, 3)
    cam_dedic = st.number_input("Camiones dedicados", 0, 100, 0)
    grano_ini = st.number_input("Grano inicial en bodega (t)", 0, 10_000, 0, step=100)
    cap_camion = st.number_input("Capacidad camión dedicado (t)", 10, 60, 30)
    prob_bodega = st.slider("Prob. llegada camiones externos a bodega", 0.0, 1.0, 0.10, 0.01)
    buques_iniciales = st.slider("Buques en rada al inicio", 0, 15, 7)
    semilla = st.number_input("Seed aleatoria (opcional)", 0, value=42, step=1)

    simular = st.button("▶️ Simular")

# --- 2 · Ejecución y cacheo ----------------------------------------------
@st.cache_data(show_spinner="Ejecutando simulación…", ttl=3600)
def run_cached(**kwargs):
    return run_sim(**kwargs)

if simular:
    df_buques, df_cola, df_bodega, summary = run_cached(
        años=años,
        camiones_dedicados=cam_dedic,
        grano=grano_ini,
        cap=cap_camion,
        prob=prob_bodega,
        buques_inicio_cola=buques_iniciales,
        seed=semilla,
    )

    # --- 3 · KPIs en tarjetas --------------------------------------------
    st.subheader("🔑 Indicadores clave")
    cols = st.columns(len(summary))
    for col, (k, v) in zip(cols, summary.items()):
        col.metric(k, f"{v:,.2f}")

    # --- 4 · Resultados detallados ---------------------------------------
    st.markdown("### Detalle de buques atendidos")
    st.dataframe(df_buques, height=300)

    st.markdown("### Evolución de la cola en rada")
    st.line_chart(df_cola.set_index("Dia")["Largo cola rada"])

    if df_bodega is not None:
        st.markdown("### Eventos en bodega")
        st.dataframe(df_bodega, height=300)

    # --- 5 · Descarga -----------------------------------------------------
    csv = df_buques.to_csv(index=False).encode()
    st.download_button("Descargar buques.csv", csv, "buques.csv", "text/csv")
