# Tesis

Repositorio de la tesis de modelacion matematica para obtener el grado de licenciado en matematicas por la Universidad de Guadalajara.

El proyecto modela la red de transporte publico del Area Metropolitana de Guadalajara mediante teoria de grafos. Incluye datos GTFS, scripts de construccion y analisis, salidas tabulares, figuras y fuentes LaTeX.

## Estructura

- `Datasets/`: datos fuente usados por el proyecto. El paquete GTFS principal se conserva en `Datasets/gtfs_amg_20240312/`.
- `Código/`: scripts de limpieza, construccion de grafos, analisis y pipelines.
- `grafos/`: figuras y resumenes derivados que se citan en la tesis. Los grafos pesados se regeneran con los pipelines y no se versionan.
- `out/`: tablas, resumenes y figuras finales de sensibilidad, intervenciones y validacion.
- `Latex/Tesis/`: manuscrito principal y PDF compilado.
- `Latex/Protocolo/` y `Latex/Presentacion/`: documentos de apoyo.

## Datos

Los datos GTFS provienen del portal de datos abiertos del Gobierno de Jalisco:

```text
Secretaria de Transporte del estado de Jalisco.
Actualizacion de Rutas de Transporte Publico Colectivo y Masivo
en la Zona Metropolitana de Guadalajara.
https://datos.jalisco.gob.mx/dataset/actualizacion-de-rutas-de-transporte-publico-colectivo-y-masivo-en-la-zona-metropolitana-de
```

La referencia del protocolo registra la consulta original el 19 de septiembre de 2024. Al ordenar este repositorio para publicacion, el dominio `datos.jalisco.gob.mx` ya no resolvia desde el entorno local; por eso se conserva una copia de los insumos usados en `Datasets/`.

## Ejecucion reproducible

Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

Reconstruir la parte computacional completa:

```bash
python "Código/run_research_pipeline.py"
```

Validar prerequisitos y plan sin ejecutar pasos:

```bash
python "Código/run_research_pipeline.py" --dry-run
```

El pipeline soporta reanudacion con checkpoints locales en `out/pipeline_state/` y genera las salidas analiticas usadas por la tesis. La guia detallada esta en `Código/README.md`.

## Tesis

El manuscrito principal esta en `Latex/Tesis/main.tex`. Para compilarlo:

```bash
cd Latex/Tesis
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

El PDF final versionado se conserva en `Latex/Tesis/main.pdf`.
