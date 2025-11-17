
import networkx as nx
import os
from networkx.algorithms import community as nx_comm

def detectar_comunidades_p_space():
    """
    Carga el grafo P-space, detecta comunidades usando el método de Louvain
    y guarda un nuevo grafo GEXF con los nodos coloreados por comunidad.
    """
    # --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
    BASE_DIR = '.'
    INPUT_GRAPH_PATH = os.path.join(BASE_DIR, "out", "p_space", "transporte_publico_grafo_p_space_centralidades.gexf")
    OUTPUT_GRAPH_PATH = os.path.join(BASE_DIR, "out", "p_space", "transporte_publico_grafo_p_space_comunidades.gexf")

    print(f"Cargando grafo P-space desde {INPUT_GRAPH_PATH}...")
    try:
        G = nx.read_gexf(INPUT_GRAPH_PATH)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo del grafo en {INPUT_GRAPH_PATH}.")
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
    os.makedirs(os.path.dirname(OUTPUT_GRAPH_PATH), exist_ok=True)
    print(f"Guardando el grafo P-space con atributos de comunidad en {OUTPUT_GRAPH_PATH}...")
    nx.write_gexf(G, OUTPUT_GRAPH_PATH)
    
    print("\n¡Proceso completado!")
    print("El nuevo archivo GEXF ahora contiene un atributo 'community' en cada nodo (ruta).")
    print("Puedes usar este atributo en Gephi para colorear las rutas y visualizar las comunidades.")

if __name__ == '__main__':
    detectar_comunidades_p_space()
