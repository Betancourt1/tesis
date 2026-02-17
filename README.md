# tesis
Tesis de modelacion matematica para obtener el grado de licenciado en matematicas por la UdG.

## Estructura general

- `Datasets/`: datos fuente (GTFS y otros insumos).
- `Código/`: construccion de grafos, analisis y pipelines.
- `Latex/`: redaccion de tesis y material de presentacion.

## Ejecucion reproducible

Para reconstruir la parte computacional completa:

```bash
python "Código/run_research_pipeline.py"
```

Para validar prerequisitos y plan sin ejecutar pasos:

```bash
python "Código/run_research_pipeline.py" --dry-run
```

El pipeline soporta reanudacion con checkpoints en `out/pipeline_state/` y genera reporte de ejecucion en `out/pipeline_state/research_last_run.json`.
Guia detallada y opciones en `Código/README.md`.
