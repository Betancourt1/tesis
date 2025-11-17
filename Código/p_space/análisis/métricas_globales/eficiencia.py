
import networkx as nx
import os
from dotenv import load_dotenv

def analizar_eficiencia_p_space():
    """
    Carga el grafo P-space y calcula métricas de eficiencia como el diámetro
    y la longitud promedio del camino más corto (en número de trasbordos).
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
    print("Grafo P-space cargado.")

    # --- 2. PREPARACIÓN DEL GRAFO ---
    # Usaremos el componente conectado más grande para el análisis.
    componentes = sorted(nx.connected_components(G), key=len, reverse=True)
    if not componentes:
        print("El grafo no tiene componentes, no se puede analizar.")
        return
        
    largest_cc_nodes = componentes[0]
    S = G.subgraph(largest_cc_nodes)
    print(f"Análisis realizado sobre el componente conectado más grande ({S.number_of_nodes()} rutas).")

    # --- 3. CÁLCULO DE MÉTRICAS DE EFICIENCIA ---
    print("\n--- ANÁLISIS DE EFICIENCIA DE LA RED (P-SPACE) ---")
    
    # Diámetro y Longitud Promedio del Camino Más Corto (no ponderado)
    try:
        if nx.is_connected(S):
            # Diámetro: La mayor distancia entre dos rutas en la red.
            diametro = nx.diameter(S)
            print(f"Diámetro de la red de rutas (máximo número de trasbordos): {diametro}")

            # Longitud promedio del camino más corto: El número promedio de trasbordos
            # necesarios para ir de una ruta cualquiera a otra.
            avg_shortest_path = nx.average_shortest_path_length(S)
            print(f"Longitud promedio del camino más corto (trasbordos promedio): {avg_shortest_path:.2f}")
        else:
            # Este caso no debería ocurrir si S es el componente conectado más grande
            print("El subgrafo no es conexo, no se pueden calcular las métricas.")

    except nx.NetworkXError as e:
        print(f"No se pudieron calcular las métricas de camino: {e}.")

    # Eficiencia Global: Mide qué tan eficientemente se intercambia información en la red.
    # Se relaciona con la inversa de las longitudes de los caminos más cortos.
    try:
        global_efficiency = nx.global_efficiency(S)
        print(f"Eficiencia global de la red de rutas: {global_efficiency:.4f}")
    except nx.NetworkXError as e:
        print(f"No se pudo calcular la eficiencia global: {e}")


if __name__ == '__main__':
    analizar_eficiencia_p_space()
