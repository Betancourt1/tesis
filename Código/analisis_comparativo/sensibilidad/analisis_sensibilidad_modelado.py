from __future__ import annotations

import argparse
import json
import pickle
import time
from itertools import combinations
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.cluster import DBSCAN

RADIO_TIERRA_METROS = 6_371_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analiza sensibilidad de supuestos de modelado: "
            "umbral de consolidacion (L-space) y definicion de clique en P-space."
        )
    )
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=int,
        default=[75, 100, 125, 150],
        help="Umbrales DBSCAN (metros) para consolidacion de supernodos.",
    )
    parser.add_argument(
        "--output-dir",
        default="out/sensibilidad/punto3_modelado",
        help="Directorio de salida para tablas y resumen.",
    )
    return parser.parse_args()


def load_env(repo_root: Path) -> None:
    dotenv_path = repo_root / ".env"
    if not dotenv_path.exists():
        raise FileNotFoundError("No existe .env en la raiz del repositorio.")
    load_dotenv(dotenv_path=dotenv_path)


def resolve_paths(repo_root: Path) -> dict[str, Path]:
    import os

    l_initial = os.getenv("L_SPACE_INITIAL_GRAPH_PATH")
    gtfs_dir = os.getenv("GTFS_DIR")
    if not l_initial or not gtfs_dir:
        raise ValueError("Faltan variables en .env: L_SPACE_INITIAL_GRAPH_PATH y/o GTFS_DIR.")

    gtfs_path = repo_root / gtfs_dir
    return {
        "l_initial_graph": repo_root / l_initial,
        "stop_times": gtfs_path / "stop_times.csv",
        "trips": gtfs_path / "trips.csv",
    }


def load_initial_l_space_graph(path: Path) -> tuple[nx.DiGraph, list[str], np.ndarray, list[float]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe grafo inicial: {path}")
    graph = nx.read_gexf(path)
    if not isinstance(graph, nx.DiGraph):
        graph = nx.DiGraph(graph)

    node_ids: list[str] = []
    coords_deg: list[list[float]] = []
    travel_times: list[float] = []

    for node_id, data in graph.nodes(data=True):
        if "stop_lat" in data and "stop_lon" in data:
            node_ids.append(str(node_id))
            coords_deg.append([float(data["stop_lat"]), float(data["stop_lon"])])

    for _, _, data in graph.edges(data=True):
        try:
            t = float(data.get("travel_time_minutes", -1.0))
        except (TypeError, ValueError):
            t = -1.0
        travel_times.append(t)

    return graph, node_ids, np.radians(np.asarray(coords_deg)), travel_times


def build_group_stop_sets(stop_times_path: Path, trips_path: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    if not stop_times_path.exists():
        raise FileNotFoundError(f"No existe: {stop_times_path}")
    if not trips_path.exists():
        raise FileNotFoundError(f"No existe: {trips_path}")

    stop_times_df = pd.read_csv(stop_times_path, dtype={"trip_id": str, "stop_id": str})
    trips_df = pd.read_csv(trips_path, dtype={"trip_id": str, "route_id": str})[["trip_id", "route_id"]]

    stop_times_df = stop_times_df[["trip_id", "stop_id"]].drop_duplicates()
    route_stops_df = stop_times_df.merge(trips_df, on="trip_id", how="inner")

    route_groups = {
        str(route_id): {str(stop_id) for stop_id in group["stop_id"].tolist()}
        for route_id, group in route_stops_df.groupby("route_id")
    }
    trip_groups = {
        str(trip_id): {str(stop_id) for stop_id in group["stop_id"].tolist()}
        for trip_id, group in stop_times_df.groupby("trip_id")
    }
    return route_groups, trip_groups


def cluster_stops(
    stop_ids: list[str],
    coords_rad: np.ndarray,
    threshold_m: int,
) -> tuple[dict[str, str], set[str]]:
    eps_rad = threshold_m / RADIO_TIERRA_METROS
    db = DBSCAN(eps=eps_rad, min_samples=1, algorithm="ball_tree", metric="haversine")
    labels = db.fit_predict(coords_rad)

    stop_to_supernode = {str(stop_id): str(cluster_id) for stop_id, cluster_id in zip(stop_ids, labels)}
    supernodes = {str(cluster_id) for cluster_id in labels}
    return stop_to_supernode, supernodes


def build_l_space_graph_for_threshold(
    initial_graph: nx.DiGraph,
    stop_to_supernode: dict[str, str],
    fallback_travel_time: float,
) -> tuple[nx.DiGraph, int]:
    aggregated_edges: dict[tuple[str, str], list[float]] = {}

    for u, v, data in initial_graph.edges(data=True):
        su = stop_to_supernode.get(str(u))
        sv = stop_to_supernode.get(str(v))
        if su is None or sv is None or su == sv:
            continue

        edge_key = (su, sv)
        aggregated_edges.setdefault(edge_key, [])
        try:
            t = float(data.get("travel_time_minutes", -1.0))
        except (TypeError, ValueError):
            t = -1.0
        aggregated_edges[edge_key].append(t)

    l_graph = nx.DiGraph()
    l_graph.add_nodes_from(set(stop_to_supernode.values()))

    imputed_edges = 0
    for (u, v), times in aggregated_edges.items():
        valid = [t for t in times if t >= 0]
        if valid:
            travel_time = min(valid)
            imputed = False
        else:
            travel_time = fallback_travel_time
            imputed = True
            imputed_edges += 1
        l_graph.add_edge(u, v, travel_time_minutes=travel_time, travel_time_imputed=imputed)

    return l_graph, imputed_edges


def build_p_space_graph(
    group_stop_sets: dict[str, set[str]],
    stop_to_supernode: dict[str, str],
    supernodes: set[str],
) -> nx.Graph:
    p_graph = nx.Graph()
    p_graph.add_nodes_from(supernodes)

    for stop_set in group_stop_sets.values():
        supernode_set = sorted({stop_to_supernode[stop_id] for stop_id in stop_set if stop_id in stop_to_supernode})
        if len(supernode_set) < 2:
            continue
        for u, v in combinations(supernode_set, 2):
            if p_graph.has_edge(u, v):
                p_graph[u][v]["weight"] += 1
            else:
                p_graph.add_edge(u, v, weight=1)

    return p_graph


def graph_metrics_directed(graph: nx.DiGraph) -> dict[str, float]:
    undirected = graph.to_undirected()
    component_sizes = sorted((len(c) for c in nx.connected_components(undirected)), reverse=True)
    lcc_size = component_sizes[0] if component_sizes else 0
    n = graph.number_of_nodes()
    m = graph.number_of_edges()

    return {
        "nodes": n,
        "edges": m,
        "density": nx.density(graph),
        "components": len(component_sizes),
        "lcc_size": lcc_size,
        "lcc_ratio": (lcc_size / n) if n else 0.0,
        "transitivity_undirected": nx.transitivity(undirected) if n > 2 else 0.0,
    }


def graph_metrics_undirected(graph: nx.Graph) -> dict[str, float]:
    component_sizes = sorted((len(c) for c in nx.connected_components(graph)), reverse=True)
    lcc_size = component_sizes[0] if component_sizes else 0
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    avg_degree = float(sum(dict(graph.degree()).values()) / n) if n else 0.0

    return {
        "nodes": n,
        "edges": m,
        "density": nx.density(graph),
        "components": len(component_sizes),
        "lcc_size": lcc_size,
        "lcc_ratio": (lcc_size / n) if n else 0.0,
        "avg_degree": avg_degree,
        "transitivity": nx.transitivity(graph) if n > 2 else 0.0,
    }


def edge_set_undirected(graph: nx.Graph) -> set[tuple[str, str]]:
    return {tuple(sorted((str(u), str(v)))) for u, v in graph.edges()}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    t0 = time.time()

    repo_root = Path(__file__).resolve().parents[3]
    load_env(repo_root)
    paths = resolve_paths(repo_root)

    output_dir = repo_root / args.output_dir
    ensure_dir(output_dir)

    print("Cargando insumos base...")
    initial_graph, stop_ids, coords_rad, edge_travel_times = load_initial_l_space_graph(paths["l_initial_graph"])
    route_groups, trip_groups = build_group_stop_sets(paths["stop_times"], paths["trips"])

    valid_edge_times = [t for t in edge_travel_times if t >= 0]
    fallback_travel_time = float(np.median(valid_edge_times)) if valid_edge_times else 1.0

    print(f"Paradas con coordenadas: {len(stop_ids)}")
    print(f"Rutas GTFS: {len(route_groups)} | Viajes GTFS: {len(trip_groups)}")
    print(f"Fallback travel_time (mediana): {fallback_travel_time:.4f} min")

    l_rows: list[dict[str, float | int | str]] = []
    p_rows: list[dict[str, float | int | str]] = []
    diff_rows: list[dict[str, float | int | str]] = []

    for threshold in args.thresholds:
        print(f"\n=== Escenario umbral = {threshold} m ===")
        stop_to_supernode, supernodes = cluster_stops(stop_ids, coords_rad, threshold)
        print(f"Supernodos: {len(supernodes)}")

        l_graph, imputed_edges = build_l_space_graph_for_threshold(
            initial_graph=initial_graph,
            stop_to_supernode=stop_to_supernode,
            fallback_travel_time=fallback_travel_time,
        )
        l_metrics = graph_metrics_directed(l_graph)
        l_row = {
            "scenario": f"L_threshold_{threshold}m",
            "threshold_m": threshold,
            **l_metrics,
            "imputed_edges": imputed_edges,
            "imputed_edges_pct": (imputed_edges / l_metrics["edges"] * 100.0) if l_metrics["edges"] else 0.0,
        }
        l_rows.append(l_row)
        print(
            "L-space -> "
            f"n={l_metrics['nodes']}, e={l_metrics['edges']}, dens={l_metrics['density']:.6f}, "
            f"comp={l_metrics['components']}, imputed={imputed_edges}"
        )

        p_route = build_p_space_graph(route_groups, stop_to_supernode, supernodes)
        p_trip = build_p_space_graph(trip_groups, stop_to_supernode, supernodes)

        p_route_metrics = graph_metrics_undirected(p_route)
        p_trip_metrics = graph_metrics_undirected(p_trip)

        p_rows.append(
            {
                "scenario": f"P_route_threshold_{threshold}m",
                "threshold_m": threshold,
                "clique_scope": "route_id",
                **p_route_metrics,
            }
        )
        p_rows.append(
            {
                "scenario": f"P_trip_threshold_{threshold}m",
                "threshold_m": threshold,
                "clique_scope": "trip_id",
                **p_trip_metrics,
            }
        )

        route_edges = edge_set_undirected(p_route)
        trip_edges = edge_set_undirected(p_trip)
        route_only = route_edges - trip_edges

        diff_rows.append(
            {
                "threshold_m": threshold,
                "route_edges": p_route.number_of_edges(),
                "trip_edges": p_trip.number_of_edges(),
                "route_only_edges": len(route_only),
                "route_only_pct_of_route": (len(route_only) / p_route.number_of_edges() * 100.0)
                if p_route.number_of_edges()
                else 0.0,
            }
        )

        print(
            "P-space(route/trip) -> "
            f"e_route={p_route.number_of_edges()}, e_trip={p_trip.number_of_edges()}, "
            f"route_only={len(route_only)} ({diff_rows[-1]['route_only_pct_of_route']:.2f}%)"
        )

    l_df = pd.DataFrame(l_rows).sort_values("threshold_m")
    p_df = pd.DataFrame(p_rows).sort_values(["threshold_m", "clique_scope"])
    diff_df = pd.DataFrame(diff_rows).sort_values("threshold_m")

    l_csv = output_dir / "sensibilidad_l_space.csv"
    p_csv = output_dir / "sensibilidad_p_space.csv"
    diff_csv = output_dir / "sensibilidad_p_route_vs_trip.csv"

    l_df.to_csv(l_csv, index=False)
    p_df.to_csv(p_csv, index=False)
    diff_df.to_csv(diff_csv, index=False)

    summary = {
        "thresholds_m": args.thresholds,
        "l_space_rows": len(l_df),
        "p_space_rows": len(p_df),
        "runtime_seconds": round(time.time() - t0, 2),
        "outputs": {
            "sensibilidad_l_space": str(l_csv),
            "sensibilidad_p_space": str(p_csv),
            "sensibilidad_p_route_vs_trip": str(diff_csv),
        },
    }
    summary_path = output_dir / "resumen_sensibilidad.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Sensibilidad completada ===")
    print(f"Tiempo total: {summary['runtime_seconds']} s")
    print(f"Salida: {l_csv}")
    print(f"Salida: {p_csv}")
    print(f"Salida: {diff_csv}")
    print(f"Salida: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
