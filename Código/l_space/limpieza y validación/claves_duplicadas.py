from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


def resolve_default_paths() -> tuple[Path, Path, Path]:
    repo_root = Path(__file__).resolve().parents[3]
    dotenv_path = repo_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)

    gtfs_rel = os.getenv("GTFS_DIR")
    if not gtfs_rel:
        raise ValueError("GTFS_DIR no esta definido en .env")

    gtfs_dir = (repo_root / gtfs_rel).resolve()
    return (
        gtfs_dir / "stop_times.csv",
        gtfs_dir / "stop_times_cleaned.csv",
        repo_root / "out" / "validacion_gtfs" / "duplicados_stop_times.csv",
    )


def parse_args() -> argparse.Namespace:
    default_input, default_output, default_report = resolve_default_paths()
    parser = argparse.ArgumentParser(
        description="Detecta y corrige duplicados de stop_times para generar stop_times_cleaned.csv"
    )
    parser.add_argument("--input", default=str(default_input), help="Ruta de stop_times.csv")
    parser.add_argument(
        "--output",
        default=str(default_output),
        help="Ruta de salida para stop_times_cleaned.csv",
    )
    parser.add_argument(
        "--report",
        default=str(default_report),
        help="Ruta del reporte CSV de duplicados",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    report_path = Path(args.report)

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    stop_times = pd.read_csv(input_path, dtype=str)

    print("=" * 80)
    print("DIAGNOSTICO DE DUPLICADOS EN stop_times.csv")
    print("=" * 80)

    duplicated_mask = stop_times.duplicated(subset=["trip_id", "stop_sequence"], keep=False)
    duplicated_rows = stop_times[duplicated_mask]

    print(f"\nTotal de registros duplicados: {len(duplicated_rows)}")
    print(f"Porcentaje: {len(duplicated_rows) / len(stop_times) * 100:.2f}%")

    if not duplicated_rows.empty:
        print("\n" + "=" * 80)
        print("ANALISIS DE PRIMEROS CASOS DUPLICADOS")
        print("=" * 80)

        trips_duplicated = (
            duplicated_rows.groupby("trip_id").size().sort_values(ascending=False).head(5)
        )
        print("\nTop 5 viajes con mas duplicados:")
        print(trips_duplicated)

        first_trip = trips_duplicated.index[0]
        example = stop_times[stop_times["trip_id"] == first_trip].sort_values("stop_sequence")
        print(f"\nEjemplo detallado del viaje: {first_trip}")
        print(
            example[
                ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"]
            ].to_string(index=False)
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    duplicated_rows.sort_values(["trip_id", "stop_sequence"]).to_csv(report_path, index=False)
    print(f"\nReporte guardado en: {report_path}")

    train_mask = stop_times["stop_id"].str.startswith("MT-", na=False)
    rows_to_drop_mask = duplicated_mask & train_mask
    rows_to_drop = int(rows_to_drop_mask.sum())

    if rows_to_drop > 0:
        print(f"\nSe eliminaran {rows_to_drop} registros duplicados de Tren Ligero (MT-*)")
        stop_times_cleaned = stop_times[~rows_to_drop_mask]
    else:
        print("\nNo se encontraron duplicados de Tren Ligero para eliminar.")
        stop_times_cleaned = stop_times.copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stop_times_cleaned.to_csv(output_path, index=False)

    print(f"\nArchivo corregido guardado en: {output_path}")
    print(f"Registros originales: {len(stop_times)}")
    print(f"Registros despues de limpieza: {len(stop_times_cleaned)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
