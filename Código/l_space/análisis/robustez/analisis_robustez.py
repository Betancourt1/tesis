import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import multiprocessing
from functools import partial
import time

def load_graph(gexf_path):
    """Carga el grafo desde un archivo GEXF."""
    if not os.path.exists(gexf_path):
        raise FileNotFoundError(f"No se encontró el archivo del grafo en: {gexf_path}")
    return nx.read_gexf(gexf_path)

def calculate_lcc_size(G):
    """Calcula el tamaño del componente conectado más grande (LCC) para grafos dirigidos."""
    if G.number_of_nodes() == 0:
        return 0
    largest_cc = max(nx.weakly_connected_components(G), key=len)
    return len(largest_cc)

def _calculate_efficiency_chunk(nodes_chunk, G, weight):
    """Función de trabajo para calcular la eficiencia de un subconjunto de nodos."""
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

def calculate_parallel_directed_global_efficiency(G, weight='travel_time_minutes'):
    """Calcula la eficiencia global para un grafo dirigido usando paralelización."""
    n = G.number_of_nodes()
    if n < 2:
        return 0.0

    nodes = list(G.nodes())
    num_cores = max(1, multiprocessing.cpu_count() - 1)
    chunk_size = int(np.ceil(n / num_cores))
    node_chunks = [nodes[i:i + chunk_size] for i in range(0, n, chunk_size)]
    
    with multiprocessing.Pool(processes=num_cores) as pool:
        worker_func = partial(_calculate_efficiency_chunk, G=G, weight=weight)
        chunk_efficiencies = pool.map(worker_func, node_chunks)

    total_efficiency = sum(chunk_efficiencies)
    return total_efficiency / (n * (n - 1))

def simulate_failures(G, node_order, iterations):
    """Simula la eliminación de nodos y calcula el impacto en la red."""
    results = []
    G_copy = G.copy()
    
    main_component_nodes = max(nx.weakly_connected_components(G_copy), key=len)
    G_main = G_copy.subgraph(main_component_nodes).copy() # Crear una copia explícita
    
    initial_lcc_size = len(main_component_nodes)
    print("Calculando eficiencia inicial...")
    initial_efficiency = calculate_parallel_directed_global_efficiency(G_main)
    print(f"Eficiencia inicial calculada: {initial_efficiency:.4f}")

    results.append({
        'nodes_removed': 0,
        'lcc_size_ratio': 1.0,
        'global_efficiency_ratio': 1.0
    })
    
    for i in range(1, iterations + 1):
        start_time = time.time()
        if not G_copy.nodes() or i > len(node_order):
            break
            
        node_to_remove = node_order[i-1]
        
        if G_copy.has_node(node_to_remove):
            G_copy.remove_node(node_to_remove)
        
        if G_copy.number_of_nodes() < 2:
            lcc_size = 0
            global_efficiency = 0
        else:
            main_component_nodes_after_removal = max(nx.weakly_connected_components(G_copy), key=len)
            G_main_after_removal = G_copy.subgraph(main_component_nodes_after_removal).copy() # Crear una copia explícita
            lcc_size = len(main_component_nodes_after_removal)
            global_efficiency = calculate_parallel_directed_global_efficiency(G_main_after_removal)

        results.append({
            'nodes_removed': i,
            'lcc_size_ratio': lcc_size / initial_lcc_size if initial_lcc_size > 0 else 0,
            'global_efficiency_ratio': global_efficiency / initial_efficiency if initial_efficiency > 0 else 0
        })
        end_time = time.time()
        print(f"Iteración {i}/{iterations} completada en {end_time - start_time:.2f}s")
        
    return pd.DataFrame(results)

def get_node_order_by_centrality(G, centrality_name):
    """Ordena los nodos según una métrica de centralidad leída del grafo."""
    if centrality_name == 'weighted degree':
        centrality_dict = {node: data.get('in_degree_weighted', 0) + data.get('out_degree_weighted', 0) 
                           for node, data in G.nodes(data=True)}
    elif centrality_name in G.nodes[list(G.nodes())[0]]:
        centrality_dict = {node: data[centrality_name] for node, data in G.nodes(data=True)}
    else:
        raise ValueError(f"La centralidad '{centrality_name}' no se encontró como atributo en los nodos del grafo.")

    sorted_nodes = sorted(centrality_dict, key=centrality_dict.get, reverse=True)
    return sorted_nodes

def main():
    """Función principal para ejecutar el análisis de robustez."""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gexf_path = os.path.normpath(os.path.join(script_dir, '..', '..', '..', '..', 'QGIS', 'transporte_publico_grafo_enriquecido.gexf'))
    output_dir = os.path.join(script_dir, 'resultados_robustez')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    G = load_graph(gexf_path)
    
    num_nodes_to_remove = int(G.number_of_nodes() * 0.05)

    scenarios = {
        'aleatoria': np.random.permutation(list(G.nodes())),
        'grado': get_node_order_by_centrality(G, 'weighted degree'),
        'intermediacion': get_node_order_by_centrality(G, 'betweenness'),
        'cercania': get_node_order_by_centrality(G, 'closeness')
    }

    results_dfs = {}
    for name, node_order in scenarios.items():
        print(f"\n--- Iniciando simulación para: {name.upper()} ---")
        df = simulate_failures(G, node_order, num_nodes_to_remove)
        results_dfs[name] = df
        df.to_csv(os.path.join(output_dir, f'robustez_ataque_{name}.csv'), index=False)

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)
    
    styles = {
        'aleatoria': {'linestyle': '--', 'color': 'black', 'marker': None},
        'grado': {'linestyle': '-', 'marker': 'o', 'markersize': 4},
        'intermediacion': {'linestyle': '-.', 'marker': 'x', 'markersize': 5},
        'cercania': {'linestyle': ':', 'marker': 's', 'markersize': 4}
    }

    # LCC Size
    for name, df in results_dfs.items():
        ax1.plot(df['nodes_removed'], df['lcc_size_ratio'], label=f'Ataque por {name.capitalize()}', **styles[name])
    ax1.set_title('Impacto en el Tamaño del Componente Conectado Gigante (LCC)', fontsize=16)
    ax1.set_ylabel('Proporción del LCC Original', fontsize=12)
    ax1.legend()
    
    # Global Efficiency
    for name, df in results_dfs.items():
        ax2.plot(df['nodes_removed'], df['global_efficiency_ratio'], label=f'Ataque por {name.capitalize()}', **styles[name])
    ax2.set_title('Impacto en la Eficiencia Global de la Red', fontsize=16)
    ax2.set_xlabel('Número de Nodos Eliminados', fontsize=12)
    ax2.set_ylabel('Proporción de la Eficiencia Original', fontsize=12)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'grafico_robustez_comparativo.png'), dpi=300)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
