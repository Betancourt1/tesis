from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consolida rangos de resultados para incertidumbre metodologica "
            "a partir de los analisis de sensibilidad (punto 3) e intervenciones (punto 4)."
        )
    )
    parser.add_argument(
        "--l-sensibilidad-csv",
        default="out/sensibilidad/punto3_modelado/sensibilidad_l_space.csv",
        help="CSV de sensibilidad del L-space (punto 3).",
    )
    parser.add_argument(
        "--p-route-trip-csv",
        default="out/sensibilidad/punto3_modelado/sensibilidad_p_route_vs_trip.csv",
        help="CSV de diferencia route_id vs trip_id en P-space (punto 3).",
    )
    parser.add_argument(
        "--intervenciones-csv",
        default="out/intervenciones/punto4_topologia/intervenciones_topologicas_l_space.csv",
        help="CSV de escenarios de intervencion topologica (punto 4).",
    )
    parser.add_argument(
        "--output-dir",
        default="out/incertidumbre/punto5_rangos",
        help="Directorio de salida para tablas y figuras del punto 5.",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe archivo requerido: {path}")
    return pd.read_csv(path)


def range_stats(series: pd.Series) -> tuple[float, float, float, float]:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if vals.empty:
        return 0.0, 0.0, 0.0, 0.0
    min_v = float(vals.min())
    max_v = float(vals.max())
    spread_abs = max_v - min_v
    # El porcentaje relativo solo es interpretable cuando el minimo es positivo.
    spread_pct_min = (spread_abs / min_v * 100.0) if min_v > 0 else float("nan")
    return min_v, max_v, spread_abs, spread_pct_min


def add_range_row(
    rows: list[dict[str, str | float]],
    bloque: str,
    metrica: str,
    serie: pd.Series,
    unidad: str,
) -> None:
    min_v, max_v, spread_abs, spread_pct_min = range_stats(serie)
    rows.append(
        {
            "bloque": bloque,
            "metrica": metrica,
            "min": min_v,
            "max": max_v,
            "amplitud_abs": spread_abs,
            "amplitud_pct_sobre_min": spread_pct_min,
            "unidad": unidad,
        }
    )


def save_modelado_figure(
    l_df: pd.DataFrame,
    p_df: pd.DataFrame,
    output_path: Path,
) -> None:
    l_plot = l_df.sort_values("threshold_m").copy()
    p_plot = p_df.sort_values("threshold_m").copy()
    l_plot["lcc_pct"] = pd.to_numeric(l_plot["lcc_ratio"], errors="coerce") * 100.0
    p_plot["route_only_pct_of_route"] = pd.to_numeric(p_plot["route_only_pct_of_route"], errors="coerce")

    thresholds = p_plot["threshold_m"].tolist()
    route_only = p_plot["route_only_pct_of_route"].tolist()
    lcc_values = l_plot["lcc_pct"].tolist()

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(thresholds, route_only, color="#c75b39", alpha=0.85, width=18, label="Route-only (%)")
    ax1.set_xlabel("Umbral de consolidacion (m)")
    ax1.set_ylabel("Route-only de P-space (%)", color="#c75b39")
    ax1.tick_params(axis="y", labelcolor="#c75b39")
    ax1.set_title("Punto 3: sensibilidad de modelado")

    ax2 = ax1.twinx()
    ax2.plot(thresholds, lcc_values, color="#245f9f", marker="o", linewidth=2.0, label="LCC L-space (%)")
    ax2.set_ylabel("LCC de L-space (%)", color="#245f9f")
    ax2.tick_params(axis="y", labelcolor="#245f9f")

    ax1.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def save_intervenciones_figure(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df.copy()
    scenario_labels = {
        "baseline": "Base",
        "proteccion_hubs": "Proteccion hubs",
        "refuerzo_periferico": "Refuerzo periferico",
        "recableado_bypass": "Recableado bypass",
    }
    plot_df["scenario_label"] = plot_df["scenario"].map(scenario_labels).fillna(plot_df["scenario"])
    plot_df["eff_retention_pct"] = pd.to_numeric(plot_df["eff_ratio_post_pre"], errors="coerce") * 100.0

    metrics = [
        ("lcc_post_pct", "LCC post-ataque (%)"),
        ("eff_retention_pct", "Retencion de eficiencia (%)"),
        ("diameter_post", "Diametro post-ataque"),
    ]

    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 9), constrained_layout=True)
    x = range(len(plot_df))

    for ax, (col, title) in zip(axes, metrics):
        values = pd.to_numeric(plot_df[col], errors="coerce").tolist()
        min_v, max_v, _, _ = range_stats(plot_df[col])
        ax.axhspan(min_v, max_v, color="#dbeaf7", alpha=0.8, label="Rango min-max")
        ax.plot(x, values, linestyle="", marker="o", color="#0f4c81", markersize=7)
        ax.set_title(title)
        ax.set_xticks(list(x), plot_df["scenario_label"].tolist(), rotation=0)
        ax.grid(axis="y", alpha=0.25)
        for idx, value in enumerate(values):
            if col == "diameter_post":
                label = f"{int(round(value))}"
            else:
                label = f"{value:.2f}"
            ax.annotate(label, (idx, value), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)

    axes[0].legend(loc="best")
    fig.suptitle("Punto 4: bandas de resultados por escenario", fontsize=12)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    t0 = time.time()

    repo_root = Path(__file__).resolve().parents[3]
    l_csv = repo_root / args.l_sensibilidad_csv
    p_csv = repo_root / args.p_route_trip_csv
    i_csv = repo_root / args.intervenciones_csv
    output_dir = repo_root / args.output_dir
    ensure_dir(output_dir)

    l_df = load_csv(l_csv)
    p_df = load_csv(p_csv)
    i_df = load_csv(i_csv)

    i_df["eff_retention_pct"] = pd.to_numeric(i_df["eff_ratio_post_pre"], errors="coerce") * 100.0
    l_df["lcc_pct"] = pd.to_numeric(l_df["lcc_ratio"], errors="coerce") * 100.0

    rows: list[dict[str, str | float]] = []
    add_range_row(rows, "P3_L-space", "Nodos", l_df["nodes"], "nodos")
    add_range_row(rows, "P3_L-space", "Aristas", l_df["edges"], "aristas")
    add_range_row(rows, "P3_L-space", "Densidad", l_df["density"], "adimensional")
    add_range_row(rows, "P3_L-space", "LCC", l_df["lcc_pct"], "%")

    add_range_row(rows, "P3_P-space", "Aristas route_only", p_df["route_only_edges"], "aristas")
    add_range_row(rows, "P3_P-space", "Route_only", p_df["route_only_pct_of_route"], "%")

    add_range_row(rows, "P4_Intervenciones", "LCC post-ataque", i_df["lcc_post_pct"], "%")
    add_range_row(rows, "P4_Intervenciones", "Retencion eficiencia post/pre", i_df["eff_retention_pct"], "%")
    add_range_row(rows, "P4_Intervenciones", "Diametro post-ataque", i_df["diameter_post"], "saltos")
    add_range_row(rows, "P4_Intervenciones", "Delta LCC vs base", i_df["delta_lcc_pp_vs_baseline_post"], "pp")
    add_range_row(rows, "P4_Intervenciones", "Delta eficiencia vs base", i_df["delta_eff_pp_vs_baseline_post"], "pp")

    ranges_df = pd.DataFrame(rows)
    ranges_csv = output_dir / "rangos_resultados.csv"
    ranges_df.to_csv(ranges_csv, index=False)

    modelado_fig = output_dir / "rangos_modelado_punto3.png"
    intervenciones_fig = output_dir / "rangos_intervenciones_punto4.png"
    save_modelado_figure(l_df, p_df, modelado_fig)
    save_intervenciones_figure(i_df, intervenciones_fig)

    resumen = {
        "runtime_seconds": round(time.time() - t0, 2),
        "inputs": {
            "l_sensibilidad_csv": str(l_csv),
            "p_route_trip_csv": str(p_csv),
            "intervenciones_csv": str(i_csv),
        },
        "outputs": {
            "rangos_resultados_csv": str(ranges_csv),
            "figura_modelado_punto3": str(modelado_fig),
            "figura_intervenciones_punto4": str(intervenciones_fig),
        },
        "highlights": {
            "route_only_pct_range": range_stats(p_df["route_only_pct_of_route"])[:2],
            "eff_retention_pct_range": range_stats(i_df["eff_retention_pct"])[:2],
            "lcc_post_pct_range": range_stats(i_df["lcc_post_pct"])[:2],
            "diameter_post_range": range_stats(i_df["diameter_post"])[:2],
        },
    }
    resumen_path = output_dir / "resumen_rangos_resultados.json"
    resumen_path.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Punto 5: rangos de resultados completado ===")
    print(f"Salida: {ranges_csv}")
    print(f"Salida: {modelado_fig}")
    print(f"Salida: {intervenciones_fig}")
    print(f"Salida: {resumen_path}")
    print(f"Tiempo total: {resumen['runtime_seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
