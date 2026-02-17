from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_GTFS_TABLES = ("agency", "stops", "routes", "trips", "stop_times")
CALENDAR_GTFS_TABLES = ("calendar", "calendar_dates")
COMPLETED_STATUSES = {"completed", "completed_with_warnings"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_repo_relative(repo_root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else repo_root / candidate


def build_signature(target_path: Path) -> str:
    if not target_path.exists():
        return f"MISSING:{target_path}"
    stat = target_path.stat()
    return f"{target_path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}"


def build_composite_signature(signature_targets: list[Path], context: str = "") -> str:
    parts = [build_signature(path) for path in signature_targets]
    if context:
        parts.append(f"context:{context}")
    return "||".join(parts)


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"steps": {}}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def save_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def run_step(command: list[str], description: str, cwd: Path, allow_failure: bool = False) -> tuple[str, int]:
    print(f"\n=== {description} ===")
    print(f"$ {' '.join(command)}")
    result = subprocess.run(command, check=False, cwd=str(cwd))
    if result.returncode == 0:
        return "completed", 0

    if allow_failure:
        print(f"WARNING: {description} failed with exit code {result.returncode}, continuing.")
        return "completed_with_warnings", result.returncode

    raise RuntimeError(f"{description} failed with exit code {result.returncode}.")


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
        "--report-file",
        default="out/pipeline_state/research_last_run.json",
        help="Reporte JSON de la ultima ejecucion del pipeline maestro.",
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida prerequisitos y muestra el plan, sin ejecutar pasos.",
    )
    return parser.parse_args()


def find_gtfs_table(gtfs_path: Path, table_name: str) -> Path | None:
    csv_path = gtfs_path / f"{table_name}.csv"
    txt_path = gtfs_path / f"{table_name}.txt"
    if csv_path.exists():
        return csv_path
    if txt_path.exists():
        return txt_path
    return None


def validate_prerequisites(gtfs_path: Path, scripts: list[Path]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    required_files: dict[str, str] = {}

    if not gtfs_path.exists():
        errors.append(f"GTFS_DIR no existe: {gtfs_path}")
        return {"ok": False, "errors": errors, "warnings": warnings, "required_files": required_files}
    if not gtfs_path.is_dir():
        errors.append(f"GTFS_DIR no es directorio: {gtfs_path}")
        return {"ok": False, "errors": errors, "warnings": warnings, "required_files": required_files}

    for table in REQUIRED_GTFS_TABLES:
        path = find_gtfs_table(gtfs_path, table)
        if path is None:
            errors.append(f"Falta archivo GTFS obligatorio: {table}.csv/txt")
            continue
        required_files[table] = str(path.resolve())
        if path.stat().st_size == 0:
            errors.append(f"Archivo GTFS vacio: {path}")

    has_calendar = any(find_gtfs_table(gtfs_path, table) is not None for table in CALENDAR_GTFS_TABLES)
    if not has_calendar:
        errors.append("Falta calendario de servicio: se requiere calendar.csv/txt o calendar_dates.csv/txt.")

    for script in scripts:
        if not script.exists():
            errors.append(f"No existe script del pipeline: {script}")

    if os.getenv("OUTPUT_DIR") is None:
        warnings.append("OUTPUT_DIR no esta definido en .env; se usaran rutas por defecto de scripts.")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings, "required_files": required_files}


def describe_path(path: Path) -> dict[str, str | bool | int]:
    exists = path.exists()
    return {
        "path": str(path.resolve() if exists else path),
        "exists": exists,
        "size_bytes": int(path.stat().st_size) if exists and path.is_file() else 0,
    }


def build_output_checks(repo_root: Path, gtfs_path: Path, state_file: Path, report_file: Path) -> dict:
    outputs: dict[str, Path] = {
        "stop_times_cleaned": gtfs_path / "stop_times_cleaned.csv",
        "research_state_file": state_file,
        "research_last_run_report": report_file,
    }

    env_output_keys = (
        "L_SPACE_INITIAL_GRAPH_PATH",
        "L_SPACE_CONSOLIDATED_GRAPH_PATH",
        "P_SPACE_GRAPH_PATH",
    )
    for key in env_output_keys:
        value = os.getenv(key)
        if value:
            outputs[key.lower()] = resolve_repo_relative(repo_root, value)

    return {name: describe_path(path) for name, path in outputs.items()}


def run_checkpointed_step(
    state: dict,
    state_file: Path,
    step_id: str,
    command: list[str],
    description: str,
    signature_targets: list[Path],
    signature_context: str,
    resume: bool,
    force: bool,
    repo_root: Path,
    expected_outputs: list[Path] | None = None,
    allow_failure: bool = False,
    dry_run: bool = False,
) -> dict:
    expected = expected_outputs or []
    signature = build_composite_signature(signature_targets, context=signature_context)
    prev = state["steps"].get(step_id, {})
    outputs_ok = all(path.exists() for path in expected)

    if resume and not force and prev.get("status") in COMPLETED_STATUSES and prev.get("signature") == signature and outputs_ok:
        print(f"SKIP: {description} (checkpoint)")
        return {
            "step_id": step_id,
            "description": description,
            "status": "skipped_checkpoint",
            "command": command,
        }

    if resume and not force and prev.get("status") in COMPLETED_STATUSES and prev.get("signature") == signature and not outputs_ok:
        print(f"RE-RUN: {description} (faltan salidas esperadas)")

    if dry_run:
        print(f"PLAN: {description}")
        print(f"  $ {' '.join(command)}")
        return {
            "step_id": step_id,
            "description": description,
            "status": "planned",
            "command": command,
        }

    state["steps"][step_id] = {
        "status": "running",
        "signature": signature,
        "started_at": utc_now_iso(),
    }
    save_state(state_file, state)

    try:
        status, return_code = run_step(command, description, cwd=repo_root, allow_failure=allow_failure)
    except Exception:
        state["steps"][step_id] = {
            "status": "failed",
            "signature": signature,
            "failed_at": utc_now_iso(),
        }
        save_state(state_file, state)
        raise

    state["steps"][step_id] = {
        "status": status,
        "signature": signature,
        "return_code": return_code,
        "completed_at": utc_now_iso(),
    }
    save_state(state_file, state)

    return {
        "step_id": step_id,
        "description": description,
        "status": status,
        "command": command,
        "return_code": return_code,
    }


def skip_by_flag_record(step_id: str, description: str) -> dict:
    return {
        "step_id": step_id,
        "description": description,
        "status": "skipped_by_flag",
        "command": [],
    }


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()

    code_dir = Path(__file__).resolve().parent
    repo_root = code_dir.parent
    state_file = resolve_repo_relative(repo_root, args.state_file)
    report_file = resolve_repo_relative(repo_root, args.report_file)
    l_state_file = state_file.parent / "l_space.json"
    p_state_file = state_file.parent / "p_space.json"
    resume = not args.no_resume

    report = {
        "pipeline": "research",
        "mode": "dry-run" if args.dry_run else "execute",
        "started_at": started_at,
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "args": vars(args),
        "repo_root": str(repo_root.resolve()),
        "state_file": str(state_file.resolve()),
        "steps": [],
        "status": "running",
    }

    try:
        dotenv_path = repo_root / ".env"
        if not dotenv_path.exists():
            raise RuntimeError("No existe .env en la raiz del repositorio.")

        load_dotenv(dotenv_path=dotenv_path)
        gtfs_dir = os.getenv("GTFS_DIR")
        if not gtfs_dir:
            raise RuntimeError("GTFS_DIR no esta definido en .env")

        gtfs_path = resolve_repo_relative(repo_root, gtfs_dir)
        gtfs_path_resolved = gtfs_path.resolve() if gtfs_path.exists() else gtfs_path

        stop_times_cleaned_path = gtfs_path / "stop_times_cleaned.csv"
        l_initial_env = os.getenv("L_SPACE_INITIAL_GRAPH_PATH")
        l_consolidated_env = os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH")
        p_graph_env = os.getenv("P_SPACE_GRAPH_PATH")

        l_initial_path = resolve_repo_relative(repo_root, l_initial_env) if l_initial_env else None
        l_consolidated_path = resolve_repo_relative(repo_root, l_consolidated_env) if l_consolidated_env else None
        p_graph_path = resolve_repo_relative(repo_root, p_graph_env) if p_graph_env else None

        step_defs: list[dict] = []

        clean_script = code_dir / "l_space" / "limpieza y validación" / "claves_duplicadas.py"
        step_defs.append(
            {
                "id": "clean_stop_times",
                "enabled": not args.skip_clean_stop_times,
                "script": clean_script,
                "description": "Generacion de stop_times_cleaned.csv",
                "command": [sys.executable, str(clean_script)],
                "allow_failure": False,
                "expected_outputs": [stop_times_cleaned_path],
            }
        )

        validate_script = code_dir / "l_space" / "limpieza y validación" / "preprocesamiento.py"
        step_defs.append(
            {
                "id": "validate_gtfs",
                "enabled": not args.skip_validation,
                "script": validate_script,
                "description": "Validacion GTFS",
                "command": [sys.executable, str(validate_script), str(gtfs_path_resolved)],
                "allow_failure": args.continue_on_validation_fail,
                "expected_outputs": [],
            }
        )

        l_script = code_dir / "l_space" / "run_l_space_pipeline.py"
        l_cmd = [sys.executable, str(l_script), "--state-file", str(l_state_file)]
        if args.force:
            l_cmd.append("--force")
        if args.no_resume:
            l_cmd.append("--no-resume")
        step_defs.append(
            {
                "id": "l_space_pipeline",
                "enabled": not args.skip_l_space,
                "script": l_script,
                "description": "Pipeline completo L-space",
                "command": l_cmd,
                "allow_failure": False,
                "expected_outputs": [path for path in [l_initial_path, l_consolidated_path] if path is not None],
            }
        )

        p_script = code_dir / "p_space" / "run_p_space_pipeline.py"
        p_cmd = [sys.executable, str(p_script), "--state-file", str(p_state_file)]
        if args.force:
            p_cmd.append("--force")
        if args.no_resume:
            p_cmd.append("--no-resume")
        step_defs.append(
            {
                "id": "p_space_pipeline",
                "enabled": not args.skip_p_space,
                "script": p_script,
                "description": "Pipeline completo P-space",
                "command": p_cmd,
                "allow_failure": False,
                "expected_outputs": [path for path in [p_graph_path] if path is not None],
            }
        )

        gephi_script = code_dir / "exportar_grafos_gephi.py"
        step_defs.append(
            {
                "id": "export_gephi",
                "enabled": args.export in {"gephi", "both"},
                "script": gephi_script,
                "description": "Exportacion a GEXF para Gephi",
                "command": [sys.executable, str(gephi_script)],
                "allow_failure": False,
                "expected_outputs": [],
            }
        )

        qgis_script = code_dir / "exportar_grafos_qgis.py"
        step_defs.append(
            {
                "id": "export_qgis",
                "enabled": args.export in {"qgis", "both"},
                "script": qgis_script,
                "description": "Exportacion a GeoPackage para QGIS",
                "command": [sys.executable, str(qgis_script)],
                "allow_failure": False,
                "expected_outputs": [],
            }
        )

        enabled_scripts = [step["script"] for step in step_defs if step["enabled"]]
        prereq = validate_prerequisites(gtfs_path, enabled_scripts)
        report["prerequisites"] = prereq
        report["gtfs_path"] = str(gtfs_path_resolved)

        if not prereq["ok"]:
            report["status"] = "failed_precheck"
            report["ended_at"] = utc_now_iso()
            save_report(report_file, report)
            print("ERROR: Fallaron prerequisitos del pipeline:")
            for msg in prereq["errors"]:
                print(f"  - {msg}")
            print(f"Reporte guardado en: {report_file}")
            return 1

        state = load_state(state_file)

        print("=============================================")
        print("=== Research Pipeline: GTFS -> L -> P =======")
        print("=============================================")
        if args.dry_run:
            print("Modo: dry-run (sin ejecucion de pasos)")
        print(f"GTFS_DIR: {gtfs_path_resolved}")
        if prereq["warnings"]:
            for warning in prereq["warnings"]:
                print(f"WARNING: {warning}")

        gtfs_signature_targets = [
            Path(path_str) for path_str in prereq.get("required_files", {}).values()
        ]

        for step in step_defs:
            if not step["enabled"]:
                report["steps"].append(skip_by_flag_record(step["id"], step["description"]))
                continue

            signature_targets = [dotenv_path, step["script"]]
            if step["id"] in {"clean_stop_times", "validate_gtfs"}:
                signature_targets.extend(gtfs_signature_targets)

            result = run_checkpointed_step(
                state=state,
                state_file=state_file,
                step_id=step["id"],
                command=step["command"],
                description=step["description"],
                signature_targets=signature_targets,
                signature_context=" ".join(step["command"]),
                resume=resume,
                force=args.force,
                repo_root=repo_root,
                expected_outputs=step["expected_outputs"],
                allow_failure=step["allow_failure"],
                dry_run=args.dry_run,
            )
            report["steps"].append(result)

        report["status"] = "completed"
        report["ended_at"] = utc_now_iso()
        save_report(report_file, report)
        report["critical_outputs"] = build_output_checks(
            repo_root=repo_root,
            gtfs_path=gtfs_path,
            state_file=state_file,
            report_file=report_file,
        )
        save_report(report_file, report)

        print("\nPipeline finalizado correctamente.")
        print(f"Reporte de ejecucion: {report_file}")
        return 0

    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        report["ended_at"] = utc_now_iso()
        save_report(report_file, report)
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
