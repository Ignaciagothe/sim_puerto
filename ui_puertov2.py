#!/usr/bin/env python3
"""
Enhanced Streamlit Interface for Port Simulation
Puerto Panul - Logistics Simulation Tool
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
    from sim_puerto import run_sim
    SIMULATION_AVAILABLE = True
except ImportError:
    SIMULATION_AVAILABLE = False
    st.error("⚠️ Simulation modules not found. Please ensure clases_sim.py and sim_puerto.py are in the same directory.")

# -----------------------------------------------------------------------------
# 🔧 Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Puerto Panul - Simulación Logística",
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
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
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
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 📚 User Guide
# -----------------------------------------------------------------------------
with st.expander("📖 **Guía de Usuario** - Cómo usar esta herramienta", expanded=False):
    st.markdown("""
    ### 🚀 Inicio Rápido
    
    1. **Carga de Datos** (Panel Izquierdo)
       - Sube el archivo de **camiones** (CSV o Excel) con las columnas: `año`, `turno`, `min_entre_camiones`, `capacidad`
       - Sube el archivo de **buques** (CSV o Excel) con las columnas requeridas
       
    2. **Configuración del Escenario**
       - Ajusta los parámetros de simulación según tu escenario
       - Los valores por defecto están basados en operaciones típicas
       
    3. **Ejecutar Simulación**
       - Presiona el botón **▶️ Ejecutar Simulación**
       - Espera a que se complete el proceso
       
    4. **Análisis de Resultados**
       - Revisa los KPIs principales
       - Explora las visualizaciones en las diferentes pestañas
       - Descarga los resultados para análisis posterior
    
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
    """)

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
    """Create a simple metric card without color coding."""
    st.metric(label, f"{value:,.2f}")

def generate_summary_report(df_buques: pd.DataFrame, df_cola: pd.DataFrame, df_bodega: pd.DataFrame = None) -> str:
    """Generate a text summary report of the simulation results."""
    report = f"""
# Reporte de Simulación - Puerto Panul
**Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Resumen Ejecutivo

### Indicadores Clave
- **Buques atendidos:** {len(df_buques):,}
- **Tiempo promedio de espera:** {df_buques['Tiempo de espera (dias)'].mean():.2f} días
- **Tiempo promedio de descarga:** {df_buques['Tiempo descarga (dias)'].mean():.2f} días
- **Largo promedio de cola:** {df_cola['Largo cola rada'].mean():.2f} buques

### Estadísticas de Buques
{df_buques.describe().to_string()}

### Estadísticas de Cola
{df_cola.describe().to_string()}
"""
    
    if df_bodega is not None:
        report += f"""
### Estadísticas de Bodega
- **Toneladas finales en bodega:** {df_bodega['ton restante bodega'].iloc[-1]:,.0f}
- **Movimientos totales:** {len(df_bodega):,}
"""
    
    return report

# -----------------------------------------------------------------------------
# 🎯 Main Application
# -----------------------------------------------------------------------------
st.title("🚢 Puerto Panul - Simulación Logística de Descarga")
st.markdown("### Sistema de análisis y optimización de operaciones portuarias")

# -----------------------------------------------------------------------------
# 📁 Sidebar - Data Loading and Parameters
# -----------------------------------------------------------------------------
with st.sidebar:
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
                st.success("✅ Archivo de camiones cargado correctamente")
                with st.expander("Vista previa - Camiones"):
                    st.dataframe(cam_df.head(), use_container_width=True)
                data_valid = True
            else:
                st.error(f"❌ Faltan columnas en camiones: {', '.join(missing)}")
                data_valid = False
    
    if buq_file:
        buq_df = load_file(buq_file)
        if buq_df is not None:
            valid, missing = validate_dataframe(buq_df, REQUIRED_BUQUES_COLS, "Buques")
            if valid:
                st.success("✅ Archivo de buques cargado correctamente")
                with st.expander("Vista previa - Buques"):
                    st.dataframe(buq_df.head(), use_container_width=True)
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
    
    # Simulation button
    st.divider()
    sim_button = st.button(
        "▶️ Ejecutar Simulación",
        disabled=not (data_valid and SIMULATION_AVAILABLE),
        use_container_width=True,
        type="primary"
    )

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
if sim_button and data_valid:
    with st.spinner("🔄 Ejecutando simulación..."):
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
            
            # Store results in session state
            st.session_state.simulation_results = {
                'df_buques': df_buques,
                'df_cola': df_cola,
                'df_bodega': df_bodega,
                'params': {
                    'años': años,
                    'camiones_dedicados': cam_dedic,
                    'capacidad_dedicados': cap_cam_dedic,
                    'grano_inicial': grano_ini,
                    'prob_bodega': prob_bodega,
                    'buques_inicial': buques_init,
                    'semilla': semilla
                }
            }
            
            progress_bar.progress(100, text="✅ Simulación completada")
            time.sleep(0.5)
            progress_bar.empty()
            
            st.success("✅ Simulación completada exitosamente")
            
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
    st.header("📊 Panel de Indicadores Clave (KPIs)")
    
    # Calculate KPIs
    kpis = {
        "Buques atendidos": (len(df_buques), None),
        "Tiempo espera promedio (días)": (df_buques["Tiempo de espera (dias)"].mean(), "Tiempo espera promedio (días)"),
        "Tiempo descarga promedio (días)": (df_buques["Tiempo descarga (dias)"].mean(), "Tiempo descarga promedio (días)"),
        "Largo cola promedio": (df_cola["Largo cola rada"].mean(), "Largo cola promedio"),
    }
    
    if 'total buques perdidos' in df_cola.columns:
        kpis["Buques perdidos"] = (df_cola["total buques perdidos"].max(), "Buques perdidos")
    
    # Display KPIs in columns
    cols = st.columns(len(kpis))
    for col, (label, (value, threshold_key)) in zip(cols, kpis.items()):
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
            camiones_bodega_count = len(df_bodega[df_bodega['actividad camion '] == 'cargar en bodega']) if 'actividad camion ' in df_bodega.columns else 0
            st.metric("Camiones a bodega", f"{camiones_bodega_count}")
        # with col3:
            
        #     st.metric("Camiones a bodega", f"{params['camiones_dedicados']}")
    
    # Tabs for detailed analysis
    st.header("📈 Análisis Detallado")
    tab_summary, tab_charts, tab_data, tab_export = st.tabs(
        ["📋 Resumen", "📊 Visualizaciones", "🗃️ Datos", "💾 Exportar"]
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
            sns.histplot(data=df_buques, x='Tiempo de espera (dias)', 
                        bins=30, kde=True, color='skyblue', ax=ax)
            ax.set_title('Distribución de Tiempo de Espera', fontsize=14, fontweight='bold')
            ax.set_xlabel('Días')
            ax.set_ylabel('Frecuencia')
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            
            # Queue length over time
            chart = alt.Chart(df_cola).mark_line(
                point=alt.OverlayMarkDef(filled=False, fill="white")
            ).encode(
                x=alt.X('Dia:Q', title='Día'),
                y=alt.Y('Largo cola rada:Q', title='Buques en cola'),
                tooltip=['Dia', 'Largo cola rada']
            ).properties(
                title='Evolución de la Cola en Rada',
                width=600,
                height=400
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
        
        with col2:
            # Unloading time distribution
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.histplot(data=df_buques, x='Tiempo descarga (dias)', 
                        bins=30, kde=True, color='lightgreen', ax=ax)
            ax.set_title('Distribución de Tiempo de Descarga', fontsize=14, fontweight='bold')
            ax.set_xlabel('Días')
            ax.set_ylabel('Frecuencia')
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            
            # Tonnage vs time scatter
            scatter = alt.Chart(df_buques).mark_circle(size=60).encode(
                x=alt.X('Tiempo de espera (dias):Q', title='Tiempo de espera (días)'),
                y=alt.Y('Tiempo descarga (dias):Q', title='Tiempo de descarga (días)'),
                size=alt.Size('Tonelaje buque:Q', title='Tonelaje'),
                color=alt.Color('Largo cola al arribo:Q', 
                               scale=alt.Scale(scheme='viridis'),
                               title='Cola al arribo'),
                tooltip=['BuqueID', 'Tonelaje buque', 'Tiempo de espera (dias)', 
                        'Tiempo descarga (dias)', 'Largo cola al arribo']
            ).properties(
                title='Relación Espera vs Descarga por Buque',
                width=600,
                height=400
            ).interactive()
            st.altair_chart(scatter, use_container_width=True)
        
        # Additional charts
        if df_bodega is not None:
            st.subheader("📦 Análisis de Bodega")
            
            # Inventory evolution
            bodega_chart = alt.Chart(df_bodega.reset_index()).mark_line(
                strokeWidth=3
            ).encode(
                x=alt.X('index:Q', title='Movimiento #'),
                y=alt.Y('ton restante bodega:Q', title='Toneladas en bodega'),
                tooltip=['index', 'ton restante bodega', 'actividad camion ']
            ).properties(
                title='Evolución del Inventario en Bodega',
                width=800,
                height=400
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
        st.subheader("💾 Descargar Resultados")
        
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
        st.subheader("📄 Reporte Resumen")
        report = generate_summary_report(df_buques, df_cola, df_bodega)
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
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>Puerto Panul - Sistema de Simulación Logística v2.0</p>
        <p>Desarrollado para optimización de operaciones portuarias</p>
    </div>
    """,
    unsafe_allow_html=True
)
