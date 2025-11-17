# Guía de Ejecución de Análisis de Grafos (L-espacio y P-espacio)

Este directorio contiene los scripts para la construcción y análisis de los grafos de transporte público en L-espacio y P-espacio, siguiendo la metodología descrita en la tesis.

## Estructura del Directorio

- `l_space/`: Contiene scripts para la construcción y análisis del grafo L-espacio.
    - `construcción/`: Scripts para la construcción del grafo L-espacio.
    - `limpieza y validación/`: Scripts para la limpieza y preprocesamiento de datos GTFS.
    - `análisis/`: Scripts para el análisis del grafo L-espacio (centralidades, comunidades, etc.).
    - `run_l_space_pipeline.py`: Script principal para ejecutar la construcción completa del grafo L-espacio.
- `p_space/`: Contiene scripts para la construcción y análisis del grafo P-espacio.
    - `construcción/`: Scripts para la construcción del grafo P-espacio.
    - `análisis/`: Scripts para el análisis del grafo P-espacio (centralidades, comunidades, etc.).
    - `run_p_space_pipeline.py`: Script principal para ejecutar la construcción completa del grafo P-espacio.
- `etapas/`: Contiene scripts relacionados con las etapas del análisis.
- `Notebooks/`: Contiene notebooks Jupyter para exploración y desarrollo.

## Pre-requisitos

Asegúrate de tener el entorno de Python configurado con las librerías necesarias (pandas, networkx, scikit-learn, etc.). Se recomienda usar el entorno de Conda `Tesis`.

## Ejecución de los Pipelines

Para ejecutar la construcción de los grafos L-espacio y P-espacio, sigue los siguientes pasos:

### 1. Construcción del Grafo L-espacio

Este pipeline realiza la construcción inicial del grafo a partir de los datos GTFS y luego consolida las paradas utilizando DBSCAN.

Para ejecutarlo, abre una terminal en el directorio raíz del proyecto y ejecuta:

```bash
C:/Users/fbetancourt/AppData/Local/anaconda3/envs/Tesis/python.exe Código/l_space/run_l_space_pipeline.py
```

El grafo consolidado del L-espacio se guardará en `out/l_space/grafo_consolidado.gpickle`.

### 2. Construcción del Grafo P-espacio

Este pipeline construye el grafo P-espacio utilizando los supernodos generados por el pipeline del L-espacio.

Para ejecutarlo, asegúrate de haber ejecutado primero el pipeline del L-espacio. Luego, en la terminal, ejecuta:

```bash
C:/Users/fbetancourt/AppData/Local/anaconda3/envs/Tesis/python.exe Código/p_space/run_p_space_pipeline.py
```

El grafo P-espacio se guardará en `out/p_space/grafo_p_space_correcto.gpickle`.

## Análisis de Grafos

Una vez construidos los grafos, puedes utilizar los scripts dentro de los directorios `l_space/análisis/` y `p_space/análisis/` para realizar los cálculos de métricas (centralidades, comunidades, etc.) descritos en la tesis.

**Nota:** Actualmente, las rutas de los archivos están codificadas directamente en los scripts. El siguiente paso es parametrizar estas rutas utilizando un archivo `.env` para facilitar la configuración y portabilidad del proyecto.
