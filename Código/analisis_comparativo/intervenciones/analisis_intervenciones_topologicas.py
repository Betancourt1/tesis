from __future__ import annotations

import argparse
import json
import pickle
import random
import time
from pathlib import Path

import networkx as nx
import pandas as pd
from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simula intervenciones topologicas sobre el L-space y cuantifica su efecto "
            "en LCC, eficiencia global dirigida y diametro bajo ataque dirigido."
        )
    )
    parser.add_argument(
        "--num-remove",
        type=int,
        default=50,
        help="Numero de nodos a remover en el ataque dirigido por grado ponderado.",
    )
    parser.add_argument(
        "--protect-top-k",
        type=int,
        default=10,
        help="Numero de hubs inmunizados en el escenario de proteccion.",
    )
    parser.add_argument(
        "--reinforcement-pairs",
        type=int,
        default=60,
        help="Numero de pares perifericos a conectar (bidireccional) en refuerzo periferico.",
    )
    parser.add_argument(
        "--rewire-hubs",
        type=int,
        default=20,
        help="Numero de hubs usados para generar bypasses en recableado.",
    )
    parser.add_argument(
        "--rewire-bypasses",
        type=int,
        default=200,
        help="Numero maximo de bypasses a crear en el escenario de recableado.",
    )
    parser.add_argument(
        "--preserve-edge-budget",
        action="store_true",
        help=(
            "Si se activa, por cada bypass agregado se remueve una arista de baja "
            "criticidad para conservar el numero de aristas."
        ),
    )
    parser.add_argument(
        "--efficiency-sources",
        type=int,
        default=500,
        help=(
            "Numero de nodos fuente a muestrear para estimar eficiencia dirigida. "
            "Si excede N, se calcula exacto."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla para aleatoriedad reproducible.",
    )
    parser.add_argument(
        "--output-dir",
        default="out/intervenciones/punto4_topologia",
        help="Directorio de salida para tablas y resumen.",
    )
    return parser.parse_args()


def load_env(repo_root: Path) -> None:
    dotenv_path = repo_root / ".env"
    if not dotenv_path.exists():
        raise FileNotFoundError("No existe .env en la raiz del repositorio.")
    load_dotenv(dotenv_path=dotenv_path)


def resolve_l_graph_path(repo_root: Path) -> Path:
    import os

    graph_rel = os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH")
    if not graph_rel:
        raise ValueError("Falta L_SPACE_CONSOLIDATED_GRAPH_PATH en .env")
    graph_path = repo_root / graph_rel
    if not graph_path.exists():
        raise FileNotFoundError(f"No existe el grafo consolidado: {graph_path}")
    return graph_path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_l_space_graph(path: Path) -> nx.DiGraph:
    with path.open("rb") as f:
        graph = pickle.load(f)
    if not isinstance(graph, nx.DiGraph):
        graph = nx.DiGraph(graph)
    return graph


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def infer_fallback_travel_time(graph: nx.DiGraph) -> float:
    vals = []
    for _, _, data in graph.edges(data=True):
        t = safe_float(data.get("travel_time_minutes"), default=-1.0)
        if t > 0:
            vals.append(t)
    if not vals:
        return 1.0
    vals.sort()
    mid = len(vals) // 2
    if len(vals) % 2 == 1:
        return float(vals[mid])
    return float((vals[mid - 1] + vals[mid]) / 2.0)


def edge_time(data: dict, fallback: float) -> float:
    t = safe_float(data.get("travel_time_minutes"), default=-1.0)
    return t if t > 0 else fallback


def weighted_degree(graph: nx.DiGraph) -> dict:
    result = {}
    for node in graph.nodes():
        in_w = 0.0
        out_w = 0.0
        for _, _, data in graph.in_edges(node, data=True):
            in_w += max(1.0, safe_float(data.get("original_edge_count"), default=1.0))
        for _, _, data in graph.out_edges(node, data=True):
            out_w += max(1.0, safe_float(data.get("original_edge_count"), default=1.0))
        if in_w == 0.0 and out_w == 0.0:
            in_w = safe_float(graph.nodes[node].get("in_degree_weighted"), default=0.0)
            out_w = safe_float(graph.nodes[node].get("out_degree_weighted"), default=0.0)
        result[node] = in_w + out_w
    return result


def top_nodes_by_weighted_degree(graph: nx.DiGraph, limit: int | None = None) -> list:
    wd = weighted_degree(graph)
    sorted_nodes = sorted(wd, key=wd.get, reverse=True)
    if limit is None:
        return sorted_nodes
    return sorted_nodes[:limit]


def estimate_directed_global_efficiency(
    graph: nx.DiGraph,
    weight: str = "travel_time_minutes",
    max_sources: int = 500,
    seed: int = 42,
) -> float:
    n = graph.number_of_nodes()
    if n < 2:
        return 0.0

    nodes = list(graph.nodes())
    if max_sources <= 0 or max_sources >= n:
        source_nodes = nodes
        scale = 1.0
    else:
        rng = random.Random(seed)
        source_nodes = rng.sample(nodes, max_sources)
        scale = n / len(source_nodes)

    total_eff = 0.0
    for source in source_nodes:
        dists = nx.single_source_dijkstra_path_length(graph, source, weight=weight)
        for target, dist in dists.items():
            if target == source:
                continue
            if dist > 0:
                total_eff += 1.0 / dist

    total_eff *= scale
    return total_eff / (n * (n - 1))


def core_metrics(
    graph: nx.DiGraph,
    max_eff_sources: int,
    seed: int,
) -> dict[str, float]:
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    if n == 0:
        return {
            "nodes": 0,
            "edges": 0,
            "components": 0,
            "lcc_size": 0,
            "lcc_ratio": 0.0,
            "global_efficiency": 0.0,
            "diameter": 0,
        }

    weak_components = sorted(nx.weakly_connected_components(graph), key=len, reverse=True)
    components = len(weak_components)
    lcc_nodes = weak_components[0] if weak_components else set()
    lcc_size = len(lcc_nodes)
    lcc_ratio = (lcc_size / n) if n else 0.0

    lcc = graph.subgraph(lcc_nodes).copy() if lcc_nodes else nx.DiGraph()
    efficiency = estimate_directed_global_efficiency(
        lcc,
        weight="travel_time_minutes",
        max_sources=max_eff_sources,
        seed=seed,
    )

    diameter = 0
    if lcc.number_of_nodes() > 1:
        und = lcc.to_undirected()
        if und.number_of_nodes() > 1 and nx.is_connected(und):
            diameter = nx.diameter(und)

    return {
        "nodes": n,
        "edges": m,
        "components": components,
        "lcc_size": lcc_size,
        "lcc_ratio": lcc_ratio,
        "global_efficiency": efficiency,
        "diameter": diameter,
    }


def simulate_targeted_attack(
    graph: nx.DiGraph,
    num_remove: int,
    protected_nodes: set | None = None,
) -> tuple[nx.DiGraph, list]:
    protected = protected_nodes or set()
    order = [n for n in top_nodes_by_weighted_degree(graph) if n not in protected]
    remove_nodes = order[: min(num_remove, len(order))]
    attacked = graph.copy()
    attacked.remove_nodes_from(remove_nodes)
    return attacked, remove_nodes


def apply_peripheral_reinforcement(
    graph: nx.DiGraph,
    num_pairs: int,
    fallback_time: float,
) -> tuple[nx.DiGraph, int]:
    reinforced = graph.copy()
    if reinforced.number_of_nodes() < 2 or num_pairs <= 0:
        return reinforced, 0

    lcc_nodes = max(nx.weakly_connected_components(reinforced), key=len)
    lcc = reinforced.subgraph(lcc_nodes).copy()
    und_lcc = lcc.to_undirected()

    closeness = nx.closeness_centrality(und_lcc)
    ranked = sorted(closeness, key=closeness.get)  # menor cercania = mas periferico
    if len(ranked) < 2:
        return reinforced, 0

    k = max(100, int(0.25 * len(ranked)))
    candidates = ranked[: min(k, len(ranked))]
    half = len(candidates) // 2
    left = candidates[:half]
    right = list(reversed(candidates[half:]))

    added_pairs = 0
    for idx in range(min(len(left), len(right))):
        if added_pairs >= num_pairs:
            break
        u = left[idx]
        v = right[idx]
        if u == v:
            continue
        if reinforced.has_edge(u, v) or reinforced.has_edge(v, u):
            continue
        try:
            dist_hops = nx.shortest_path_length(und_lcc, source=u, target=v)
        except nx.NetworkXNoPath:
            continue
        if dist_hops < 4:
            continue

        attrs = {
            "travel_time_minutes": fallback_time,
            "original_edge_count": 1.0,
            "intervention": "refuerzo_periferico",
        }
        reinforced.add_edge(u, v, **attrs)
        reinforced.add_edge(v, u, **attrs)
        added_pairs += 1

    return reinforced, added_pairs * 2


def apply_bypass_rewiring(
    graph: nx.DiGraph,
    hubs: list,
    max_bypasses: int,
    fallback_time: float,
    seed: int,
    preserve_edge_budget: bool,
) -> tuple[nx.DiGraph, int, int]:
    rewired = graph.copy()
    if max_bypasses <= 0:
        return rewired, 0, 0

    rng = random.Random(seed)
    hub_set = set(hubs)
    added_edges: list[tuple] = []

    for hub in hubs:
        preds = [u for u in rewired.predecessors(hub) if u not in hub_set]
        succs = [v for v in rewired.successors(hub) if v not in hub_set]
        rng.shuffle(preds)
        rng.shuffle(succs)

        for u in preds:
            if len(added_edges) >= max_bypasses:
                break
            for v in succs:
                if len(added_edges) >= max_bypasses:
                    break
                if u == v or rewired.has_edge(u, v):
                    continue
                data_uh = rewired.get_edge_data(u, hub, default={})
                data_hv = rewired.get_edge_data(hub, v, default={})
                t = edge_time(data_uh, fallback_time) + edge_time(data_hv, fallback_time)
                rewired.add_edge(
                    u,
                    v,
                    travel_time_minutes=t,
                    original_edge_count=1.0,
                    intervention="recableado_bypass",
                )
                added_edges.append((u, v))

    to_remove = len(added_edges)
    if to_remove == 0:
        return rewired, 0, 0
    if not preserve_edge_budget:
        return rewired, len(added_edges), 0

    bridges = {tuple(sorted((u, v))) for u, v in nx.bridges(rewired.to_undirected())}
    candidates = []
    for u, v, data in rewired.edges(data=True):
        if (u, v) in added_edges:
            continue
        if u in hub_set or v in hub_set:
            continue
        if tuple(sorted((u, v))) in bridges:
            continue
        if data.get("intervention") == "recableado_bypass":
            continue
        edge_w = max(1.0, safe_float(data.get("original_edge_count"), default=1.0))
        tt = edge_time(data, fallback_time)
        candidates.append((edge_w, -tt, u, v))

    candidates.sort(key=lambda x: (x[0], x[1]))
    removed = 0
    initial_lcc_size = len(max(nx.weakly_connected_components(rewired), key=len))
    for _, _, u, v in candidates:
        if removed >= to_remove:
            break
        if rewired.has_edge(u, v):
            original_data = dict(rewired.get_edge_data(u, v, default={}))
            rewired.remove_edge(u, v)

            if rewired.number_of_nodes() == 0:
                rewired.add_edge(u, v, **original_data)
                continue

            current_lcc_size = len(max(nx.weakly_connected_components(rewired), key=len))
            if current_lcc_size < initial_lcc_size:
                rewired.add_edge(u, v, **original_data)
                continue

            removed += 1

    return rewired, len(added_edges), removed


def scenario_result_row(
    scenario: str,
    pre: dict[str, float],
    post: dict[str, float],
    added_edges: int,
    removed_edges: int,
    protected_hubs: int,
    removed_nodes: int,
) -> dict[str, float | int | str]:
    lcc_ratio_attack = (post["lcc_ratio"] / pre["lcc_ratio"]) if pre["lcc_ratio"] > 0 else 0.0
    eff_ratio_attack = (
        (post["global_efficiency"] / pre["global_efficiency"])
        if pre["global_efficiency"] > 0
        else 0.0
    )
    return {
        "scenario": scenario,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "protected_hubs": protected_hubs,
        "nodes_removed_attack": removed_nodes,
        "nodes_pre": pre["nodes"],
        "edges_pre": pre["edges"],
        "lcc_pre_pct": pre["lcc_ratio"] * 100.0,
        "eff_pre": pre["global_efficiency"],
        "diameter_pre": pre["diameter"],
        "nodes_post": post["nodes"],
        "edges_post": post["edges"],
        "lcc_post_pct": post["lcc_ratio"] * 100.0,
        "eff_post": post["global_efficiency"],
        "diameter_post": post["diameter"],
        "lcc_ratio_post_pre": lcc_ratio_attack,
        "eff_ratio_post_pre": eff_ratio_attack,
        "diameter_delta": post["diameter"] - pre["diameter"],
    }


def scenario_methodology(args: argparse.Namespace, fallback_time: float) -> dict:
    return {
        "common_attack_rule": (
            "El ataque elimina num_remove supernodos ordenados por grado ponderado "
            "total. En refuerzo_periferico y recableado_bypass el orden se recalcula "
            "sobre el grafo intervenido; en proteccion_hubs se excluyen del ataque "
            "los protect_top_k hubs del grafo base."
        ),
        "weighted_degree": (
            "Suma de original_edge_count en aristas entrantes y salientes; si no "
            "existe el atributo, se usa peso 1."
        ),
        "fallback_time_minutes": fallback_time,
        "efficiency": (
            "Eficiencia global dirigida ponderada por travel_time_minutes. Si "
            "efficiency_sources es menor que el numero de nodos del LCC, se estima "
            "con muestreo reproducible de fuentes."
        ),
        "scenarios": {
            "baseline": {
                "description": "Grafo L-space consolidado sin cambios.",
                "intervention": "Sin aristas agregadas, removidas ni nodos protegidos.",
            },
            "proteccion_hubs": {
                "description": "Inmuniza hubs estructurales ante el ataque.",
                "node_selection": f"Top {args.protect_top_k} por grado ponderado en el grafo base.",
                "edge_changes": "No agrega ni remueve aristas.",
                "attack_rule": (
                    "Remueve los siguientes num_remove nodos de mayor grado ponderado "
                    "que no esten en el conjunto protegido."
                ),
            },
            "refuerzo_periferico": {
                "description": "Agrega enlaces bidireccionales entre nodos perifericos.",
                "node_selection": (
                    "Calcula cercania no dirigida en el LCC; toma hasta el 25% de "
                    "menor cercania, con minimo 100 candidatos."
                ),
                "pairing_rule": (
                    "Empareja extremos opuestos de la lista periferica; descarta pares "
                    "ya adyacentes o separados por menos de 4 saltos."
                ),
                "edge_weight": (
                    "Cada arista nueva usa travel_time_minutes=fallback_time_minutes "
                    "y original_edge_count=1."
                ),
                "edge_changes": (
                    f"Agrega hasta {args.reinforcement_pairs} pares bidireccionales "
                    "sin remover aristas existentes."
                ),
            },
            "recableado_bypass": {
                "description": "Agrega bypasses dirigidos alrededor de hubs.",
                "node_selection": f"Top {args.rewire_hubs} hubs por grado ponderado en el grafo base.",
                "edge_rule": (
                    "Para un hub h, si u->h y h->v existen, u y v no son hubs, "
                    "u!=v y u->v no existe, agrega u->v."
                ),
                "edge_weight": (
                    "El peso de u->v es travel_time(u,h)+travel_time(h,v); "
                    "original_edge_count=1."
                ),
                "edge_changes": (
                    f"Agrega hasta {args.rewire_bypasses} bypasses. preserve_edge_budget="
                    f"{args.preserve_edge_budget}; si es true, remueve aristas no puente "
                    "de baja criticidad para compensar."
                ),
                "randomness": f"Orden de predecesores/sucesores aleatorizado con seed={args.seed}.",
            },
        },
    }


def main() -> int:
    args = parse_args()
    t0 = time.time()

    repo_root = Path(__file__).resolve().parents[3]
    load_env(repo_root)
    graph_path = resolve_l_graph_path(repo_root)

    output_dir = repo_root / args.output_dir
    ensure_dir(output_dir)

    print(f"Cargando L-space consolidado: {graph_path}")
    base_graph = load_l_space_graph(graph_path)
    fallback_time = infer_fallback_travel_time(base_graph)

    print(
        f"Grafo base: N={base_graph.number_of_nodes()} "
        f"E={base_graph.number_of_edges()} fallback_time={fallback_time:.3f} min"
    )

    rows: list[dict[str, float | int | str]] = []

    # Escenario base
    pre_base = core_metrics(base_graph, args.efficiency_sources, seed=args.seed + 1)
    attacked_base, removed_base = simulate_targeted_attack(base_graph, args.num_remove)
    post_base = core_metrics(attacked_base, args.efficiency_sources, seed=args.seed + 2)
    rows.append(
        scenario_result_row(
            scenario="baseline",
            pre=pre_base,
            post=post_base,
            added_edges=0,
            removed_edges=0,
            protected_hubs=0,
            removed_nodes=len(removed_base),
        )
    )
    print(
        "[baseline] "
        f"LCC post={rows[-1]['lcc_post_pct']:.2f}% "
        f"EFF ratio={rows[-1]['eff_ratio_post_pre']:.4f} "
        f"DIAM post={rows[-1]['diameter_post']}"
    )

    # Escenario 1: proteccion de hubs
    protected_hubs = set(top_nodes_by_weighted_degree(base_graph, args.protect_top_k))
    attacked_protected, removed_protected = simulate_targeted_attack(
        base_graph, args.num_remove, protected_nodes=protected_hubs
    )
    post_protected = core_metrics(attacked_protected, args.efficiency_sources, seed=args.seed + 3)
    rows.append(
        scenario_result_row(
            scenario="proteccion_hubs",
            pre=pre_base,
            post=post_protected,
            added_edges=0,
            removed_edges=0,
            protected_hubs=len(protected_hubs),
            removed_nodes=len(removed_protected),
        )
    )
    print(
        "[proteccion_hubs] "
        f"LCC post={rows[-1]['lcc_post_pct']:.2f}% "
        f"EFF ratio={rows[-1]['eff_ratio_post_pre']:.4f} "
        f"DIAM post={rows[-1]['diameter_post']}"
    )

    # Escenario 2: refuerzo periferico
    reinforced_graph, added_reinforcement = apply_peripheral_reinforcement(
        base_graph, args.reinforcement_pairs, fallback_time=fallback_time
    )
    pre_reinforced = core_metrics(reinforced_graph, args.efficiency_sources, seed=args.seed + 4)
    attacked_reinforced, removed_reinforced = simulate_targeted_attack(reinforced_graph, args.num_remove)
    post_reinforced = core_metrics(attacked_reinforced, args.efficiency_sources, seed=args.seed + 5)
    rows.append(
        scenario_result_row(
            scenario="refuerzo_periferico",
            pre=pre_reinforced,
            post=post_reinforced,
            added_edges=added_reinforcement,
            removed_edges=0,
            protected_hubs=0,
            removed_nodes=len(removed_reinforced),
        )
    )
    print(
        "[refuerzo_periferico] "
        f"LCC post={rows[-1]['lcc_post_pct']:.2f}% "
        f"EFF ratio={rows[-1]['eff_ratio_post_pre']:.4f} "
        f"DIAM post={rows[-1]['diameter_post']} "
        f"(added_edges={added_reinforcement})"
    )

    # Escenario 3: recableado con bypass
    hubs_for_rewire = top_nodes_by_weighted_degree(base_graph, args.rewire_hubs)
    rewired_graph, rewired_added, rewired_removed = apply_bypass_rewiring(
        base_graph,
        hubs=hubs_for_rewire,
        max_bypasses=args.rewire_bypasses,
        fallback_time=fallback_time,
        seed=args.seed,
        preserve_edge_budget=args.preserve_edge_budget,
    )
    pre_rewired = core_metrics(rewired_graph, args.efficiency_sources, seed=args.seed + 6)
    attacked_rewired, removed_rewired = simulate_targeted_attack(rewired_graph, args.num_remove)
    post_rewired = core_metrics(attacked_rewired, args.efficiency_sources, seed=args.seed + 7)
    rows.append(
        scenario_result_row(
            scenario="recableado_bypass",
            pre=pre_rewired,
            post=post_rewired,
            added_edges=rewired_added,
            removed_edges=rewired_removed,
            protected_hubs=0,
            removed_nodes=len(removed_rewired),
        )
    )
    print(
        "[recableado_bypass] "
        f"LCC post={rows[-1]['lcc_post_pct']:.2f}% "
        f"EFF ratio={rows[-1]['eff_ratio_post_pre']:.4f} "
        f"DIAM post={rows[-1]['diameter_post']} "
        f"(+{rewired_added}/-{rewired_removed} edges)"
    )

    df = pd.DataFrame(rows)
    base_post = df[df["scenario"] == "baseline"].iloc[0]
    df["delta_lcc_pp_vs_baseline_post"] = df["lcc_post_pct"] - base_post["lcc_post_pct"]
    df["delta_eff_pp_vs_baseline_post"] = (df["eff_post"] - base_post["eff_post"]) * 100.0
    df["delta_diameter_vs_baseline_post"] = df["diameter_post"] - base_post["diameter_post"]

    csv_path = output_dir / "intervenciones_topologicas_l_space.csv"
    df.to_csv(csv_path, index=False)

    summary = {
        "runtime_seconds": round(time.time() - t0, 2),
        "graph_path": str(graph_path),
        "parameters": {
            "num_remove": args.num_remove,
            "protect_top_k": args.protect_top_k,
            "reinforcement_pairs": args.reinforcement_pairs,
            "rewire_hubs": args.rewire_hubs,
            "rewire_bypasses": args.rewire_bypasses,
            "preserve_edge_budget": args.preserve_edge_budget,
            "efficiency_sources": args.efficiency_sources,
            "seed": args.seed,
        },
        "methodology": scenario_methodology(args, fallback_time),
        "output_csv": str(csv_path),
        "scenarios": df.to_dict(orient="records"),
    }
    summary_path = output_dir / "resumen_intervenciones_topologicas.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Analisis de intervenciones completado ===")
    print(f"Salida: {csv_path}")
    print(f"Salida: {summary_path}")
    print(f"Tiempo total: {summary['runtime_seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
