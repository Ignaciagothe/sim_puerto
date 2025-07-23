#!/usr/bin/env python3
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

import clases_sim
#from clases_sim import simulacion, load_data


# -----------------------------------------------------------------------------
# Configuracion pagina
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ELOGIS - Simulación Puerto Panul",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------
REQUIRED_CAMIONES_COLS: List[str] = [
    "año", "turno", "min_entre_camiones", "capacidad",
]

REQUIRED_BUQUES_COLS: List[str] = [
    "tiempo_descarga", "tiempo_entre_arribos", "tiempo_de_espera",
    "total_detenciones", "total_falta_equipos", "tonelaje",
]


OPTIONAL_BUQUES_COLS: List[str] = [
    "inicio_descarga", "primera_espia"
]


GITHUB_REPO_URL = "https://github.com/Ignaciagothe/sim_puerto"  

# -----------------------------------------------------------------------------
# CSS estilo
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
    
    .github-link {
        display: inline-flex;
        align-items: center;
        color: rgba(255,255,255,0.9);
        text-decoration: none;
        font-size: 0.9rem;
        margin-top: 0.5rem;
        padding: 0.3rem 0.8rem;
        background: rgba(255,255,255,0.1);
        border-radius: 5px;
        transition: all 0.3s ease;
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
    
    .guide-section {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
    }
    
    .guide-section h3 {
        color: #1a73e8;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


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
    """Generar resumen ejecutivo de los resultados de la simulación"""
    report = f"""
================================================================================
                 REPORTE DE SIMULACIÓN - PUERTO PANUL
                          ELOGIS - Consultoría Logística
================================================================================

Fecha de generación: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

Parámetros de Simulación:
------------------------
• Años simulados: {params.get('años', 'N/A')}
• Semilla aleatoria: {params.get('semilla', 'N/A')}
• Camiones dedicados: {params.get('camiones_dedicados', 0)}
• Capacidad camiones dedicados: {params.get('capacidad_dedicados', 0)} toneladas
• Grano inicial en bodega: {params.get('grano_inicial', 0)} toneladas
• Probabilidad uso bodega: {params.get('prob_bodega', 0):.2%}
• Buques iniciales en cola: {params.get('buques_inicial', 0)}

Tiempos Operacionales (minutos):
--------------------------------
• Tiempo puerta entrada: {params.get('tiempo_puerta_entrada', 'N/A')}
• Tiempo puerta salida: {params.get('tiempo_puerta_salida', 'N/A')}
• Tiempo cargar en chute: {params.get('tiempo_cargar_chute', 'N/A')}
• Tiempo atraque: {params.get('tiempo_atraque', 'N/A')}
• Tiempo llegada camiones: {params.get('tiempo_llegada_camiones', 'N/A')}

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
              Consultoría en Data Sceince y Logística 
================================================================================
"""
    
    return report

def calculate_real_data_statistics(buq_df: pd.DataFrame) -> dict:
    """Calculate statistics from real ship data."""
    stats = {}
    if 'tiempo_de_espera' in buq_df.columns:
        stats['waiting_time_hours'] = buq_df['tiempo_de_espera'].dropna()
        stats['waiting_time_days'] = stats['waiting_time_hours'] / 24
    if 'tiempo_descarga' in buq_df.columns:
        stats['unloading_time_hours'] = buq_df['tiempo_descarga'].dropna()
        stats['unloading_time_days'] = stats['unloading_time_hours'] / 24
    return stats

# -----------------------------------------------------------------------------
# Selección de pagina
# -----------------------------------------------------------------------------
page = st.sidebar.selectbox(
    "📄 Seleccionar Página",
    ["🚢 Simulación", "📖 Guía de Usuario"],
    index=0
)


# -----------------------------------------------------------------------------
# pagina 1  - Guia usuario
# -----------------------------------------------------------------------------

if page == "📖 Guía de Usuario":
    # Header
    st.title("Guía de Usuario")
    st.markdown("**Sistema de Simulación Puerto Panul** - Manual de uso")
    st.divider()
    
    # Introduction
    with st.container():
        st.subheader("Introducción")
        st.markdown("""
        El Sistema de Simulación Puerto Panul es una herramienta desarrollada por ELOGIS para 
        optimizar las operaciones portuarias mediante simulación de eventos discretos. Permite 
        analizar diferentes escenarios operacionales y evaluar el impacto de cambios en los 
        parámetros del sistema.
        """)
    
    # Quick Start Guide
    st.subheader("🚀 Inicio Rápido")
    
    col1, col2 = st.columns([1, 20])
    with col1:
        st.write("1.")
    with col2:
        st.write("**Preparación de Datos**  \nAsegúrese de tener los archivos históricos en formato CSV o Excel")
    
    col1, col2 = st.columns([1, 20])
    with col1:
        st.write("2.")
    with col2:
        st.write("**Carga de Archivos**  \nUse el panel lateral para subir sus datos")
    
    col1, col2 = st.columns([1, 20])
    with col1:
        st.write("3.")
    with col2:
        st.write("**Configuración**  \nAjuste los parámetros según su escenario")
    
    col1, col2 = st.columns([1, 20])
    with col1:
        st.write("4.")
    with col2:
        st.write("**Ejecutar**  \nPresione 'Ejecutar Simulación' y espere los resultados")
    
    col1, col2 = st.columns([1, 20])
    with col1:
        st.write("5.")
    with col2:
        st.write("**Análisis**  \nRevise los KPIs y exporte los resultados")
    
    # File Format Section
    st.subheader("📁 Formato de Archivos de Entrada")
    
    # Trucks file format
    with st.expander("**Archivo de Camiones** - Ver formato requerido", expanded=True):
        camiones_df = pd.DataFrame({
            'Columna': ['año', 'turno', 'min_entre_camiones', 'capacidad'],
            'Descripción': [
                'Año del registro', 
                'Turno de trabajo (1, 2 o 3)', 
                'Minutos entre llegadas', 
                'Capacidad del camión (toneladas)'
            ],
            'Tipo': ['Entero', 'Entero', 'Decimal', 'Decimal'],
        })
        st.dataframe(camiones_df, use_container_width=True, hide_index=True)
    
    # Ships file format
    with st.expander("**Archivo de Buques** - Ver formato requerido", expanded=True):
        buques_df = pd.DataFrame({
            'Columna': [
                'tiempo_descarga', 
                'tiempo_entre_arribos', 
                'tiempo_de_espera', 
                'total_detenciones', 
                'total_falta_equipos', 
                'tonelaje'
            ],
            'Descripción': [
                'Horas de descarga', 
                'Horas entre arribos', 
                'Horas de espera', 
                'Horas de detenciones', 
                'Horas sin equipos', 
                'Tonelaje del buque'
            ],
            'Tipo': ['Decimal', 'Decimal', 'Decimal', 'Decimal', 'Decimal', 'Entero'],
        })
        st.dataframe(buques_df, use_container_width=True, hide_index=True)
    
    # Simulation Parameters
    st.subheader("⚙️ Parámetros de Simulación")
    
    # Using tabs for better organization
    tab1, tab2, tab3 = st.tabs(["Generales", "Camiones Dedicados", "Tiempos Operacionales"])
    
    with tab1:
        st.markdown("""
        - **Años a simular:** Duración de la simulación (1-10 años)
        - **Semilla aleatoria:** Para reproducibilidad de resultados
        - **Buques en cola inicial:** Cantidad al inicio de la simulación
        """)
    
    with tab2:
        st.markdown("""
        - **Número de camiones:** Exclusivos para bodega (0-20)
        - **Capacidad:** Tonelaje de cada camión dedicado
        - **Grano inicial:** Inventario inicial en bodega (toneladas)
        - **Probabilidad bodega:** Que un camión vaya a bodega (0-100%)
        """)
    
    with tab3:
        st.markdown("""
        Todos los tiempos se configuran en **minutos**:
        - **Tiempos de puerta:** Entrada y salida del puerto
        - **Tiempos de bodega:** Carga, descarga y tránsito
        - **Tiempos de buques:** Atraque y espera de camiones
        """)
    
    # Important Notes
    st.subheader("💡 Recomendaciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Para mejores resultados:**
        - Use datos de al menos 1 año
        - Valide tiempos con datos reales
        - Ajuste probabilidades según patrones históricos
        """)
    
    with col2:
        st.warning("""
        **Importante:**
        - Los nombres de columnas deben coincidir exactamente
        - La simulación puede tomar varios segundos
        - Exporte resultados para análisis posteriores
        """)
    
    # Footer
    st.divider()
    st.caption("Sistema de Simulación Puerto Panul - Desarrollado por ELOGIS")
    

# -----------------------------------------------------------------------------
# Pagina Simulacion
# -----------------------------------------------------------------------------
else:
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    
    st.markdown(f"""
    <div class="company-header">
        <h1> Puerto Panul - Sistema de Simulación Logística</h1>
        <p>Desarrollado por <strong>ELOGIS</strong> - Consultoría en Logística y Optimización</p>
        <a href="{GITHUB_REPO_URL}" class="github-link">
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" style="margin-right: 5px;">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
            </svg>
            Repositorio GitHub
        </a>
    </div>
    """, unsafe_allow_html=True)


    st.markdown("## Interfaz de análisis y optimización de operaciones portuarias")

    # -----------------------------------------------------------------------------
    # Barra lateral - Subir Datos y parametros
    # -----------------------------------------------------------------------------
    with st.sidebar:
        
        st.header("📁 1. Carga de Datos Históricos")
        
        # subir archivos
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
        
        # Validar datos
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
                else:
                    st.error(f"❌ Faltan columnas en buques: {', '.join(missing)}")
                    data_valid = False
        
        st.divider()
        
    
        st.header("⚙️ 2. Parámetros de Simulación")
        
        col1, col2 = st.columns(2)
        with col1:
            años = st.number_input(
                "Años a simular",
                min_value=1,
                max_value=10,
                value=3,
                help="Duración de la simulación"
            )
            
            semilla = st.number_input(
                "Semilla aleatoria",
                min_value=0,
                max_value=99999,
                value=42,
                help="Para reproducibilidad"
            )
        
        with col2:
            buques_init = st.number_input(
                "Buques en cola inicial",
                min_value=0,
                max_value=20,
                value=7,
                help="Cantidad inicial en rada"
            )
        
        st.divider()
        
        st.subheader("🚛 Configuración de Camiones Dedicados")
        
        col1, col2 = st.columns(2)
        with col1:
            cam_dedic = st.number_input(
                "Número de camiones dedicados",
                min_value=0,
                max_value=20,
                value=0,
                help="Camiones exclusivos para bodega"
            )
            
            cap_cam_dedic = st.number_input(
                "Capacidad (ton)",
                min_value=10,
                max_value=100,
                value=30,
                help="Capacidad de cada camión dedicado",
                disabled=(cam_dedic == 0)
            )
        
        with col2:
            grano_ini = st.number_input(
                "Grano inicial en bodega (ton)",
                min_value=0,
                max_value=10000,
                value=0,
                step=100,
                help="Inventario inicial",
                disabled=(cam_dedic == 0)
            )
            
            prob_bodega = st.slider(
                "Probabilidad bodega (%)",
                min_value=0,
                max_value=100,
                value=0,
                help="Probabilidad de ir a bodega",
                disabled=(cam_dedic == 0)
            ) / 100.0
        
        with st.expander("⏱️ Tiempos Operacionales", expanded=True):
            st.markdown("**Tiempos de Camiones (minutos)**")
            col1, col2 = st.columns(2)
            
            with col1:
                tiempo_puerta_entrada = st.number_input(
                    "Tiempo puerta entrada",
                    min_value=1.0,
                    max_value=10.0,
                    value=2.0,
                    step=0.5,
                    help="Tiempo para entrar al puerto"
                )
                
                tiempo_puerta_salida = st.number_input(
                    "Tiempo puerta salida",
                    min_value=1.0,
                    max_value=20.0,
                    value=8.0,
                    step=0.5,
                    help="Tiempo para salir del puerto"
                )
                
                tiempo_cargar_chute = st.number_input(
                    "Tiempo cargar en chute",
                    min_value=1.0,
                    max_value=20.0,
                    value=7.0,
                    step=0.5,
                    help="Tiempo de carga en chute"
                )
            
            with col2:
                tiempo_a_bodega = st.number_input(
                    "Tiempo a bodega",
                    min_value=1.0,
                    max_value=10.0,
                    value=3.0,
                    step=0.5,
                    help="Tiempo para llegar a bodega"
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
                
                if tiempo_llegada_camiones >= tiempo_atraque:
                    st.warning("⚠️ El tiempo de llegada de camiones debe ser menor al tiempo de atraque")
            
                max_rada = st.number_input(
                    "Máximo buques en rada",
                    min_value=1,
                    max_value=20,
                    value=8,
                    help="Capacidad máxima de la rada"
                )
        
        # Boton simulacion
        st.divider()
        # col1 = st.columns(1)
        # with col1:
        sim_button = st.button(
            "▶️ Ejecutar Simulación",
            disabled=not (data_valid),
            use_container_width=True,
            type="primary"
        )
        # with col2:
        #     if st.button(
        #         "🔄 Valores por Defecto",
        #         use_container_width=True,
        #         help="Restaurar todos los parámetros a sus valores por defecto y limpiar resultados"
        #     ):
        #         # Clear session state
        #         if 'simulation_results' in st.session_state:
        #             del st.session_state.simulation_results
        #         st.rerun()

    # -----------------------------------------------------------------------------
    #  Contenido principal
    # -----------------------------------------------------------------------------

   
    if sim_button and data_valid:
        
        # if 'simulation_results' in st.session_state:
        #     del st.session_state.simulation_results
        
        with st.spinner("🔄 Ejecutando simulación..."):
            start_time = time.time()
            progress_bar = st.progress(0, text="Inicializando simulación...")

            try:
                progress_bar.progress(20, text="Cargando datos históricos...")
                time.sleep(0.5)
                clases_sim.load_data(cam_df, buq_df)
                progress_bar.progress(40, text="Configurando parámetros...")
                time.sleep(0.5)
                progress_bar.progress(60, text="Ejecutando simulación...")
                time_params = {
                    'TIEMPO_PUERTA_ENTRADA': tiempo_puerta_entrada,
                    'TIEMPO_PUERTA_SALIDA': tiempo_puerta_salida,
                    'TIEMPO_ENTRADA_CAMION_DEDICADO': tiempo_puerta_entrada,
                    'TIEMPO_CARGAR_EN_CHUTE': tiempo_cargar_chute,
                    'TIEMPO_A_BODEGA': tiempo_a_bodega,
                    'TIEMPO_DESCARGAR_EN_BODEGA': tiempo_descargar_bodega,
                    'TIEMPO_CARGAR_EN_BODEGA': tiempo_cargar_bodega,
                    'TIEMPO_SALIDA_DE_BODEGA': tiempo_salida_bodega,
                    'TIEMPO_ATRAQUE': tiempo_atraque,
                    'TIEMPO_LLEGADA_CAMIONES': tiempo_llegada_camiones,
                    'TASA_LLEGADA_FACTOR': 1.08,
                    'MAXIMO_RADA': int(max_rada)
                }
                
                # Definicion de los parametros en el script clases_sim module
                for param, value in time_params.items():
                    setattr(clases_sim, param, value)
                
                if cam_dedic > 0:
                    df_buques, df_cola, df_bodega = clases_sim.simulacion(
                        años=años,
                        camiones_dedicados=cam_dedic,
                        grano=grano_ini,
                        cap=cap_cam_dedic,
                        prob=prob_bodega,
                        buques_inicio_cola=buques_init,
                        seed=int(semilla)
                    )
                else:
                    results = clases_sim.simulacion(
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
                
               
                execution_time = time.time() - start_time
           
                real_data_stats = calculate_real_data_statistics(buq_df)
                
                # Guardar resultados de la sesion
                st.session_state.simulation_results = {
                    'df_buques': df_buques,
                    'df_cola': df_cola,
                    'df_bodega': df_bodega,
                    'real_data_stats': real_data_stats,
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
                    st.success("✅ Simulación completada - Resultados disponibles")
                with col2:
                    st.info(f"⏱️ Tiempo: {execution_time:.1f} seg")
                
            except Exception as e:
                progress_bar.empty()
                st.error(f"❌ Error en la simulación: {str(e)}")
                st.exception(e)

    # Mostrar resultados 
    if st.session_state.simulation_results:
        results = st.session_state.simulation_results
        df_buques = results['df_buques']
        df_cola = results['df_cola']
        df_bodega = results['df_bodega']
        real_data_stats = results['real_data_stats']
        params = results['params']
        
       
        st.header("📊 Resultados de la Simulación")
        kpis = {
            "Buques atendidos": len(df_buques),
            "Tiempo espera promedio (días)": df_buques["Tiempo de espera (dias)"].mean(),
            "Tiempo descarga promedio (días)": df_buques["Tiempo descarga (dias)"].mean(),
            "Largo cola promedio": df_cola["Largo cola rada"].mean(),
        }
        
        if 'total buques perdidos' in df_cola.columns:
            kpis["Buques perdidos"] = df_cola["total buques perdidos"].max()
        
        cols = st.columns(len(kpis))
        for col, (label, value) in zip(cols, kpis.items()):
            with col:
                create_metric_card(label, value)
        

        if df_bodega is not None:
            st.subheader("📦 Métricas de Bodega")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Inventario final (toneladas)", f"{df_bodega['ton restante bodega'].iloc[-1]:,.0f}")
            with col2:
                st.metric("Movimientos totales", f"{len(df_bodega):,}")
            with col3:
                st.metric("Camiones a bodega", f"{params['camiones_dedicados']}")
        
        st.header("📈 Análisis")
        tab_summary, tab_charts, tab_data, tab_export = st.tabs(
            ["Resultados prinicpales", " Graficos ", " Tablas de Datos", " Exportar"]
        )
        
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
            
            st.subheader("Distribución de Tiempos")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("P50 Espera", f"{df_buques['Tiempo de espera (dias)'].quantile(0.5):.2f} días")
            with col2:
                st.metric("P90 Espera", f"{df_buques['Tiempo de espera (dias)'].quantile(0.9):.2f} días")
            with col3:
                st.metric("P95 Espera", f"{df_buques['Tiempo de espera (dias)'].quantile(0.95):.2f} días")
        
        # ventana graficos
        with tab_charts:
            
            st.subheader("Datos Reales vs Simulación")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                sns.set_style("whitegrid")
                
                # datos reales histogramas
                if 'waiting_time_days' in real_data_stats:
                    sns.histplot(data=real_data_stats['waiting_time_days'], 
                                bins=30, kde=True, color="#78de84", alpha=0.7, ax=ax1)
                    ax1.set_title('Tiempo de Espera - Datos Reales', fontsize=14, fontweight='bold')
                    ax1.set_xlabel('Días', fontsize=12)
                    ax1.set_ylabel('Frecuencia', fontsize=12)
                    ax1.grid(True, alpha=0.3, linestyle='--')
                    
              
                
                #  datos simulados histogramas
                sns.histplot(data=df_buques, x='Tiempo de espera (dias)', 
                            bins=30, kde=True, color="#4a87d6", alpha=0.7, ax=ax2)
                ax2.set_title('Tiempo de Espera - Simulación', fontsize=14, fontweight='bold')
                ax2.set_xlabel('Días', fontsize=12)
                ax2.set_ylabel('Frecuencia', fontsize=12)
                ax2.grid(True, alpha=0.3, linestyle='--')        
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                
                # datos reales histogramas
                if 'unloading_time_days' in real_data_stats:
                    sns.histplot(data=real_data_stats['unloading_time_days'], 
                                bins=30, kde=True, color="#78de84", alpha=0.7, ax=ax1)
                    ax1.set_title('Tiempo de Descarga - Datos Reales', fontsize=14, fontweight='bold')
                    ax1.set_xlabel('Días', fontsize=12)
                    ax1.set_ylabel('Frecuencia', fontsize=12)
                    ax1.grid(True, alpha=0.3, linestyle='--')
                    
                   
                # datos simulados histogramas
                sns.histplot(data=df_buques, x='Tiempo descarga (dias)', 
                            bins=30, kde=True, color="#4a87d6", alpha=0.7, ax=ax2)
                ax2.set_title('Tiempo de Descarga - Simulación', fontsize=14, fontweight='bold')
                ax2.set_xlabel('Días', fontsize=12)
                ax2.set_ylabel('Frecuencia', fontsize=12)
                ax2.grid(True, alpha=0.3, linestyle='--')
                               
                plt.tight_layout()
                st.pyplot(fig)
            
           
            
            st.divider()
            
            st.subheader("Otras Visualizaciones")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Largo de la cola en rada a lo largo del tiempo
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
                # Scatter plot de tiempo de espera vs tiempo de descarga
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
                        "text": 'Espera vs Descarga',
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
            
           
            if df_bodega is not None:
                st.subheader("📦 Moviemientos en Bodega")
                
                # Evolucion de la bodega
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
            st.subheader(" Datos de Buques")
            st.dataframe(df_buques, use_container_width=True)
            
            st.subheader("Datos de Cola")
            st.dataframe(df_cola, use_container_width=True)
            
            if df_bodega is not None:
                st.subheader("Datos de Bodega")
                st.dataframe(df_bodega, use_container_width=True)
        
        # Export Tab
        with tab_export:
            st.markdown("### 💾 Exportar Resultados")
            st.info(" Todos los archivos incluyen metadatos de la simulación y están listos para análisis posterior")
            
            st.subheader("Descargas Individuales")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                csv_buques = df_buques.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar Datos de Buques (CSV)",
                    data=csv_buques,
                    file_name=f"buques_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                csv_cola = df_cola.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar Datos de Cola (CSV)",
                    data=csv_cola,
                    file_name=f"cola_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col3:
                if df_bodega is not None:
                    csv_bodega = df_bodega.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar Datos de Bodega (CSV)",
                        data=csv_bodega,
                        file_name=f"bodega_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            # Generate and download summary report
            st.subheader("Resumen")
            report = generate_summary_report(df_buques, df_cola, df_bodega, params)
            st.download_button(
                label="📥 Descargar Reporte Completo (TXT)",
                data=report,
                file_name=f"reporte_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
            
            # Export all data as Excel
            st.subheader(" Exportar Todo a Excel")
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
            <div class="company-name"> © 2025 ELOGIS - Consultoría Logística y Data Science </div>
            <p style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.8;">
                Soluciones para optimización de operaciones y logística
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
