from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def build_signature(script_path: Path) -> str:
    stat = script_path.stat()
    return f"{script_path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}"


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"steps": {}}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def run_script(script_path: Path, description: str) -> None:
    print(f"\n--- {description} ---")
    command = [sys.executable, str(script_path)]
    print(f"Executing command: {' '.join(command)}")
    result = subprocess.run(command, check=True)
    if result.returncode == 0:
        print(f"SUCCESS: {description} completed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline L-space con soporte de reanudacion.")
    parser.add_argument(
        "--state-file",
        default="out/pipeline_state/l_space.json",
        help="Archivo JSON para guardar estado de pasos completados.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="No usar checkpoints; ejecutar todo desde cero.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignorar checkpoints y forzar ejecucion de todos los pasos.",
    )
    return parser.parse_args()


def run_l_space_pipeline(state_file: Path, resume: bool, force: bool) -> None:
    print("=============================================")
    print("=== Starting L-Space Graph Pipeline =========")
    print("=============================================")

    l_space_dir = Path(__file__).resolve().parent
    steps = [
        (
            "l_space_build_initial",
            l_space_dir / "construcción" / "construcción_de_grafo.py",
            "Construccion inicial del grafo L-espacio desde GTFS",
        ),
        (
            "l_space_consolidate",
            l_space_dir / "construcción" / "consolidación.py",
            "Consolidacion de paradas para el grafo L-espacio",
        ),
        (
            "l_space_centralidades",
            l_space_dir / "análisis" / "centralidades" / "calcular_centralidades.py",
            "Calculo de centralidades para el grafo L-espacio",
        ),
        (
            "l_space_comunidades_detectar",
            l_space_dir / "análisis" / "comunidades" / "detectar_comunidades.py",
            "Deteccion de comunidades para el grafo L-espacio",
        ),
        (
            "l_space_comunidades_analizar",
            l_space_dir / "análisis" / "comunidades" / "analizar_comunidades.py",
            "Analisis de las comunidades detectadas en el grafo L-espacio",
        ),
        (
            "l_space_conectividad",
            l_space_dir / "análisis" / "métricas_globales" / "conectividad.py",
            "Analisis de conectividad del grafo L-espacio",
        ),
        (
            "l_space_distancias",
            l_space_dir / "análisis" / "métricas_globales" / "distancias.py",
            "Calculo de la matriz de distancias del grafo L-espacio",
        ),
        (
            "l_space_analisis_matriz",
            l_space_dir / "análisis" / "métricas_globales" / "analisis_matriz_distancias.py",
            "Analisis de la matriz de distancias del grafo L-espacio",
        ),
        (
            "l_space_eficiencia",
            l_space_dir / "análisis" / "métricas_globales" / "eficiencia.py",
            "Analisis de eficiencia del grafo L-espacio",
        ),
        (
            "l_space_estructura_local",
            l_space_dir / "análisis" / "métricas_globales" / "estructura_local.py",
            "Analisis de la estructura local del grafo L-espacio",
        ),
        (
            "l_space_robustez",
            l_space_dir / "análisis" / "robustez" / "analisis_robustez.py",
            "Analisis de robustez del grafo L-espacio",
        ),
    ]

    state = load_state(state_file)
    for step_id, script_path, description in steps:
        signature = build_signature(script_path)
        prev = state["steps"].get(step_id, {})
        if resume and not force and prev.get("status") == "completed" and prev.get("signature") == signature:
            print(f"SKIP: {description} (checkpoint)")
            continue

        state["steps"][step_id] = {
            "status": "running",
            "signature": signature,
            "started_at": datetime.now().isoformat(),
        }
        save_state(state_file, state)

        try:
            run_script(script_path, description)
        except Exception:
            state["steps"][step_id] = {
                "status": "failed",
                "signature": signature,
                "failed_at": datetime.now().isoformat(),
            }
            save_state(state_file, state)
            raise

        state["steps"][step_id] = {
            "status": "completed",
            "signature": signature,
            "completed_at": datetime.now().isoformat(),
        }
        save_state(state_file, state)

    print("=============================================")
    print("=== L-Space Graph Pipeline Completed ========")
    print("=============================================")


if __name__ == "__main__":
    args = parse_args()
    run_l_space_pipeline(
        state_file=Path(args.state_file),
        resume=not args.no_resume,
        force=args.force,
    )
