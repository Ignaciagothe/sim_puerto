"""
demo_data.py (revisado)
----------------------
Crea y sirve pequeños «datasets demo» válidos para la interfaz cuando el
usuario todavía no sube archivos propios.

**Corrección importante**
- Se usa `Path(__file__).parent / "demo"` y `mkdir(parents=True, …)` para
  asegurar que la carpeta se cree aun cuando no existan los directorios
  intermedios, evitando el `FileNotFoundError`.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

# --------------------------------------------------------------------- #
# Configuración de rutas                                                #
# --------------------------------------------------------------------- #
# La carpeta «demo» se ubica junto al archivo actual (demo_data.py/demo/)
_DEMO_DIR: Path = Path(__file__).parent / "demo"
_DEMO_DIR.mkdir(parents=True, exist_ok=True)  # ← crea toda la ruta si falta

_CAM_FILE = _DEMO_DIR / "camiones_demo.csv"
_BUQ_FILE = _DEMO_DIR / "buques_demo.xlsx"

# --------------------------------------------------------------------- #
# Utilidades internas                                                   #
# --------------------------------------------------------------------- #

def _sample(df: pd.DataFrame, n: int = 200) -> pd.DataFrame:
    """Devuelve una muestra aleatoria (estratificada si posible)."""
    if df.empty:
        raise ValueError("DataFrame original vacío; no se puede muestrear.")
    frac = min(1.0, n / len(df))
    return (
        df.sample(frac=frac, random_state=123, replace=False)
        .sort_index()
        .reset_index(drop=True)
    )

def _write_if_needed(df: pd.DataFrame, fp: Path) -> None:
    """Guarda el archivo sólo si aún no existe (no sobreescribe)."""
    if fp.exists():
        return  # ya existe → no lo tocamos
    fp.parent.mkdir(parents=True, exist_ok=True)
    if fp.suffix == ".csv":
        df.to_csv(fp, index=False)
    else:
        df.to_excel(fp, index=False)

# --------------------------------------------------------------------- #
# API pública                                                           #
# --------------------------------------------------------------------- #

def create_demo_sets(camiones_df: pd.DataFrame, buques_df: pd.DataFrame) -> None:
    """Genera y persiste archivos demo (una sola vez) a partir de datos reales."""
    cam_demo = _sample(camiones_df, 200).assign(
        año=lambda d: np.where(d["año"] < 2023, 2023, d["año"])
    )
    buq_demo = _sample(buques_df, 200)

    _write_if_needed(cam_demo, _CAM_FILE)
    _write_if_needed(buq_demo, _BUQ_FILE)


def load_demo_camiones() -> pd.DataFrame:
    return pd.read_csv(_CAM_FILE)


def load_demo_buques() -> pd.DataFrame:
    return pd.read_excel(_BUQ_FILE, engine="openpyxl")
