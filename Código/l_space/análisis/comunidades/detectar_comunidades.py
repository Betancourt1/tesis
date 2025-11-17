
import networkx as nx
import os
from networkx.algorithms import community as nx_comm
from dotenv import load_dotenv
import pickle
import sys

def detectar_comunidades():
    """
    Carga el grafo consolidado, detecta comunidades usando el método de Louvain
    con ponderación por número de rutas, y guarda un nuevo grafo GEXF
    con los nodos coloreados por comunidad.
    """
    # --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
    try:
        dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'))
        if not os.path.exists(dotenv_path):
            raise FileNotFoundError
        load_dotenv(dotenv_path=dotenv_path)
        project_root = os.path.dirname(dotenv_path)
    except FileNotFoundError:
        print("Error: No se pudo encontrar el archivo .env en la raíz del proyecto.")
        sys.exit(1)
    
    # Rutas de entrada/salida
    GRAPH_PATH = os.path.join(project_root, os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"))
    
    if not os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"):
        print(f"Error: La variable L_SPACE_CONSOLIDATED_GRAPH_PATH no está definida en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        return

    print(f"Cargando grafo desde {GRAPH_PATH}...")
    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
    print("Grafo cargado.")

    # --- 2. DETECCIÓN DE COMUNIDADES (MÉTODO DE LOUVAIN) ---
    print("Detectando comunidades con el método de Louvain...")
    
    # El método de Louvain funciona mejor en grafos no dirigidos.
    # Convertimos el grafo a no dirigido para el algoritmo de comunidad.
    # Mantenemos los atributos de las aristas (como el peso).
    G_undirected = G.to_undirected()

    # Usamos 'original_edge_count' como peso para que las comunidades se formen
    # en torno a los corredores con más rutas.
    communities = nx_comm.louvain_communities(G_undirected, weight='original_edge_count', seed=123)
    
    print(f"Se detectaron {len(communities)} comunidades.")

    # --- 3. AÑADIR ATRIBUTOS DE COMUNIDAD AL GRAFO ORIGINAL ---
    print("Asignando ID de comunidad a cada nodo en el grafo original...")
    
    # Crear un diccionario para mapear cada nodo a su ID de comunidad
    node_community_mapping = {}
    for i, community in enumerate(communities):
        for node in community:
            node_community_mapping[node] = i
            
    # Añadir el atributo 'community' al grafo dirigido original (G)
    nx.set_node_attributes(G, node_community_mapping, 'community')

    # --- 4. GUARDAR EL GRAFO CON COMUNIDADES ---
    print(f"Guardando el grafo con atributos de comunidad en {GRAPH_PATH}...")
    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    
    print("\n¡Proceso completado!")
    print("El nuevo archivo GEXF ahora contiene un atributo 'community' en cada nodo.")
    print("Puedes usar este atributo en Gephi/QGIS para colorear los nodos y visualizar las comunidades.")

if __name__ == '__main__':
    detectar_comunidades()
