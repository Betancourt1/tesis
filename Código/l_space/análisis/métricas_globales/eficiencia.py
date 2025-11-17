
import networkx as nx
import os
import numpy as np
import random
from dotenv import load_dotenv

def haversine(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia haversine entre dos puntos en la Tierra.
    """
    R = 6371000  # Radio de la Tierra en metros
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c

def analizar_eficiencia():
    """
    Carga el grafo y calcula métricas de eficiencia como el diámetro,
    la longitud promedio del camino más corto y el índice de desvío.
    """
    # --- 1. CARGA DE DATOS ---
    try:
        dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'))
        if not os.path.exists(dotenv_path):
            raise FileNotFoundError
        load_dotenv(dotenv_path=dotenv_path)
        project_root = os.path.dirname(dotenv_path)
    except FileNotFoundError:
        print("Error: No se pudo encontrar el archivo .env en la raíz del proyecto.")
        sys.exit(1)
        
    GRAPH_PATH = os.path.join(project_root, os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"))
    
    print(f"Cargando grafo desde {GRAPH_PATH}...")
    if not os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"):
        print(f"Error: La variable L_SPACE_CONSOLIDATED_GRAPH_PATH no está definida en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: El archivo del grafo no se encontró en la ruta especificada en .env: {GRAPH_PATH}")
        return

    G = nx.read_gpickle(GRAPH_PATH)
    print("Grafo cargado.")

    # --- 2. PREPARACIÓN DEL GRAFO ---
    # Para métricas como diámetro y camino más corto, necesitamos un grafo fuertemente conectado.
    # Usaremos el componente débilmente conectado más grande para el análisis.
    componentes = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
    if not componentes:
        print("El grafo no tiene componentes, no se puede analizar.")
        return
        
    largest_cc_nodes = componentes[0]
    S = G.subgraph(largest_cc_nodes).copy()
    print(f"Análisis realizado sobre el componente conectado más grande ({S.number_of_nodes()} nodos).")

    # --- 3. CÁLCULO DE MÉTRICAS DE EFICIENCIA ---
    print("\n--- ANÁLISIS DE EFICIENCIA DE LA RED ---")
    
    # Diámetro y Longitud Promedio del Camino Más Corto (usando 'travel_time_minutes' como peso)
    # Estas métricas pueden ser computacionalmente intensivas.
    try:
        # Usamos un subgrafo no dirigido para asegurar la conectividad para el diámetro
        G_undirected = S.to_undirected()
        if nx.is_connected(G_undirected):
            diametro = nx.diameter(G_undirected)
            print(f"Diámetro (en saltos/trasbordos): {diametro}")
        else:
            print("El subgrafo más grande no es conexo, no se puede calcular el diámetro.")

        # Para el camino más corto, usamos el grafo dirigido con pesos de tiempo
        avg_shortest_path = nx.average_shortest_path_length(S, weight='travel_time_minutes')
        print(f"Longitud promedio del camino más corto (en minutos): {avg_shortest_path:.2f}")

    except nx.NetworkXError as e:
        print(f"No se pudieron calcular las métricas de camino: {e}. El grafo puede no ser fuertemente conectado.")

    # Índice de Desvío (Detour Index)
    # Compara la distancia real en la red con la distancia en línea recta.
    # Se calcula sobre una muestra de pares de nodos para eficiencia.
    print("\nCalculando el Índice de Desvío (Detour Index)... (puede tardar)")
    detour_ratios = []
    nodos_muestra = random.sample(list(S.nodes()), min(100, S.number_of_nodes()))

    for u in nodos_muestra:
        for v in nodos_muestra:
            if u == v or not nx.has_path(S, u, v):
                continue

            # Distancia en la red (camino más corto por tiempo)
            network_dist = nx.shortest_path_length(S, source=u, target=v, weight='travel_time_minutes')

            # Distancia en línea recta (Haversine)
            lat1, lon1 = S.nodes[u]['stop_lat'], S.nodes[u]['stop_lon']
            lat2, lon2 = S.nodes[v]['stop_lat'], S.nodes[v]['stop_lon']
            straight_dist_meters = haversine(lat1, lon1, lat2, lon2)
            
            # Asumimos una velocidad promedio para convertir distancia a tiempo (ej. 20 km/h = 333 m/min)
            straight_dist_time = straight_dist_meters / 333 

            if straight_dist_time > 0:
                detour_ratios.append(network_dist / straight_dist_time)

    if detour_ratios:
        avg_detour = np.mean(detour_ratios)
        print(f"Índice de Desvío Promedio: {avg_detour:.2f}")
        print("Un valor de 1 es un viaje perfectamente directo. Valores más altos indican rutas más indirectas.")
    else:
        print("No se pudo calcular el índice de desvío.")

if __name__ == '__main__':
    analizar_eficiencia()
