
import networkx as nx
import os
from networkx.algorithms import community as nx_comm
from dotenv import load_dotenv
import pickle
import sys

def detectar_comunidades_p_space():
    """
    Carga el grafo P-space, detecta comunidades usando el método de Louvain
    y guarda un nuevo grafo GEXF con los nodos coloreados por comunidad.
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

    GRAPH_PATH = os.path.join(project_root, os.getenv("P_SPACE_GRAPH_PATH"))

    print(f"Cargando grafo P-space desde {GRAPH_PATH}...")
    try:
        with open(GRAPH_PATH, "rb") as f:
            G = pickle.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo del grafo en {GRAPH_PATH}.")
        print("Asegúrate de haber ejecutado primero el script de cálculo de centralidades para P-space.")
        return
    print("Grafo cargado.")

    # --- 2. DETECCIÓN DE COMUNIDADES (MÉTODO DE LOUVAIN) ---
    print("Detectando comunidades de rutas con el método de Louvain...")
    
    # El método de Louvain funciona mejor en grafos no dirigidos.
    # El grafo P-space ya es no dirigido.
    communities = nx_comm.louvain_communities(G, seed=123)
    
    print(f"Se detectaron {len(communities)} comunidades de rutas.")

    # --- 3. AÑADIR ATRIBUTOS DE COMUNIDAD AL GRAFO ---
    print("Asignando ID de comunidad a cada ruta (nodo)...")
    
    # Crear un diccionario para mapear cada nodo a su ID de comunidad
    node_community_mapping = {}
    for i, community in enumerate(communities):
        for node in community:
            node_community_mapping[node] = i
            
    # Añadir el atributo 'community' al grafo
    nx.set_node_attributes(G, node_community_mapping, 'community')

    # --- 4. GUARDAR EL GRAFO CON COMUNIDADES ---
    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    print(f"Guardando el grafo P-space con atributos de comunidad en {GRAPH_PATH} (sobrescribiendo)...")
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    
    print("\n¡Proceso completado!")
    print("El nuevo archivo GEXF ahora contiene un atributo 'community' en cada nodo (ruta).")
    print("Puedes usar este atributo en Gephi para colorear las rutas y visualizar las comunidades.")

if __name__ == '__main__':
    detectar_comunidades_p_space()
