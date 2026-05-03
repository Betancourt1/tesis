# Guia de ejecucion de analisis de grafos (L-space y P-space)

Este directorio contiene los scripts para reconstruir la investigacion desde GTFS hasta metricas y robustez.

## Pre-requisitos

1. Crear entorno e instalar dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Crear `.env` desde `.env.example` y ajustar rutas.
3. Usar Python 3.10+ (validado en 3.12).

## Pipeline reproducible (un solo comando)

Desde la raiz del repo:

```bash
python "Código/run_research_pipeline.py"
```

El pipeline hace, en orden:
1. Genera `stop_times_cleaned.csv` (`claves_duplicadas.py`).
2. Valida GTFS (`preprocesamiento.py`).
3. Ejecuta construccion + analisis de `L-space`.
4. Ejecuta construccion + analisis de `P-space`.

El pipeline guarda checkpoints en `out/pipeline_state/`. Si falla en un paso avanzado, al relanzar continua desde donde se quedo.
Cada ejecucion deja un reporte JSON en `out/pipeline_state/research_last_run.json`.

## Robustez: ataques dirigidos y fallos aleatorios

Los pasos de robustez de `L-space` y `P-space` ejecutan, por defecto, dos perturbaciones:

- ataque dirigido por grado, removiendo 50 supernodos;
- fallos aleatorios reproducibles con semilla base 42.

Las repeticiones aleatorias generan un CSV largo con cada corrida, un CSV resumido por numero de nodos removidos y una figura comparativa con media y banda empirica 5%-95%.
Por costo computacional, `L-space` usa 30 repeticiones aleatorias y 128 fuentes muestreadas para la eficiencia aleatoria; `P-space` usa 10 repeticiones y 32 fuentes muestreadas para ataque dirigido y fallos aleatorios.

Para ajustar el costo computacional puedes ejecutar los scripts de robustez directamente:

```bash
python "Código/l_space/análisis/robustez/analisis_robustez.py" --random-repetitions 100 --random-efficiency-sources 128
python "Código/p_space/análisis/robustez/analisis_robustez.py" --random-repetitions 10 --random-efficiency-sources 32 --targeted-efficiency-sources 32
```

Usa `--random-efficiency-sources 0` solo si necesitas eficiencia exacta tambien en fallos aleatorios; en `L-space` puede ser muy costoso.

## Opciones utiles

- Continuar aunque falle validacion GTFS:

```bash
python "Código/run_research_pipeline.py" --continue-on-validation-fail
```

- Omitir pasos especificos:

```bash
python "Código/run_research_pipeline.py" --skip-validation --skip-clean-stop-times
```

- Exportar resultados para Gephi/QGIS al final:

```bash
python "Código/run_research_pipeline.py" --export both
```

- Forzar recalculo completo sin usar checkpoints:

```bash
python "Código/run_research_pipeline.py" --force
```

- Re-ejecutar ignorando estado guardado (sin borrar archivos):

```bash
python "Código/run_research_pipeline.py" --no-resume
```

- Validar prerequisitos y plan sin ejecutar pasos:

```bash
python "Código/run_research_pipeline.py" --dry-run
```

- Definir rutas personalizadas para checkpoints y reporte:

```bash
python "Código/run_research_pipeline.py" --state-file out/pipeline_state/custom_research.json --report-file out/pipeline_state/custom_last_run.json
```

## Sensibilidad de supuestos de modelado (Punto 3)

Para evaluar estabilidad de resultados ante cambios de umbral de consolidacion y criterio de clique en P-space:

```bash
python "Código/analisis_comparativo/sensibilidad/analisis_sensibilidad_modelado.py"
```

Opcionalmente puedes definir umbrales concretos:

```bash
python "Código/analisis_comparativo/sensibilidad/analisis_sensibilidad_modelado.py" --thresholds 75 100 125 150
```

Salidas:
- `out/sensibilidad/punto3_modelado/sensibilidad_l_space.csv`
- `out/sensibilidad/punto3_modelado/sensibilidad_p_space.csv`
- `out/sensibilidad/punto3_modelado/sensibilidad_p_route_vs_trip.csv`
- `out/sensibilidad/punto3_modelado/resumen_sensibilidad.json`

## Escenarios de intervencion topologica (Punto 4)

Para cuantificar propuestas de mejora sobre el L-space (proteccion de hubs, refuerzo periferico y recableado con bypass):

```bash
python "Código/analisis_comparativo/intervenciones/analisis_intervenciones_topologicas.py"
```

Opcional: conservar presupuesto de aristas en recableado (cada bypass agregado remueve una arista de baja criticidad):

```bash
python "Código/analisis_comparativo/intervenciones/analisis_intervenciones_topologicas.py" --preserve-edge-budget
```

Salidas:
- `out/intervenciones/punto4_topologia/intervenciones_topologicas_l_space.csv`
- `out/intervenciones/punto4_topologia/resumen_intervenciones_topologicas.json`

## Rangos de resultados e incertidumbre (Punto 5)

Para consolidar bandas de resultados a partir de los puntos 3 y 4:

```bash
python "Código/analisis_comparativo/rangos/analisis_rangos_resultados.py"
```

Salidas:
- `out/incertidumbre/punto5_rangos/rangos_resultados.csv`
- `out/incertidumbre/punto5_rangos/rangos_modelado_punto3.png`
- `out/incertidumbre/punto5_rangos/rangos_intervenciones_punto4.png`
- `out/incertidumbre/punto5_rangos/resumen_rangos_resultados.json`

## Reproducibilidad de cierre one-click (Punto 6)

Validacion rapida sin recomputar toda la investigacion:

```bash
python "Código/run_research_pipeline.py" --dry-run
python "Código/run_research_pipeline.py" --skip-clean-stop-times --skip-validation --skip-l-space --skip-p-space
```

Checklist de validacion en `out/pipeline_state/research_last_run.json`:
- `prerequisites.ok` en `true`.
- `steps[*].status` consistente con el modo ejecutado (`planned`, `skipped_by_flag`, `completed`, `skipped_checkpoint`).
- `critical_outputs` con existencia de archivos clave (`stop_times_cleaned`, `l_space_consolidated_graph_path`, `p_space_graph_path`).

## Salidas esperadas

- Grafos y metricas: `grafos/`
- Exportes QGIS: `grafos_qgis/`
- Reporte de duplicados GTFS: `out/validacion_gtfs/`
- Estado y reportes de pipeline: `out/pipeline_state/`

Estos directorios estan ignorados en Git para no versionar artefactos generados.
