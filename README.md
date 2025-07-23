# Simulación Logística Puerto Panul

Este repositorio contiene el motor de simulación y las interfaces de Streamlit desarrolladas por **ELOGIS** para modelar el proceso de descarga de buques en Puerto Panul.

La versión en línea de la interfaz está disponible en: <https://simulacion-puertopanul.streamlit.app/>

## Instrucciones rápidas

1. Instale Python 3.10 o superior y cree un entorno virtual.
2. Instale las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecute la interfaz recomendada:
   ```bash
   streamlit run ui_puertov2.py
   ```
   *(También puede usar `ui_puerto.py` para la versión básica.)*
4. Cargue los archivos históricos de **camiones** y **buques** cuando la aplicación lo solicite.
5. Ajuste los parámetros en la barra lateral y haga clic en **Ejecutar Simulación**.

## Formato de datos

- **Camiones** (CSV/Excel) debe incluir las columnas `año`, `turno`, `min_entre_camiones` y `capacidad`.
- **Buques** (CSV/Excel) debe contener `tiempo_descarga`, `tiempo_entre_arribos`, `tiempo_de_espera`, `total_detenciones`, `total_falta_equipos` y `tonelaje`. Las columnas opcionales `inicio_descarga` y `primera_espia` mejoran la precisión.

Para un ejemplo de datos consulte `demo_data.py`.

## Resultados

Al finalizar la simulación se muestran los principales indicadores de desempeño, tablas de buques atendidos, evolución de colas y, si corresponde, movimientos de bodega. Todos los resultados pueden descargarse desde la interfaz.

## Sobre la simulación

La lógica principal (en `clases_sim.py`) utiliza **SimPy** para representar el muelle, los camiones, la bodega y la llegada de buques. El módulo `sim_puerto.py` envuelve la simulación y calcula los KPI que se muestran en la interfaz. Todos los parámetros son configurables desde la aplicación.

Para soporte o consultas diríjase al equipo de ELOGIS.
