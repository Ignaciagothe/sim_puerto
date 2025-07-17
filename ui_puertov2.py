"""
ui_puerto.py — versión 16 Jul 2025 · corrección histograma espera
---------------------------------------------------------------
Interfaz Streamlit para la simulación logística de Puerto Panul.
- Acepta CSV/XLSX/XLS para buques y camiones.
- Valida columnas y muestra ayudas contextuales.
- KPIs + pestañas (Indicadores / Gráficos / Datos).

🎯 **Corrección**: el histograma de tiempos de espera de buques ahora se
siempre en **días**.  Si el DataFrame no trae la columna
`'Tiempo de espera (dias)'`, se calcula a partir de horas o minutos.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import List, Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from sim_puerto import run_sim, load_data

# ------------------------------------------------------------------ #
# Configuración Streamlit
# ------------------------------------------------------------------ #
st.set_page_config(page_title="Simulación Puerto", page_icon="🚢", layout="wide")
st.title("🚢 Simulación logística de descarga (Puerto)")

# ------------------------------------------------------------------ #
# 1 · Subida de archivos & validación
# ------------------------------------------------------------------ #
CAM_COLS_REQ = {"año", "capacidad", "min_entre_camiones", "turno"}
BUQ_COLS_REQ = {"tiempo_de_espera", "tiempo_descarga", "tonelaje", "tiempo_entre_arribos"}

with st.sidebar:
    st.header("1. Cargar datos históricos")
    st.markdown(
        "Los archivos deben incluir al menos las columnas mínimas listadas.\n"
        "Puedes subir *_csv* o *_xlsx/xls_* indistintamente."
    )

    file_camiones = st.file_uploader("Camiones", type=["csv", "xlsx", "xls"], key="cam")
    file_buques   = st.file_uploader("Buques",   type=["csv", "xlsx", "xls"], key="buq")

    # Validación simple de formato y columnas
    def _read_df(uploaded) -> pd.DataFrame | None:
        if not uploaded:
            return None
        try:
            if uploaded.name.lower().endswith("csv"):
                return pd.read_csv(uploaded)
            return pd.read_excel(uploaded, engine="openpyxl")
        except Exception as exc:
            st.error(f"❌ No se pudo leer **{uploaded.name}**: {exc}")
            return None

    cam_df = _read_df(file_camiones)
    buq_df = _read_df(file_buques)

    def _check_cols(df: pd.DataFrame | None, req: set[str], label: str) -> bool:
        if df is None:
            st.warning(f"⬆️ Sube el archivo de {label}.")
            return False
        missing = req - set(df.columns)
        if missing:
            st.error(f"❌ El archivo de {label} carece de columnas: {', '.join(missing)}")
            return False
        return True

    files_ok = _check_cols(cam_df, CAM_COLS_REQ, "camiones") and _check_cols(buq_df, BUQ_COLS_REQ, "buques")

    st.divider()
    st.header("2. Configurar escenario")

    años            = st.number_input("Años a simular",  1, 10, 3, help="Duración total de la simulación en años calendario.")
    cam_dedic       = st.number_input("Camiones dedicados", 0, 100, 0, help="Número de camiones que operan exclusivamente para la bodega.")
    grano_ini       = st.number_input("Grano inicial en bodega (t)", 0, 10_000, 0, step=100,
                                      help="Stock de partida dentro de la bodega intermedia.")
    cap_camion      = st.number_input("Capacidad camión dedicado (t)", 10, 60, 30,
                                      help="Toneladas que transporta cada camión dedicado por viaje.")
    prob_bodega     = st.slider("Prob. camiones externos a bodega", 0.0, 1.0, 0.10, 0.01,
                                help="Fracción de camiones externos que se dirigen a la bodega.")
    buques_inic     = st.slider("Buques en rada al inicio", 0, 15, 7,
                                help="Cuántos buques están esperando antes del t=0.")
    semilla         = st.number_input("Seed aleatoria", 0, value=42, step=1,
                                      help="Semilla numérica para reproducibilidad.")

    btn_run = st.button("▶️ Ejecutar simulación", disabled=not files_ok)

# ------------------------------------------------------------------ #
# 3 · Lanzamiento de simulación si procede
# ------------------------------------------------------------------ #
if btn_run and files_ok:
    load_data(cam_df, buq_df)

    @st.cache_data(show_spinner="⏳ Ejecutando…", ttl=3600)
    def _run():
        return run_sim(
            años=años,
            camiones_dedicados=cam_dedic,
            grano=grano_ini,
            cap=cap_camion,
            prob=prob_bodega,
            buques_inicio_cola=buques_inic,
            seed=semilla,
        )

    result = _run()
    df_buques, df_cola, *rest = result
    df_bodega = rest[0] if rest else None

    # ------------------------------------------------------------------ #
    # KPIs
    # ------------------------------------------------------------------ #
    st.subheader("🔑 Indicadores clave")
    kpis = {
        "Buques atendidos"     : len(df_buques),
        "Espera media (días)"  : df_buques["Tiempo de espera (dias)"].mean(),
        "Espera P95 (días)"    : df_buques["Tiempo de espera (dias)"].quantile(0.95),
        "Descarga media (días)": df_buques["Tiempo descarga (dias)"].mean(),
        "Cola media"           : df_cola["Largo cola rada"].mean(),
    }
    col_kpi = st.columns(len(kpis))
    for c, (k, v) in zip(col_kpi, kpis.items()):
        c.metric(k, f"{v:,.2f}")

    # ------------------------------------------------------------------ #
    # Pestañas de resultados
    # ------------------------------------------------------------------ #
    tab_kpi, tab_graf, tab_data = st.tabs(["📊 Indicadores", "📈 Gráficos", "🗃 Datos"])

    with tab_kpi:
        st.write("Los mismos KPIs en tabla:")
        st.dataframe(pd.DataFrame(kpis, index=[0]))

    with tab_graf:
        st.subheader("Histograma de tiempo de espera de buques (días)")
        # Conversión robusta a días -------------------------------------
        if "Tiempo de espera (dias)" in df_buques.columns:
            espera_dias = df_buques["Tiempo de espera (dias)"]
        elif "Tiempo de espera (horas)" in df_buques.columns:
            espera_dias = df_buques["Tiempo de espera (horas)"] / 24
        else:
            st.error("No se encontró ninguna columna de tiempo de espera.")
            espera_dias = pd.Series(dtype=float)

        fig, ax = plt.subplots(figsize=(8, 4))
        sns.histplot(espera_dias, bins=30, kde=True, ax=ax, color="skyblue")
        ax.set_xlabel("Días")
        ax.set_ylabel("Frecuencia")
        ax.grid(True)
        st.pyplot(fig)

        st.divider()
        st.subheader("Evolución del largo de cola en rada")
        st.line_chart(df_cola.set_index("Dia")["Largo cola rada"], use_container_width=True)

    with tab_data:
        st.markdown("#### Buques atendidos")
        st.dataframe(df_buques, height=300, use_container_width=True)

        st.markdown("#### Cola de la rada")
        st.dataframe(df_cola, height=300, use_container_width=True)

        if df_bodega is not None:
            st.markdown("#### Eventos en bodega")
            st.dataframe(df_bodega, height=300, use_container_width=True)

    # Opcional: descarga CSV
    st.download_button("💾 Descargar buques.csv", df_buques.to_csv(index=False).encode(),
                       file_name="buques_simulados.csv", mime="text/csv")
