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

## Pipeline reproducible (un solo comando)

Desde la raiz del repo:

```bash
python Código/run_research_pipeline.py
```

El pipeline hace, en orden:
1. Genera `stop_times_cleaned.csv` (`claves_duplicadas.py`).
2. Valida GTFS (`preprocesamiento.py`).
3. Ejecuta construccion + analisis de `L-space`.
4. Ejecuta construccion + analisis de `P-space`.

El pipeline guarda checkpoints en `out/pipeline_state/`. Si falla en un paso avanzado, al relanzar continua desde donde se quedo.

## Opciones utiles

- Continuar aunque falle validacion GTFS:

```bash
python Código/run_research_pipeline.py --continue-on-validation-fail
```

- Omitir pasos especificos:

```bash
python Código/run_research_pipeline.py --skip-validation --skip-clean-stop-times
```

- Exportar resultados para Gephi/QGIS al final:

```bash
python Código/run_research_pipeline.py --export both
```

- Forzar recalculo completo sin usar checkpoints:

```bash
python Código/run_research_pipeline.py --force
```

- Re-ejecutar ignorando estado guardado (sin borrar archivos):

```bash
python Código/run_research_pipeline.py --no-resume
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

## Salidas esperadas

- Grafos y metricas: `grafos/`
- Exportes QGIS: `grafos_qgis/`
- Reporte de duplicados GTFS: `out/validacion_gtfs/`

Estos directorios estan ignorados en Git para no versionar artefactos generados.
