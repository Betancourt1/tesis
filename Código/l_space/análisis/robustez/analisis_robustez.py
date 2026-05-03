import argparse
import json
import multiprocessing
import os
import pickle
import random
import sys
import time
from functools import partial

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from dotenv import load_dotenv


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analisis de robustez del L-espacio ante ataque dirigido y fallos aleatorios."
    )
    parser.add_argument(
        "--num-remove",
        type=int,
        default=50,
        help="Numero de nodos a remover en cada simulacion.",
    )
    parser.add_argument(
        "--random-repetitions",
        type=int,
        default=30,
        help="Numero de repeticiones para fallos aleatorios. Use 0 para omitirlas.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Semilla base para fallos aleatorios reproducibles.",
    )
    parser.add_argument(
        "--random-efficiency-sources",
        type=int,
        default=128,
        help=(
            "Numero de fuentes muestreadas para estimar eficiencia dirigida en fallos "
            "aleatorios. Si es 0 o mayor que el numero de nodos, se calcula exacto."
        ),
    )
    return parser.parse_args()


def load_graph(graph_path):
    """Carga el grafo desde un archivo gpickle."""
    if not os.path.exists(graph_path):
        raise FileNotFoundError(f"No se encontro el archivo del grafo en: {graph_path}")
    with open(graph_path, "rb") as f:
        return pickle.load(f)


def _calculate_efficiency_chunk(nodes_chunk, G, weight):
    """Funcion de trabajo para calcular la eficiencia de un subconjunto de nodos."""
    total_efficiency = 0.0
    all_nodes = list(G.nodes())
    for source in nodes_chunk:
        try:
            dists = nx.single_source_dijkstra_path_length(G, source, weight=weight)
            for target in all_nodes:
                if source != target:
                    dist = dists.get(target)
                    if dist is not None and dist > 0:
                        total_efficiency += 1 / dist
        except nx.NodeNotFound:
            pass
    return total_efficiency


def calculate_parallel_directed_global_efficiency(G, weight="travel_time_minutes"):
    """Calcula la eficiencia global exacta para un grafo dirigido usando paralelizacion."""
    n = G.number_of_nodes()
    if n < 2:
        return 0.0

    nodes = list(G.nodes())
    num_cores = max(1, multiprocessing.cpu_count() - 1)
    chunk_size = int(np.ceil(n / num_cores))
    node_chunks = [nodes[i : i + chunk_size] for i in range(0, n, chunk_size)]

    with multiprocessing.Pool(processes=num_cores) as pool:
        worker_func = partial(_calculate_efficiency_chunk, G=G, weight=weight)
        chunk_efficiencies = pool.map(worker_func, node_chunks)

    total_efficiency = sum(chunk_efficiencies)
    return total_efficiency / (n * (n - 1))


def calculate_sampled_directed_global_efficiency(
    G,
    weight="travel_time_minutes",
    max_sources=128,
    seed=42,
):
    """Estima la eficiencia global dirigida con una muestra de nodos fuente."""
    n = G.number_of_nodes()
    if n < 2:
        return 0.0

    if max_sources <= 0 or max_sources >= n:
        return calculate_parallel_directed_global_efficiency(G, weight=weight)

    nodes = list(G.nodes())
    rng = random.Random(seed)
    source_nodes = rng.sample(nodes, max_sources)

    total_efficiency = 0.0
    all_nodes = list(G.nodes())
    for source in source_nodes:
        try:
            dists = nx.single_source_dijkstra_path_length(G, source, weight=weight)
        except nx.NodeNotFound:
            continue
        for target in all_nodes:
            if source == target:
                continue
            dist = dists.get(target)
            if dist is not None and dist > 0:
                total_efficiency += 1 / dist

    return total_efficiency / (len(source_nodes) * (n - 1))


def calculate_efficiency(
    G,
    mode="exact",
    weight="travel_time_minutes",
    max_sources=128,
    seed=42,
):
    if mode == "sampled":
        return calculate_sampled_directed_global_efficiency(
            G,
            weight=weight,
            max_sources=max_sources,
            seed=seed,
        )
    return calculate_parallel_directed_global_efficiency(G, weight=weight)


def simulate_failures(
    G,
    node_order,
    iterations,
    efficiency_mode="exact",
    max_efficiency_sources=128,
    seed=42,
    verbose=True,
):
    """Simula la eliminacion de nodos y calcula el impacto en la red."""
    results = []
    G_copy = G.copy()

    main_component_nodes = max(nx.weakly_connected_components(G_copy), key=len)
    G_main = G_copy.subgraph(main_component_nodes).copy()

    initial_lcc_size = len(main_component_nodes)
    if verbose:
        print("Calculando eficiencia inicial...")
    initial_efficiency = calculate_efficiency(
        G_main,
        mode=efficiency_mode,
        max_sources=max_efficiency_sources,
        seed=seed,
    )
    if verbose:
        print(f"Eficiencia inicial calculada: {initial_efficiency:.4f}")

    results.append(
        {
            "nodes_removed": 0,
            "lcc_size_ratio": 1.0,
            "global_efficiency_ratio": 1.0,
        }
    )

    for i in range(1, iterations + 1):
        start_time = time.time()
        if not G_copy.nodes() or i > len(node_order):
            break

        node_to_remove = node_order[i - 1]

        if G_copy.has_node(node_to_remove):
            G_copy.remove_node(node_to_remove)

        if G_copy.number_of_nodes() < 2:
            lcc_size = 0
            global_efficiency = 0
        else:
            main_component_nodes_after_removal = max(nx.weakly_connected_components(G_copy), key=len)
            G_main_after_removal = G_copy.subgraph(main_component_nodes_after_removal).copy()
            lcc_size = len(main_component_nodes_after_removal)
            global_efficiency = calculate_efficiency(
                G_main_after_removal,
                mode=efficiency_mode,
                max_sources=max_efficiency_sources,
                seed=seed + i,
            )

        results.append(
            {
                "nodes_removed": i,
                "lcc_size_ratio": lcc_size / initial_lcc_size if initial_lcc_size > 0 else 0,
                "global_efficiency_ratio": (
                    global_efficiency / initial_efficiency if initial_efficiency > 0 else 0
                ),
            }
        )
        end_time = time.time()
        if verbose:
            print(f"Iteracion {i}/{iterations} completada en {end_time - start_time:.2f}s")

    return pd.DataFrame(results)


def simulate_random_failures(
    G,
    iterations,
    repetitions,
    seed,
    max_efficiency_sources,
):
    """Ejecuta fallos aleatorios con varias repeticiones independientes."""
    all_nodes = list(G.nodes())
    frames = []
    for rep in range(repetitions):
        rep_seed = seed + rep
        rng = random.Random(rep_seed)
        node_order = all_nodes.copy()
        rng.shuffle(node_order)
        print(f"\n--- Fallos aleatorios L-space: repeticion {rep + 1}/{repetitions} (seed={rep_seed}) ---")
        df = simulate_failures(
            G,
            node_order,
            iterations,
            efficiency_mode="sampled",
            max_efficiency_sources=max_efficiency_sources,
            seed=rep_seed,
            verbose=False,
        )
        df.insert(0, "seed", rep_seed)
        df.insert(0, "run_id", rep + 1)
        frames.append(df)

    if not frames:
        return pd.DataFrame(
            columns=["run_id", "seed", "nodes_removed", "lcc_size_ratio", "global_efficiency_ratio"]
        )
    return pd.concat(frames, ignore_index=True)


def summarize_random_results(df):
    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby("nodes_removed", as_index=False).agg(
        repetitions=("run_id", "nunique"),
        lcc_size_ratio_mean=("lcc_size_ratio", "mean"),
        lcc_size_ratio_std=("lcc_size_ratio", "std"),
        global_efficiency_ratio_mean=("global_efficiency_ratio", "mean"),
        global_efficiency_ratio_std=("global_efficiency_ratio", "std"),
    )
    quantiles = (
        df.groupby("nodes_removed")[["lcc_size_ratio", "global_efficiency_ratio"]]
        .quantile([0.05, 0.95])
        .unstack()
    )
    quantiles.columns = [
        f"{metric}_q{int(q * 100):02d}" for metric, q in quantiles.columns.to_flat_index()
    ]
    quantiles = quantiles.reset_index()
    return grouped.merge(quantiles, on="nodes_removed", how="left")


def get_node_order_by_centrality(G, centrality_name):
    """Ordena los nodos segun una metrica de centralidad leida del grafo."""
    if centrality_name == "weighted degree":
        centrality_dict = {}
        for node, data in G.nodes(data=True):
            edge_weight = 0.0
            for _, _, edge_data in G.in_edges(node, data=True):
                edge_weight += max(1.0, float(edge_data.get("original_edge_count", 1.0)))
            for _, _, edge_data in G.out_edges(node, data=True):
                edge_weight += max(1.0, float(edge_data.get("original_edge_count", 1.0)))
            if edge_weight == 0.0:
                edge_weight = data.get("in_degree_weighted", 0) + data.get("out_degree_weighted", 0)
            centrality_dict[node] = edge_weight
    elif centrality_name in G.nodes[list(G.nodes())[0]]:
        centrality_dict = {node: data[centrality_name] for node, data in G.nodes(data=True)}
    else:
        raise ValueError(
            f"La centralidad '{centrality_name}' no se encontro como atributo en los nodos del grafo."
        )

    sorted_nodes = sorted(centrality_dict, key=centrality_dict.get, reverse=True)
    return sorted_nodes


def add_random_band(ax, random_summary, metric, label_prefix="Fallos aleatorios"):
    if random_summary.empty:
        return
    x = random_summary["nodes_removed"].to_numpy()
    y = random_summary[f"{metric}_mean"].to_numpy()
    y_low = random_summary[f"{metric}_q05"].to_numpy()
    y_high = random_summary[f"{metric}_q95"].to_numpy()
    ax.plot(x, y, label=f"{label_prefix} (media)", linestyle="--", color="black")
    ax.fill_between(x, y_low, y_high, color="black", alpha=0.12, label=f"{label_prefix} (5%-95%)")


def main():
    """Funcion principal para ejecutar el analisis de robustez."""
    args = parse_args()
    try:
        dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
        if not os.path.exists(dotenv_path):
            raise FileNotFoundError
        load_dotenv(dotenv_path=dotenv_path)
        project_root = os.path.dirname(dotenv_path)
    except FileNotFoundError:
        print("Error: No se pudo encontrar el archivo .env en la raiz del proyecto.")
        sys.exit(1)

    graph_rel = os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH")
    robustness_rel = os.getenv("L_SPACE_ROBUSTNESS_OUTPUT_DIR") or "grafos/l_space/robustez"

    if not graph_rel:
        print("Error: La variable L_SPACE_CONSOLIDATED_GRAPH_PATH no esta definida en .env")
        return

    graph_path = os.path.join(project_root, graph_rel)
    output_dir = os.path.join(project_root, robustness_rel)
    if not os.path.exists(graph_path):
        print(f"Error: No se encontro el archivo del grafo en la ruta especificada en .env: {graph_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    G = load_graph(graph_path)
    num_nodes_to_remove = min(args.num_remove, G.number_of_nodes())

    scenarios = {
        "grado": get_node_order_by_centrality(G, "weighted degree"),
    }

    results_dfs = {}
    for name, node_order in scenarios.items():
        print(f"\n--- Iniciando simulacion para: {name.upper()} ---")
        df = simulate_failures(G, node_order, num_nodes_to_remove)
        results_dfs[name] = df
        df.to_csv(os.path.join(output_dir, f"robustez_ataque_{name}.csv"), index=False)

    random_df = pd.DataFrame()
    random_summary = pd.DataFrame()
    if args.random_repetitions > 0:
        random_df = simulate_random_failures(
            G,
            iterations=num_nodes_to_remove,
            repetitions=args.random_repetitions,
            seed=args.random_seed,
            max_efficiency_sources=args.random_efficiency_sources,
        )
        random_summary = summarize_random_results(random_df)
        random_df.to_csv(
            os.path.join(output_dir, "robustez_ataque_aleatoria_repeticiones.csv"),
            index=False,
        )
        random_summary.to_csv(
            os.path.join(output_dir, "robustez_ataque_aleatoria_resumen.csv"),
            index=False,
        )

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)

    styles = {
        "grado": {"linestyle": "-", "marker": "o", "markersize": 4},
    }

    for name, df in results_dfs.items():
        ax1.plot(
            df["nodes_removed"],
            df["lcc_size_ratio"],
            label=f"Ataque por {name.capitalize()}",
            **styles[name],
        )
    add_random_band(ax1, random_summary, "lcc_size_ratio")
    ax1.set_title("Impacto en el Tamano del Componente Conectado Gigante (LCC)", fontsize=16)
    ax1.set_ylabel("Proporcion del LCC Original", fontsize=12)
    ax1.legend()

    for name, df in results_dfs.items():
        ax2.plot(
            df["nodes_removed"],
            df["global_efficiency_ratio"],
            label=f"Ataque por {name.capitalize()}",
            **styles[name],
        )
    add_random_band(ax2, random_summary, "global_efficiency_ratio")
    ax2.set_title("Impacto en la Eficiencia Global de la Red", fontsize=16)
    ax2.set_xlabel("Numero de Nodos Eliminados", fontsize=12)
    ax2.set_ylabel("Proporcion de la Eficiencia Original", fontsize=12)
    ax2.legend()

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "grafico_robustez_comparativo.png")
    plt.savefig(plot_path, dpi=300)

    summary = {
        "graph": "L-space",
        "num_nodes_to_remove": num_nodes_to_remove,
        "targeted_scenarios": list(results_dfs.keys()),
        "random_repetitions": args.random_repetitions,
        "random_seed": args.random_seed,
        "random_efficiency_sources": args.random_efficiency_sources,
        "random_efficiency_note": (
            "La eficiencia de los fallos aleatorios se estima con muestreo de fuentes; "
            "use --random-efficiency-sources 0 para calculo exacto."
        ),
        "outputs": {
            "targeted_degree": os.path.join(output_dir, "robustez_ataque_grado.csv"),
            "random_repetitions": os.path.join(output_dir, "robustez_ataque_aleatoria_repeticiones.csv"),
            "random_summary": os.path.join(output_dir, "robustez_ataque_aleatoria_resumen.csv"),
            "plot": plot_path,
        },
    }
    with open(os.path.join(output_dir, "resumen_robustez_l_space.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
