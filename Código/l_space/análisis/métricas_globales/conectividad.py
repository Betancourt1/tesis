
import networkx as nx
import os
from dotenv import load_dotenv

def analizar_conectividad():
    """
    Carga el grafo consolidado y calcula métricas de conectividad y básicas.
    """
    # --- 1. CARGA DE DATOS ---
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'))
    GRAPH_PATH = os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH")
    
    print(f"Cargando grafo desde {GRAPH_PATH}...")
    if not GRAPH_PATH or not os.path.exists(GRAPH_PATH):
        print(f"Error: El archivo del grafo no se encontró en la ruta especificada en .env: {GRAPH_PATH}")
        return

    G = nx.read_gpickle(GRAPH_PATH)
    print("Grafo cargado exitosamente.")

    # --- 2. CÁLCULO DE MÉTRICAS BÁSICAS Y DE CONECTIVIDAD ---
    num_nodos = G.number_of_nodes()
    num_aristas = G.number_of_edges()
    
    # Densidad del grafo
    # Para un grafo dirigido es D = E / (V * (V - 1))
    densidad = nx.density(G)
    
    # Componentes débilmente conectados
    # Un grafo es débilmente conectado si al reemplazar todas sus aristas dirigidas
    # por aristas no dirigidas se obtiene un grafo conectado.
    num_componentes_conectados = nx.number_weakly_connected_components(G)
    
    # --- 3. IMPRESIÓN DE RESULTADOS ---
    print("\n--- ANÁLISIS DE CONECTIVIDAD ---")
    print(f"Número de nodos (supernodos): {num_nodos}")
    print(f"Número de aristas (conexiones): {num_aristas}")
    print(f"Densidad del grafo: {densidad:.6f}")
    
    if num_componentes_conectados == 1:
        print("La red de transporte está completamente conectada (en un solo componente).")
    else:
        print(f"¡Atención! La red está fragmentada en {num_componentes_conectados} componentes no conectados entre sí.")

if __name__ == '__main__':
    analizar_conectividad()
