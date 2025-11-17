
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import time
from dotenv import load_dotenv

def load_graph(graph_path):
    """Carga el grafo desde un archivo gpickle."""
    if not os.path.exists(graph_path):
        raise FileNotFoundError(f"No se encontró el archivo del grafo en: {graph_path}")
    # El grafo P-space es no dirigido
    return nx.read_gpickle(graph_path)

def calculate_lcc_size(G):
    """Calcula el tamaño del componente conectado más grande (LCC) para grafos no dirigidos."""
    if G.number_of_nodes() == 0:
        return 0
    largest_cc = max(nx.connected_components(G), key=len)
    return len(largest_cc)

def simulate_failures(G, node_order, iterations):
    """Simula la eliminación de nodos y calcula el impacto en la red P-space."""
    results = []
    G_copy = G.copy()
    
    initial_lcc_size = calculate_lcc_size(G_copy)
    print("Calculando eficiencia inicial...")
    initial_efficiency = nx.global_efficiency(G_copy)
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
            lcc_size = calculate_lcc_size(G_copy)
            # Usamos la eficiencia global para grafos no dirigidos
            global_efficiency = nx.global_efficiency(G_copy)

        results.append({
            'nodes_removed': i,
            'lcc_size_ratio': lcc_size / initial_lcc_size if initial_lcc_size > 0 else 0,
            'global_efficiency_ratio': global_efficiency / initial_efficiency if initial_efficiency > 0 else 0
        })
        end_time = time.time()
        print(f"Iteración {i}/{iterations} (Ruta '{node_to_remove}' eliminada) completada en {end_time - start_time:.2f}s")
        
    return pd.DataFrame(results)

def get_node_order_by_centrality(G, centrality_name):
    """Ordena las rutas (nodos) según una métrica de centralidad."""
    try:
        centrality_dict = nx.get_node_attributes(G, centrality_name)
        if not centrality_dict:
             raise KeyError
    except KeyError:
        raise ValueError(f"La centralidad '{centrality_name}' no se encontró como atributo en los nodos del grafo.")

    sorted_nodes = sorted(centrality_dict, key=centrality_dict.get, reverse=True)
    return sorted_nodes

def main():
    """Función principal para ejecutar el análisis de robustez en P-space."""
    try:
        dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'))
        if not os.path.exists(dotenv_path):
            raise FileNotFoundError
        load_dotenv(dotenv_path=dotenv_path)
        project_root = os.path.dirname(dotenv_path)
    except FileNotFoundError:
        print("Error: No se pudo encontrar el archivo .env en la raíz del proyecto.")
        sys.exit(1)
    
    GRAPH_PATH = os.path.join(project_root, os.getenv("P_SPACE_GRAPH_PATH"))
    OUTPUT_DIR = os.path.join(project_root, os.getenv("P_SPACE_ROBUSTNESS_OUTPUT_DIR"))

    if not os.getenv("P_SPACE_GRAPH_PATH"):
        print(f"Error: La variable P_SPACE_GRAPH_PATH no está definida en .env")
        return
    if not os.getenv("P_SPACE_ROBUSTNESS_OUTPUT_DIR"):
        print("Error: La variable P_SPACE_ROBUSTNESS_OUTPUT_DIR no está definida en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    G = load_graph(GRAPH_PATH)
    
    # Atacar un % del total de rutas
    num_nodes_to_remove = int(G.number_of_nodes() * 0.20) # Aumentamos a 20% para ver mejor el efecto

    scenarios = {
        'aleatoria': list(np.random.permutation(list(G.nodes()))),
        'grado': get_node_order_by_centrality(G, 'degree'),
        'intermediacion': get_node_order_by_centrality(G, 'betweenness'),
        'cercania': get_node_order_by_centrality(G, 'closeness')
    }

    results_dfs = {}
    for name, node_order in scenarios.items():
        print(f"\n--- Iniciando simulación para P-space: {name.upper()} ---")
        df = simulate_failures(G, node_order, num_nodes_to_remove)
        results_dfs[name] = df
        df.to_csv(os.path.join(OUTPUT_DIR, f'robustez_p_space_ataque_{name}.csv'), index=False)

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
    ax1.set_title('Impacto en el LCC (P-space)', fontsize=16)
    ax1.set_ylabel('Proporción del LCC Original', fontsize=12)
    ax1.legend()
    
    # Global Efficiency
    for name, df in results_dfs.items():
        ax2.plot(df['nodes_removed'], df['global_efficiency_ratio'], label=f'Ataque por {name.capitalize()}', **styles[name])
    ax2.set_title('Impacto en la Eficiencia Global (P-space)', fontsize=16)
    ax2.set_xlabel('Número de Rutas Eliminadas', fontsize=12)
    ax2.set_ylabel('Proporción de la Eficiencia Original', fontsize=12)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_robustez_p_space_comparativo.png'), dpi=300)
    print(f"\nGráfico de robustez guardado en {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
