from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


def build_signature(target_path: Path) -> str:
    stat = target_path.stat()
    return f"{target_path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}"


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"steps": {}}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def run_step(command: list[str], description: str, allow_failure: bool = False) -> None:
    print(f"\n=== {description} ===")
    print(f"$ {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        if allow_failure:
            print(f"WARNING: {description} failed with exit code {exc.returncode}, continuing.")
            return
        raise SystemExit(f"ERROR: {description} failed with exit code {exc.returncode}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta el pipeline completo de la investigacion (GTFS -> L-space -> P-space)."
    )
    parser.add_argument("--skip-validation", action="store_true", help="Omite validacion de GTFS.")
    parser.add_argument(
        "--skip-clean-stop-times",
        action="store_true",
        help="Omite la generacion de stop_times_cleaned.csv.",
    )
    parser.add_argument("--skip-l-space", action="store_true", help="Omite el pipeline de L-space.")
    parser.add_argument("--skip-p-space", action="store_true", help="Omite el pipeline de P-space.")
    parser.add_argument(
        "--export",
        choices=["none", "gephi", "qgis", "both"],
        default="none",
        help="Exportaciones adicionales al finalizar.",
    )
    parser.add_argument(
        "--continue-on-validation-fail",
        action="store_true",
        help="Continua aun si falla la validacion GTFS.",
    )
    parser.add_argument(
        "--state-file",
        default="out/pipeline_state/research.json",
        help="Archivo JSON para checkpoints del pipeline maestro.",
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


def run_checkpointed_step(
    state: dict,
    state_file: Path,
    step_id: str,
    signature_target: Path,
    command: list[str],
    description: str,
    resume: bool,
    force: bool,
    allow_failure: bool = False,
) -> None:
    signature = build_signature(signature_target)
    prev = state["steps"].get(step_id, {})
    if resume and not force and prev.get("status") == "completed" and prev.get("signature") == signature:
        print(f"SKIP: {description} (checkpoint)")
        return

    state["steps"][step_id] = {
        "status": "running",
        "signature": signature,
        "started_at": datetime.now().isoformat(),
    }
    save_state(state_file, state)

    try:
        run_step(command, description, allow_failure=allow_failure)
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


def main() -> int:
    args = parse_args()

    code_dir = Path(__file__).resolve().parent
    repo_root = code_dir.parent
    state_file = Path(args.state_file)
    resume = not args.no_resume

    dotenv_path = repo_root / ".env"
    if not dotenv_path.exists():
        raise SystemExit("ERROR: No existe .env en la raiz del repositorio.")

    load_dotenv(dotenv_path=dotenv_path)
    gtfs_dir = os.getenv("GTFS_DIR")
    if not gtfs_dir:
        raise SystemExit("ERROR: GTFS_DIR no esta definido en .env")

    gtfs_path = str((repo_root / gtfs_dir).resolve())
    state = load_state(state_file)

    print("=============================================")
    print("=== Research Pipeline: GTFS -> L -> P =======")
    print("=============================================")

    if not args.skip_clean_stop_times:
        script = code_dir / "l_space" / "limpieza y validación" / "claves_duplicadas.py"
        run_checkpointed_step(
            state=state,
            state_file=state_file,
            step_id="clean_stop_times",
            signature_target=script,
            command=[sys.executable, str(script)],
            description="Generacion de stop_times_cleaned.csv",
            resume=resume,
            force=args.force,
        )

    if not args.skip_validation:
        script = code_dir / "l_space" / "limpieza y validación" / "preprocesamiento.py"
        run_checkpointed_step(
            state=state,
            state_file=state_file,
            step_id="validate_gtfs",
            signature_target=script,
            command=[sys.executable, str(script), gtfs_path],
            description="Validacion GTFS",
            resume=resume,
            force=args.force,
            allow_failure=args.continue_on_validation_fail,
        )

    if not args.skip_l_space:
        script = code_dir / "l_space" / "run_l_space_pipeline.py"
        cmd = [sys.executable, str(script)]
        if args.force:
            cmd.append("--force")
        if args.no_resume:
            cmd.append("--no-resume")
        run_checkpointed_step(
            state=state,
            state_file=state_file,
            step_id="l_space_pipeline",
            signature_target=script,
            command=cmd,
            description="Pipeline completo L-space",
            resume=resume,
            force=args.force,
        )

    if not args.skip_p_space:
        script = code_dir / "p_space" / "run_p_space_pipeline.py"
        cmd = [sys.executable, str(script)]
        if args.force:
            cmd.append("--force")
        if args.no_resume:
            cmd.append("--no-resume")
        run_checkpointed_step(
            state=state,
            state_file=state_file,
            step_id="p_space_pipeline",
            signature_target=script,
            command=cmd,
            description="Pipeline completo P-space",
            resume=resume,
            force=args.force,
        )

    if args.export in {"gephi", "both"}:
        script = code_dir / "exportar_grafos_gephi.py"
        run_checkpointed_step(
            state=state,
            state_file=state_file,
            step_id="export_gephi",
            signature_target=script,
            command=[sys.executable, str(script)],
            description="Exportacion a GEXF para Gephi",
            resume=resume,
            force=args.force,
        )

    if args.export in {"qgis", "both"}:
        script = code_dir / "exportar_grafos_qgis.py"
        run_checkpointed_step(
            state=state,
            state_file=state_file,
            step_id="export_qgis",
            signature_target=script,
            command=[sys.executable, str(script)],
            description="Exportacion a GeoPackage para QGIS",
            resume=resume,
            force=args.force,
        )

    print("\nPipeline finalizado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
