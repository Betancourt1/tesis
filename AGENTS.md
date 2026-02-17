# Repository Guidelines

## Project Structure & Module Organization
- `Código/` contains the Python workflows for transport-network modeling.
- `Código/l_space/` and `Código/p_space/` each include `construcción/`, `análisis/`, and a pipeline entrypoint (`run_l_space_pipeline.py`, `run_p_space_pipeline.py`).
- `Datasets/` stores GTFS and supporting source files; treat this as input-only.
- `out/` stores generated artifacts (`.gpickle`, tables, intermediate outputs).
- `grafos/` and `grafos_qgis/` contain exported visualization/network files.
- `Latex/Tesis/` is the thesis manuscript (`main.tex` plus chapter files); `Latex/Presentacion/` and `Latex/Protocolo/` are supporting documents.

## Build, Test, and Development Commands
- `python -m pip install -r requirements.txt`: install Python dependencies.
- `python "Código/l_space/run_l_space_pipeline.py"`: build and consolidate the L-space graph.
- `python "Código/p_space/run_p_space_pipeline.py"`: build the P-space graph (run after L-space).
- `python "Código/l_space/análisis/centralidades/calcular_centralidades.py"`: example metric run for L-space.
- `pdflatex Latex/Tesis/main.tex`: compile thesis draft from LaTeX sources.

## Coding Style & Naming Conventions
- Python: follow PEP 8, 4-space indentation, and `snake_case` for functions/files.
- Keep module responsibilities split by stage (`construcción`, `análisis`, `exportar_*`).
- Prefer relative paths and `.env` configuration over hardcoded absolute paths.
- Name outputs descriptively, e.g., `grafo_consolidado.gpickle`, `grafico_robustez_comparativo.png`.

## Testing Guidelines
- There is no enforced automated test suite yet.
- Validate changes by rerunning affected pipelines and checking regenerated files in `out/`, `grafos/`, and summary `.txt` outputs.
- For new reusable logic, add `pytest` tests under a new `tests/` directory (file pattern: `test_*.py`).

## Commit & Pull Request Guidelines
- Use concise, imperative commit subjects (Spanish or English), and include scope when useful.
- Avoid vague messages like `Cambiar cosas`; prefer `Refine modularity metrics in capitulo1`.
- PRs should include: objective, modified datasets/scripts, commands run, and key output paths.
- Attach screenshots when LaTeX figures/tables or graph visualizations change.

## Security & Configuration Tips
- Copy `.env.example` to `.env` for local configuration; never commit secrets.
- Do not add large derived binaries unless they are required reproducible outputs.

## Seguimiento IA - Mejoras de Tesis (Backlog Vivo)
- Regla de uso:
- Esta lista contiene solo pendientes. Cuando una mejora se complete, se elimina de esta sección.
- La evidencia de cierre debe quedar en commit(s) y/o en `Latex/Tesis/*.tex`, `Código/*`, `grafos/*`, `out/*`.


- [ ] 7) Consistencia editorial total
- Objetivo: unificar términos y notación en toda la tesis.
- Acción mínima: estandarizar `supernodo`, `arista`/`arco`, `salto`/`trasbordo`, criterios de redondeo y estilo técnico.
- Evidencia esperada: correcciones transversales en `Latex/Tesis/capitulo*.tex`.

- [ ] 8) Storytelling de figuras y tablas
- Objetivo: que cada visual responda una pregunta concreta y sea legible sin ambigüedad.
- Acción mínima: mejorar captions, referencias en texto y secuencia narrativa; reducir visuales densas sin guía.
- Evidencia esperada: figuras/captions ajustados en cap. 4 y posibles reemplazos en `grafos/*`.

- [ ] 9) Cierre con recomendaciones accionables
- Objetivo: traducir resultados de red a decisiones de planeación claras.
- Acción mínima: incluir recomendaciones priorizadas con impacto esperado, riesgo y dependencia de datos.
- Evidencia esperada: subsección final en `Latex/Tesis/capitulo5_conclusiones.tex`.
