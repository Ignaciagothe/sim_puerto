# sim_puerto.py
import pandas as pd
from functools import wraps

# sim_puerto.py  (fragmento)

from clases_sim import simulacion, load_data

def run_sim(
    años: int = 3,
    camiones_dedicados: int = 0,
    grano: int = 0,
    cap: int = 0,
    prob: float = 0.0,
    buques_inicio_cola: int = 7,
    seed: int | None = None,
    camiones_df: pd.DataFrame | None = None,
    buques_df: pd.DataFrame | None = None,
):
    # ← 1 · Carga de datos dinámica
    if camiones_df is not None and buques_df is not None:
        load_data(camiones_df, buques_df)

    """Lanza la simulación y devuelve dataframes + KPIs resumidos."""
    res = simulacion(
        años=años,
        camiones_dedicados=camiones_dedicados,
        grano=grano,
        cap=cap,
        prob=prob,
        buques_inicio_cola=buques_inicio_cola,
        seed=seed,
    )
    # despaqueta según modo
    if camiones_dedicados > 0:
        df_buques, df_cola, df_bodega = res
    else:
        df_buques, df_cola = res
        df_bodega = None

    summary = _kpis(df_buques, df_cola, df_bodega)
    return df_buques, df_cola, df_bodega, summary


# --- KPIs principales para mostrar en la UI -----------------------------
def _kpis(df_buques: pd.DataFrame, df_cola: pd.DataFrame, df_bodega: pd.DataFrame | None):
    kpi = {}
    kpi["Tiempo medio de espera (días)"] = df_buques["Tiempo de espera (dias)"].mean()
    kpi["Tiempo medio de descarga (días)"] = df_buques["Tiempo descarga (dias)"].mean()
    kpi["Camiones normales / buque"] = df_buques["Camiones normales"].mean()
    if df_bodega is not None:
        kpi["Tons restantes en bodega"] = df_bodega["ton restante bodega"].iloc[-1]
    kpi["Buques perdidos"] = df_cola["total buques perdidos"].max()
    return kpi
