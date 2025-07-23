#!/usr/bin/env python3
"""
Enhanced Streamlit Interface for Port Simulation
Puerto Panul - Logistics Simulation Tool
Developed by ELOGIS - Consultoría Logística
Lead Consultant: Herman Gothe
"""

from __future__ import annotations

import io
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path

import altair as alt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from datetime import datetime

# Import the actual simulation modules
try:
    from clases_sim import simulacion, load_data
    import clases_sim
    from sim_puerto import run_sim
    SIMULATION_AVAILABLE = True
except ImportError:
    SIMULATION_AVAILABLE = False
    st.error("⚠️ Simulation modules not found. Please ensure clases_sim.py and sim_puerto.py are in the same directory.")

# -----------------------------------------------------------------------------
# 🔧 Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ELOGIS - Simulación Puerto Panul",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 📄 Constants
# -----------------------------------------------------------------------------
REQUIRED_CAMIONES_COLS: List[str] = [
    "año", "turno", "min_entre_camiones", "capacidad",
]

REQUIRED_BUQUES_COLS: List[str] = [
    "tiempo_descarga", "tiempo_entre_arribos", "tiempo_de_espera",
    "total_detenciones", "total_falta_equipos", "tonelaje",
]

# Additional optional columns for buques
OPTIONAL_BUQUES_COLS: List[str] = [
    "inicio_descarga", "primera_espia"
]



# -----------------------------------------------------------------------------
# 🎨 Custom CSS
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Professional Corporate Styling */
    .main {
        background-color: #fafafa;
    }
    
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border: 1px solid #e0e0e0;
    }
    
    .stMetric label {
        color: #2c3e50;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .stMetric div[data-testid="metric-container"] > div[data-testid="metric-value"] {
        color: #1a73e8;
        font-weight: 700;
    }
    
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        margin: 1rem 0;
    }
    
    /* Professional headers */
    h1 {
        color: #1a1a1a;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Button styling */
    .stButton > button {
        transition: all 0.3s ease;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-weight: 600;
    }
    
    /* Company branding */
    .company-header {
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .company-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    
    .company-header p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    .professional-footer {
        background-color: #2c3e50;
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-top: 3rem;
        text-align: center;
    }
    
    .professional-footer p {
        margin: 0.3rem 0;
        color: rgba(255,255,255,0.9);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
    }
    
    /* Dataframe styling */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #1a73e8;
    }
    
    .professional-footer .company-name {
        font-size: 1.3rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 📚 User Guide
# -----------------------------------------------------------------------------
with st.expander("📖 **Guía de Usuario** - Cómo usar esta herramienta", expanded=False):
    st.markdown("""
    ### 🚀 Inicio Rápido
    
    1. **Carga de Datos** (Panel Izquierdo)
       - Sube el archivo de **camiones** (CSV o Excel)
       - Sube el archivo de **buques** (CSV o Excel)
       
    2. **Configuración del Escenario**
       - Ajusta los parámetros de simulación según tu escenario
       - Los valores por defecto están basados en operaciones típicas
       - Configura tiempos operacionales en la sección expandible "⏱️ Tiempos Operacionales"
       
    3. **Ejecutar Simulación**
       - Presiona el botón **▶️ Ejecutar Simulación**
       - Espera a que se complete el proceso
       
    4. **Análisis de Resultados**
       - Revisa los KPIs principales
       - Explora las visualizaciones en las diferentes pestañas
       - Descarga los resultados para análisis posterior
    
    ---
    
    ### 📁 Formato de Archivos de Entrada
    
    #### **Archivo de Camiones**
    El archivo debe contener las siguientes columnas (nombres exactos, sensible a mayúsculas/minúsculas):
    
    | Columna | Descripción | Tipo de Dato | Ejemplo |
    |---------|-------------|--------------|---------|
    | `año` | Año del registro | Número entero | 2023 |
    | `turno` | Turno de trabajo (1, 2 o 3) | Número entero | 1 |
    | `min_entre_camiones` | Minutos entre llegadas | Número decimal | 15.5 |
    | `capacidad` | Capacidad del camión en toneladas | Número decimal | 30.0 |
    
    **Ejemplo de formato:**
    ```
    año,turno,min_entre_camiones,capacidad
    2023,1,12.5,30
    2023,2,15.0,35
    2023,3,18.2,30
    ```
    
    #### **Archivo de Buques**
    El archivo debe contener las siguientes columnas obligatorias:
    
    | Columna | Descripción | Tipo de Dato | Ejemplo |
    |---------|-------------|--------------|---------|
    | `tiempo_descarga` | Horas de descarga | Número decimal | 48.5 |
    | `tiempo_entre_arribos` | Horas entre arribos | Número decimal | 72.0 |
    | `tiempo_de_espera` | Horas de espera | Número decimal | 24.3 |
    | `total_detenciones` | Horas de detenciones | Número decimal | 2.5 |
    | `total_falta_equipos` | Horas sin equipos | Número decimal | 1.0 |
    | `tonelaje` | Tonelaje del buque | Número entero | 35000 |
    
    **Columnas opcionales (mejoran la precisión):**
    - `inicio_descarga`: Fecha/hora de inicio (datetime)
    - `primera_espia`: Fecha/hora de primera espía (datetime)
    
    **Ejemplo de formato:**
    ```
    tiempo_descarga,tiempo_entre_arribos,tiempo_de_espera,total_detenciones,total_falta_equipos,tonelaje
    45.2,68.5,12.3,1.5,0.5,32000
    52.1,72.0,18.6,2.0,1.0,35000
    48.7,65.3,15.2,1.8,0.8,33500
    ```
    
    ---
    
    ### 📊 Interpretación de Resultados
    
    Los resultados de la simulación muestran el desempeño del puerto bajo las condiciones especificadas. Presta atención a:
    
    - **Tiempo de espera**: Menor es mejor, indica eficiencia en el atraque
    - **Tiempo de descarga**: Refleja la eficiencia operativa
    - **Largo de cola**: Indica congestión potencial
    - **Buques perdidos**: Deben minimizarse para maximizar ingresos
    
    ### 💡 Tips
    - Usa diferentes seeds para comparar múltiples escenarios
    - Los camiones dedicados ayudan cuando hay congestión
    - La probabilidad de bodega afecta el flujo de material
    - Ajusta los tiempos operacionales para simular diferentes eficiencias
    - Modifica el factor de tasa de llegada para simular diferentes demandas
    
    ### ⚠️ Notas Importantes
    - Los archivos pueden ser CSV o Excel (.xlsx, .xls)
    - Los nombres de columnas deben coincidir exactamente
    - Se recomienda datos de al menos 1 año para mejor precisión
    - Los tiempos en el archivo de buques están en **horas**
    - Los tiempos en la configuración están en **minutos**
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 🏗️ Helper Functions
# -----------------------------------------------------------------------------
@st.cache_data
def load_file(file) -> pd.DataFrame:
    """Load CSV or Excel file with proper error handling."""
    try:
        ext = Path(file.name).suffix.lower()
        if ext == '.csv':
            df = pd.read_csv(file)
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file, engine='openpyxl' if ext == '.xlsx' else 'xlrd')
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def validate_dataframe(df: pd.DataFrame, required_cols: List[str], name: str) -> Tuple[bool, List[str]]:
    """Validate that DataFrame has required columns."""
    if df is None:
        return False, []
    missing = [col for col in required_cols if col not in df.columns]
    return len(missing) == 0, missing

def create_metric_card(label: str, value: float) -> None:
    """Create a professional metric card."""
    if label == "Buques atendidos" or label == "Buques perdidos":
        st.metric(label, f"{int(value):,}")
    else:
        st.metric(label, f"{value:,.2f}")

def generate_summary_report(df_buques: pd.DataFrame, df_cola: pd.DataFrame, df_bodega: pd.DataFrame = None, params: dict = None) -> str:
    """Generate a professional text summary report of the simulation results."""
    report = f"""
================================================================================
                    ELOGIS - CONSULTORÍA LOGÍSTICA
                    Reporte de Simulación Puerto Panul
================================================================================

Fecha de generación: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Consultor: Herman Gothe
Cliente: Puerto Panul

================================================================================
PARÁMETROS DE SIMULACIÓN
================================================================================
"""
    
    if params:
        report += f"""
Configuración General:
---------------------
• Años simulados: {params.get('años', 'N/A')}
• Semilla aleatoria: {params.get('semilla', 'N/A')}
• Buques iniciales en rada: {params.get('buques_inicial', 'N/A')}

Configuración de Camiones:
-------------------------
• Camiones dedicados: {params.get('camiones_dedicados', 'N/A')}
• Capacidad camiones dedicados: {params.get('capacidad_dedicados', 'N/A')} ton
• Probabilidad envío a bodega: {params.get('prob_bodega', 'N/A'):.2%}

Configuración de Bodega:
-----------------------
• Inventario inicial: {params.get('grano_inicial', 'N/A'):,} ton
"""
    
    report += f"""
================================================================================
RESUMEN EJECUTIVO
================================================================================

Indicadores Clave de Rendimiento (KPIs):
----------------------------------------
• Buques atendidos: {len(df_buques):,}
• Tiempo promedio de espera: {df_buques['Tiempo de espera (dias)'].mean():.2f} días
• Tiempo promedio de descarga: {df_buques['Tiempo descarga (dias)'].mean():.2f} días
• Largo promedio de cola: {df_cola['Largo cola rada'].mean():.2f} buques

Estadísticas de Buques:
----------------------
{df_buques.describe().to_string()}

Estadísticas de Cola:
--------------------
{df_cola.describe().to_string()}
"""
    
    if df_bodega is not None:
        report += f"""
Estadísticas de Bodega:
----------------------
• Toneladas finales en bodega: {df_bodega['ton restante bodega'].iloc[-1]:,.0f}
• Movimientos totales: {len(df_bodega):,}
• Camiones que cargaron en bodega: {len(df_bodega[df_bodega['actividad camion '] == 'cargar en bodega']):,}
"""
    
    report += """
================================================================================
                           © 2025 ELOGIS
              Consultoría especializada en logística portuaria
================================================================================
"""
    
    return report

# -----------------------------------------------------------------------------
# 🎯 Main Application
# -----------------------------------------------------------------------------
    # Professional Company Header with session info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        <div class="company-header">
            <h1>🚢 Puerto Panul - Sistema de Simulación Logística</h1>
            <p>Desarrollado por <strong>ELOGIS</strong> - Consultoría en Logística y Optimización</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='text-align: right; padding: 1rem; color: #666;'>
            <small><strong>Sesión activa</strong></small><br>
            <small>{datetime.now().strftime("%d/%m/%Y %H:%M")}</small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("### Interfaz de análisis y optimización de operaciones portuarias")

# -----------------------------------------------------------------------------
# 📁 Sidebar - Data Loading and Parameters
# -----------------------------------------------------------------------------
with st.sidebar:
    # Company branding in sidebar
    st.markdown("""
    <div style='text-align: center; padding: 1rem; background-color: #1a73e8; color: white; border-radius: 10px; margin-bottom: 1rem;'>
        <h3 style='margin: 0; color: white;'>ELOGIS</h3>
        <p style='margin: 0; font-size: 0.9rem;'>Consultoría Logística</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.header("📁 1. Carga de Datos Históricos")
    
    # File uploaders
    cam_file = st.file_uploader(
        "Archivo de Camiones",
        type=["csv", "xlsx", "xls"],
        help="Debe contener: año, turno, min_entre_camiones, capacidad"
    )
    
    buq_file = st.file_uploader(
        "Archivo de Buques",
        type=["csv", "xlsx", "xls"],
        help="Debe contener las columnas requeridas de operación"
    )
    
    # Data validation and preview
    cam_df: Optional[pd.DataFrame] = None
    buq_df: Optional[pd.DataFrame] = None
    data_valid = False
    
    if cam_file:
        cam_df = load_file(cam_file)
        if cam_df is not None:
            valid, missing = validate_dataframe(cam_df, REQUIRED_CAMIONES_COLS, "Camiones")
            if valid:
                st.success("✅ Archivo de camiones validado correctamente")
                with st.expander("👁️ Vista previa - Camiones", expanded=False):
                    st.dataframe(cam_df.head(), use_container_width=True)
                    st.caption(f"Mostrando primeras 5 filas de {len(cam_df):,} registros totales")
                data_valid = True
            else:
                st.error(f"❌ Faltan columnas en camiones: {', '.join(missing)}")
                data_valid = False
    
    if buq_file:
        buq_df = load_file(buq_file)
        if buq_df is not None:
            valid, missing = validate_dataframe(buq_df, REQUIRED_BUQUES_COLS, "Buques")
            if valid:
                st.success("✅ Archivo de buques validado correctamente")
                with st.expander("👁️ Vista previa - Buques", expanded=False):
                    st.dataframe(buq_df.head(), use_container_width=True)
                    st.caption(f"Mostrando primeras 5 filas de {len(buq_df):,} registros totales")
                # Check for optional columns
                optional_present = [col for col in OPTIONAL_BUQUES_COLS if col in buq_df.columns]
                if optional_present:
                    st.info(f"ℹ️ Columnas opcionales detectadas: {', '.join(optional_present)}")
            else:
                st.error(f"❌ Faltan columnas en buques: {', '.join(missing)}")
                data_valid = False
    
    st.divider()
    
    # Simulation parameters
    st.header("⚙️ 2. Parámetros de Simulación")
    
    with st.expander("Configuración Temporal", expanded=True):
        años = st.number_input(
            "Años a simular",
            min_value=1,
            max_value=20,
            value=3,
            help="Horizonte temporal de la simulación"
        )
        
        semilla = st.number_input(
            "Semilla aleatoria",
            min_value=0,
            value=42,
            help="Para reproducibilidad de resultados"
        )
    
    with st.expander("Configuración de Camiones", expanded=True):
        cam_dedic = st.slider(
            "Camiones dedicados",
            min_value=0,
            max_value=100,
            value=0,
            help="Camiones exclusivos para transporte a bodega"
        )
        
        if cam_dedic > 0:
            cap_cam_dedic = st.slider(
                "Capacidad camión dedicado (t)",
                min_value=10,
                max_value=60,
                value=30,
                help="Toneladas por camión dedicado"
            )
        else:
            cap_cam_dedic = 30
    
    with st.expander("Configuración de Bodega", expanded=True):
        grano_ini = st.number_input(
            "Inventario inicial bodega (t)",
            min_value=0,
            max_value=50000,
            value=0,
            step=1000,
            help="Toneladas iniciales en bodega"
        )
        
        prob_bodega = st.slider(
            "Probabilidad envío a bodega",
            min_value=0.0,
            max_value=1.0,
            value=0.10,
            step=0.01,
            help="Probabilidad de que un camión vaya a bodega"
        )
    
    with st.expander("Estado Inicial", expanded=True):
        buques_init = st.slider(
            "Buques en rada al inicio",
            min_value=0,
            max_value=15,
            value=7,
            help="Cola inicial de buques esperando"
        )
    
    with st.expander("⏱️ Tiempos Operacionales", expanded=False):
        st.info("💡 Todos los tiempos están expresados en **minutos**")
        
        st.markdown("**Tiempos de Camiones (minutos)**")
        col1, col2 = st.columns(2)
        
        with col1:
            tiempo_puerta_entrada = st.number_input(
                "Tiempo puerta entrada",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.5,
                help="Tiempo para entrar al puerto"
            )
            
            tiempo_puerta_salida = st.number_input(
                "Tiempo puerta salida",
                min_value=0.5,
                max_value=15.0,
                value=8.16,
                step=0.5,
                help="Tiempo para salir del puerto"
            )
            
            tiempo_cargar_chute = st.number_input(
                "Tiempo cargar en chute",
                min_value=1.0,
                max_value=20.0,
                value=7.28,
                step=0.5,
                help="Tiempo de carga en el chute"
            )
        
        with col2:
            tiempo_a_bodega = st.number_input(
                "Tiempo traslado a bodega",
                min_value=1.0,
                max_value=15.0,
                value=3.0,
                step=0.5,
                help="Tiempo de viaje a bodega"
            )
            
            tiempo_descargar_bodega = st.number_input(
                "Tiempo descargar en bodega",
                min_value=1.0,
                max_value=20.0,
                value=6.0,
                step=0.5,
                help="Tiempo para descargar"
            )
            
            tiempo_cargar_bodega = st.number_input(
                "Tiempo cargar en bodega",
                min_value=1.0,
                max_value=20.0,
                value=6.0,
                step=0.5,
                help="Tiempo para cargar"
            )
            
            tiempo_salida_bodega = st.number_input(
                "Tiempo salida de bodega",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.5,
                help="Tiempo para salir de bodega"
            )
        
        st.markdown("**Tiempos de Buques (minutos)**")
        col3, col4 = st.columns(2)
        
        with col3:
            tiempo_atraque = st.number_input(
                "Tiempo de atraque",
                min_value=60,
                max_value=1000,
                value=462,
                step=30,
                help="Tiempo total de atraque"
            )
            
            tiempo_llegada_camiones = st.number_input(
                "Tiempo llegada camiones",
                min_value=60,
                max_value=800,
                value=440,
                step=30,
                help="Tiempo antes de que lleguen camiones"
            )
            
            # Validación de tiempos
            if tiempo_llegada_camiones >= tiempo_atraque:
                st.warning("⚠️ El tiempo de llegada de camiones debe ser menor al tiempo de atraque")
        
        # with col4:
        #     tasa_llegada_factor = st.number_input(
        #         "Factor tasa llegada buques",
        #         min_value=0.5,
        #         max_value=2.0,
        #         value=1.08,
        #         step=0.01,
        #         help="Factor multiplicador de llegada"
        #     )
            
            max_rada = st.number_input(
                "Máximo buques en rada",
                min_value=1,
                max_value=20,
                value=8,
                help="Capacidad máxima de la rada"
            )
    
    # Simulation button
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        sim_button = st.button(
            "▶️ Ejecutar Simulación",
            disabled=not (data_valid and SIMULATION_AVAILABLE),
            use_container_width=True,
            type="primary"
        )
    with col2:
        if st.button(
            "🔄 Valores por Defecto",
            use_container_width=True,
            help="Restaurar todos los parámetros a sus valores por defecto y limpiar resultados"
        ):
            # Clear session state
            if 'simulation_results' in st.session_state:
                del st.session_state.simulation_results
            st.rerun()


# -----------------------------------------------------------------------------
# 📊 Main Content Area
# -----------------------------------------------------------------------------
if not SIMULATION_AVAILABLE:
    st.error("⚠️ Los módulos de simulación no están disponibles. Por favor, verifica la instalación.")
    st.stop()

# Session state for results
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None

# Run simulation
# Run simulation
if sim_button and data_valid:
    # Clear previous results
    if 'simulation_results' in st.session_state:
        del st.session_state.simulation_results
    
    with st.spinner("🔄 Ejecutando simulación..."):
        start_time = time.time()
        progress_bar = st.progress(0, text="Inicializando simulación...")

        
        
        try:
            # Update progress
            progress_bar.progress(20, text="Cargando datos históricos...")
            time.sleep(0.5)
            
            # Load data into simulation
            load_data(cam_df, buq_df)
            
            progress_bar.progress(40, text="Configurando parámetros...")
            time.sleep(0.5)
            
            # Run simulation
            progress_bar.progress(60, text="Ejecutando simulación...")
            
            # Prepare time parameters dictionary
            time_params = {
                'TIEMPO_PUERTA_ENTRADA': tiempo_puerta_entrada,
                'TIEMPO_PUERTA_SALIDA': tiempo_puerta_salida,
                'TIEMPO_ENTRADA_CAMION_DEDICADO': tiempo_puerta_entrada,  # Same as regular entrance
                'TIEMPO_CARGAR_EN_CHUTE': tiempo_cargar_chute,
                'TIEMPO_A_BODEGA': tiempo_a_bodega,
                'TIEMPO_DESCARGAR_EN_BODEGA': tiempo_descargar_bodega,
                'TIEMPO_CARGAR_EN_BODEGA': tiempo_cargar_bodega,
                'TIEMPO_SALIDA_DE_BODEGA': tiempo_salida_bodega,
                'TIEMPO_ATRAQUE': tiempo_atraque,
                'TIEMPO_LLEGADA_CAMIONES': tiempo_llegada_camiones,
                'TASA_LLEGADA_FACTOR': 1.08,  # Default value, can be adjusted
                'MAXIMO_RADA': int(max_rada)
            }
            
            # Set parameters in clases_sim module
            for param, value in time_params.items():
                setattr(clases_sim, param, value)
            
            if cam_dedic > 0:
                df_buques, df_cola, df_bodega = simulacion(
                    años=años,
                    camiones_dedicados=cam_dedic,
                    grano=grano_ini,
                    cap=cap_cam_dedic,
                    prob=prob_bodega,
                    buques_inicio_cola=buques_init,
                    seed=int(semilla)
                )
            else:
                results = simulacion(
                    años=años,
                    camiones_dedicados=0,
                    grano=0,
                    cap=0,
                    prob=prob_bodega,
                    buques_inicio_cola=buques_init,
                    seed=int(semilla)
                )
                df_buques, df_cola = results
                df_bodega = None
            
            progress_bar.progress(90, text="Procesando resultados...")
            time.sleep(0.5)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Store results in session state
            st.session_state.simulation_results = {
                'df_buques': df_buques,
                'df_cola': df_cola,
                'df_bodega': df_bodega,
                'execution_time': execution_time,
                'params': {
                    'años': años,
                    'camiones_dedicados': cam_dedic,
                    'capacidad_dedicados': cap_cam_dedic,
                    'grano_inicial': grano_ini,
                    'prob_bodega': prob_bodega,
                    'buques_inicial': buques_init,
                    'semilla': semilla,
                    'tiempo_puerta_entrada': tiempo_puerta_entrada,
                    'tiempo_puerta_salida': tiempo_puerta_salida,
                    'tiempo_cargar_chute': tiempo_cargar_chute,
                    'tiempo_a_bodega': tiempo_a_bodega,
                    'tiempo_descargar_bodega': tiempo_descargar_bodega,
                    'tiempo_cargar_bodega': tiempo_cargar_bodega,
                    'tiempo_salida_bodega': tiempo_salida_bodega,
                    'tiempo_atraque': tiempo_atraque,
                    'tiempo_llegada_camiones': tiempo_llegada_camiones,
                    'tasa_llegada_factor': 1.08,
                    'max_rada': int(max_rada)
                }
            }
            
            progress_bar.progress(100, text="✅ Simulación completada")
            time.sleep(0.5)
            progress_bar.empty()
            
            st.balloons()
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success("✅ Simulación completada exitosamente - Resultados listos para análisis")
            with col2:
                st.info(f"⏱️ Tiempo: {execution_time:.1f} seg")
            
        except Exception as e:
            progress_bar.empty()
            st.error(f"❌ Error en la simulación: {str(e)}")
            st.exception(e)

# Display results
if st.session_state.simulation_results:
    results = st.session_state.simulation_results
    df_buques = results['df_buques']
    df_cola = results['df_cola']
    df_bodega = results['df_bodega']
    params = results['params']
    
    # KPI Dashboard
    st.header("📊 Panel de Control - Indicadores Clave de Desempeño")
    
    # Calculate KPIs
    kpis = {
        "Buques atendidos": len(df_buques),
        "Tiempo espera promedio (días)": df_buques["Tiempo de espera (dias)"].mean(),
        "Tiempo descarga promedio (días)": df_buques["Tiempo descarga (dias)"].mean(),
        "Largo cola promedio": df_cola["Largo cola rada"].mean(),
    }
    
    if 'total buques perdidos' in df_cola.columns:
        kpis["Buques perdidos"] = df_cola["total buques perdidos"].max()
    
    # Display KPIs in columns
    cols = st.columns(len(kpis))
    for col, (label, value) in zip(cols, kpis.items()):
        with col:
            create_metric_card(label, value)
    
    # Additional metrics
    if df_bodega is not None:
        st.subheader("📦 Métricas de Bodega")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Inventario final (t)", f"{df_bodega['ton restante bodega'].iloc[-1]:,.0f}")
        with col2:
            st.metric("Movimientos totales", f"{len(df_bodega):,}")
        with col3:
            st.metric("Camiones a bodega", f"{params['camiones_dedicados']}")
    
    # Tabs for detailed analysis
    st.header("📈 Centro de Análisis Detallado")
    tab_summary, tab_charts, tab_data, tab_export = st.tabs(
        ["📋 Resumen Estadístico", "📊 Visualizaciones Avanzadas", "🗃️ Datos Completos", "💾 Centro de Exportación"]
    )
    
    # Summary Tab
    with tab_summary:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estadísticas de Buques")
            st.dataframe(
                df_buques[['Tiempo de espera (dias)', 'Tiempo descarga (dias)', 
                          'Tonelaje buque', 'Camiones normales', 'Camiones dedicados']].describe(),
                use_container_width=True
            )
        
        with col2:
            st.subheader("Estadísticas de Cola")
            st.dataframe(
                df_cola[['Largo cola rada']].describe(),
                use_container_width=True
            )
        
        # Distribution summaries
        st.subheader("Distribución de Tiempos")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("P50 Espera", f"{df_buques['Tiempo de espera (dias)'].quantile(0.5):.2f} días")
        with col2:
            st.metric("P90 Espera", f"{df_buques['Tiempo de espera (dias)'].quantile(0.9):.2f} días")
        with col3:
            st.metric("P95 Espera", f"{df_buques['Tiempo de espera (dias)'].quantile(0.95):.2f} días")
    
    # Charts Tab
    with tab_charts:
        # Create two columns for charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Waiting time distribution
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.set_style("whitegrid")
            sns.histplot(data=df_buques, x='Tiempo de espera (dias)', 
                        bins=30, kde=True, color='#1a73e8', alpha=0.7, ax=ax)
            ax.set_title('Distribución de Tiempo de Espera', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Días', fontsize=12)
            ax.set_ylabel('Frecuencia', fontsize=12)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig)
            
            # Queue length over time
            chart = alt.Chart(df_cola).mark_line(
                strokeWidth=3,
                color='#1a73e8',
                point=alt.OverlayMarkDef(
                    filled=True, 
                    fill="#1a73e8",
                    size=80
                )
            ).encode(
                x=alt.X('Dia:Q', title='Día de Simulación'),
                y=alt.Y('Largo cola rada:Q', title='Número de Buques en Cola'),
                tooltip=[
                    alt.Tooltip('Dia:Q', title='Día'),
                    alt.Tooltip('Largo cola rada:Q', title='Buques en cola')
                ]
            ).properties(
                title={
                    "text": 'Evolución de la Cola en Rada',
                    "fontSize": 16,
                    "fontWeight": "bold"
                },
                width=600,
                height=400
            ).configure_axis(
                labelFontSize=12,
                titleFontSize=14
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
        
        with col2:
            # Unloading time distribution
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.set_style("whitegrid")
            sns.histplot(data=df_buques, x='Tiempo descarga (dias)', 
                        bins=30, kde=True, color='#34a853', alpha=0.7, ax=ax)
            ax.set_title('Distribución de Tiempo de Descarga', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Días', fontsize=12)
            ax.set_ylabel('Frecuencia', fontsize=12)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig)
            
            # Tonnage vs time scatter
            scatter = alt.Chart(df_buques).mark_circle(size=100, opacity=0.8).encode(
                x=alt.X('Tiempo de espera (dias):Q', 
                       title='Tiempo de espera (días)',
                       scale=alt.Scale(zero=False)),
                y=alt.Y('Tiempo descarga (dias):Q', 
                       title='Tiempo de descarga (días)',
                       scale=alt.Scale(zero=False)),
                size=alt.Size('Tonelaje buque:Q', 
                             title='Tonelaje',
                             scale=alt.Scale(range=[100, 400])),
                color=alt.Color('Largo cola al arribo:Q', 
                               scale=alt.Scale(scheme='viridis'),
                               title='Cola al arribo'),
                tooltip=[
                    alt.Tooltip('BuqueID:N', title='ID Buque'),
                    alt.Tooltip('Tonelaje buque:Q', title='Tonelaje', format=',.0f'),
                    alt.Tooltip('Tiempo de espera (dias):Q', title='Espera (días)', format='.2f'),
                    alt.Tooltip('Tiempo descarga (dias):Q', title='Descarga (días)', format='.2f'),
                    alt.Tooltip('Largo cola al arribo:Q', title='Cola al arribo')
                ]
            ).properties(
                title={
                    "text": 'Análisis Multivariable: Espera vs Descarga',
                    "fontSize": 16,
                    "fontWeight": "bold"
                },
                width=600,
                height=400
            ).configure_axis(
                labelFontSize=12,
                titleFontSize=14
            ).interactive()
            st.altair_chart(scatter, use_container_width=True)
        
        # Additional charts
        if df_bodega is not None:
            st.subheader("📦 Análisis de Gestión de Bodega")
            
            # Inventory evolution
            bodega_chart = alt.Chart(df_bodega.reset_index()).mark_area(
                line={'color':'#ea4335', 'strokeWidth': 3},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[
                        alt.GradientStop(color='#ea4335', offset=0),
                        alt.GradientStop(color='#fbbc04', offset=1)
                    ],
                    x1=1, x2=1, y1=1, y2=0
                ),
                opacity=0.6
            ).encode(
                x=alt.X('index:Q', title='Número de Movimiento'),
                y=alt.Y('ton restante bodega:Q', title='Toneladas en Bodega'),
                tooltip=[
                    alt.Tooltip('index:Q', title='Movimiento #'),
                    alt.Tooltip('ton restante bodega:Q', title='Toneladas', format=',.0f'),
                    alt.Tooltip('actividad camion :N', title='Actividad')
                ]
            ).properties(
                title={
                    "text": 'Evolución del Inventario en Bodega',
                    "fontSize": 16,
                    "fontWeight": "bold"
                },
                width=800,
                height=400
            ).configure_axis(
                labelFontSize=12,
                titleFontSize=14
            ).interactive()
            st.altair_chart(bodega_chart, use_container_width=True)
    
    # Data Tab
    with tab_data:
        st.subheader("🚢 Datos de Buques")
        st.dataframe(df_buques, use_container_width=True)
        
        st.subheader("📊 Datos de Cola")
        st.dataframe(df_cola, use_container_width=True)
        
        if df_bodega is not None:
            st.subheader("📦 Datos de Bodega")
            st.dataframe(df_bodega, use_container_width=True)
    
    # Export Tab
    with tab_export:
        st.markdown("### 💾 Centro de Exportación de Resultados")
        st.info("📊 Todos los archivos incluyen metadatos de la simulación y están listos para análisis posterior")
        
        st.subheader("Descargas Individuales")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export buques data
            csv_buques = df_buques.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Datos de Buques (CSV)",
                data=csv_buques,
                file_name=f"buques_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Export cola data
            csv_cola = df_cola.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Datos de Cola (CSV)",
                data=csv_cola,
                file_name=f"cola_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col3:
            # Export bodega data if available
            if df_bodega is not None:
                csv_bodega = df_bodega.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar Datos de Bodega (CSV)",
                    data=csv_bodega,
                    file_name=f"bodega_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # Generate and download summary report
        st.subheader("📄 Reporte Ejecutivo")
        # Pass params to report generation
        report = generate_summary_report(df_buques, df_cola, df_bodega, params)
        st.download_button(
            label="📥 Descargar Reporte Completo (TXT)",
            data=report,
            file_name=f"reporte_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
        
        # Export all data as Excel
        st.subheader("📊 Exportar Todo a Excel")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_buques.to_excel(writer, sheet_name='Buques', index=False)
            df_cola.to_excel(writer, sheet_name='Cola', index=False)
            if df_bodega is not None:
                df_bodega.to_excel(writer, sheet_name='Bodega', index=False)
            
            # Add parameters sheet
            params_df = pd.DataFrame([params])
            params_df.to_excel(writer, sheet_name='Parametros', index=False)
        
        excel_data = buffer.getvalue()
        st.download_button(
            label="📥 Descargar Todo en Excel",
            data=excel_data,
            file_name=f"simulacion_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="professional-footer">
        <div class="company-name"> © 2025 ELOGIS Data Science - Consultoría Logística</div>
        <p>Sistema de Simulación Puerto Panul</p>
        <p style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.8;">
            Soluciones para optimización de operaciones y logística
        </p>
    </div>
    """,
    unsafe_allow_html=True
)