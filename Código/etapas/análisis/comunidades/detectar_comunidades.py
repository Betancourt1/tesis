
import networkx as nx
import os
from networkx.algorithms import community as nx_comm

def detectar_comunidades():
    """
    Carga el grafo consolidado, detecta comunidades usando el método de Louvain
    con ponderación por número de rutas, y guarda un nuevo grafo GEXF
    con los nodos coloreados por comunidad.
    """
    # --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
    BASE_DIR = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis"
    
    # Rutas de entrada
    GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo_consolidado.gexf")
    
    # Ruta de salida
    OUTPUT_DIR = os.path.join(BASE_DIR, "QGIS")
    OUTPUT_GRAPH_PATH = os.path.join(OUTPUT_DIR, "transporte_publico_grafo_comunidades.gexf")

    print(f"Cargando grafo desde {GRAPH_PATH}...")
    G = nx.read_gexf(GRAPH_PATH)
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
    print(f"Guardando el grafo con atributos de comunidad en {OUTPUT_GRAPH_PATH}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nx.write_gexf(G, OUTPUT_GRAPH_PATH)
    
    print("\n¡Proceso completado!")
    print("El nuevo archivo GEXF ahora contiene un atributo 'community' en cada nodo.")
    print("Puedes usar este atributo en Gephi/QGIS para colorear los nodos y visualizar las comunidades.")

if __name__ == '__main__':
    detectar_comunidades()
