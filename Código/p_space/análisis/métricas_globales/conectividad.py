
import networkx as nx
import os
from dotenv import load_dotenv

def analizar_conectividad_p_space():
    """
    Carga el grafo P-space y calcula métricas de conectividad y básicas.
    """
    # --- 1. CARGA DE DATOS ---
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'))
    GRAPH_PATH = os.getenv("P_SPACE_GRAPH_PATH")
    
    print(f"Cargando grafo P-space desde {GRAPH_PATH}...")
    if not GRAPH_PATH or not os.path.exists(GRAPH_PATH):
        print(f"Error: El archivo del grafo no se encontró en la ruta especificada en .env: {GRAPH_PATH}")
        print("Asegúrate de haber ejecutado primero el script de construcción del grafo P-space.")
        return

    G = nx.read_gpickle(GRAPH_PATH)
    print("Grafo P-space cargado exitosamente.")

    # --- 2. CÁLCULO DE MÉTRICAS BÁSICAS Y DE CONECTIVIDAD ---
    num_nodos = G.number_of_nodes()
    num_aristas = G.number_of_edges()
    
    # Densidad del grafo
    # Para un grafo no dirigido es D = 2 * E / (V * (V - 1))
    densidad = nx.density(G)
    
    # Componentes conectados (para grafos no dirigidos)
    num_componentes_conectados = nx.number_connected_components(G)
    
    # --- 3. IMPRESIÓN DE RESULTADOS ---
    print("\n--- ANÁLISIS DE CONECTIVIDAD (P-SPACE) ---")
    print(f"Número de nodos (rutas): {num_nodos}")
    print(f"Número de aristas (trasbordos): {num_aristas}")
    print(f"Densidad del grafo: {densidad:.6f}")
    
    if num_componentes_conectados == 1:
        print("La red de rutas está completamente conectada (en un solo componente).")
    else:
        print(f"¡Atención! La red de rutas está fragmentada en {num_componentes_conectados} componentes no conectados entre sí.")
        print("Esto significa que hay grupos de rutas que no tienen ninguna parada en común con rutas de otros grupos.")

if __name__ == '__main__':
    analizar_conectividad_p_space()
