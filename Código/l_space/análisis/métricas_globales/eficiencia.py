
import networkx as nx
import os
import numpy as np
from dotenv import load_dotenv
import pickle
import sys

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


def construir_grafo_fisico_no_dirigido(G):
    """
    Construye una version no dirigida del grafo usando longitud fisica
    Haversine entre centroides de supernodos como peso de cada arista.
    Si existen aristas paralelas en sentidos opuestos, conserva la longitud
    fisica menor para representar el tramo mas directo observado.
    """
    H = nx.Graph()
    for nodo, atributos in G.nodes(data=True):
        H.add_node(nodo, **atributos)

    for u, v in G.edges():
        lat1 = G.nodes[u].get('stop_lat')
        lon1 = G.nodes[u].get('stop_lon')
        lat2 = G.nodes[v].get('stop_lat')
        lon2 = G.nodes[v].get('stop_lon')
        if None in (lat1, lon1, lat2, lon2):
            continue

        distancia = haversine(float(lat1), float(lon1), float(lat2), float(lon2))
        if distancia <= 0:
            continue

        if H.has_edge(u, v):
            H[u][v]['physical_distance_meters'] = min(
                H[u][v]['physical_distance_meters'],
                distancia,
            )
        else:
            H.add_edge(u, v, physical_distance_meters=distancia)

    return H


def calcular_indice_desvio_promedio(G):
    """
    Calcula el Detour Index geometrico promedio en el componente principal.
    El numerador es la longitud fisica del camino minimo en la red; el
    denominador es la distancia Haversine directa entre los dos supernodos.
    """
    nodos = list(G.nodes())
    indice = {nodo: i for i, nodo in enumerate(nodos)}
    suma = 0.0
    pares_validos = 0

    for i, origen in enumerate(nodos):
        distancias_red = nx.single_source_dijkstra_path_length(
            G,
            origen,
            weight='physical_distance_meters',
        )
        lat1 = G.nodes[origen].get('stop_lat')
        lon1 = G.nodes[origen].get('stop_lon')

        for destino, distancia_red in distancias_red.items():
            if indice[destino] <= i:
                continue

            lat2 = G.nodes[destino].get('stop_lat')
            lon2 = G.nodes[destino].get('stop_lon')
            if None in (lat1, lon1, lat2, lon2):
                continue

            distancia_directa = haversine(
                float(lat1),
                float(lon1),
                float(lat2),
                float(lon2),
            )
            if distancia_directa <= 0:
                continue

            suma += distancia_red / distancia_directa
            pares_validos += 1

    if pares_validos == 0:
        return None, 0
    return suma / pares_validos, pares_validos

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

    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
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
    # Compara longitud física del camino mínimo en la red con la distancia
    # Haversine directa. No usa tiempos de viaje, para mantener la
    # interpretación geométrica del índice.
    print("\nCalculando el Índice de Desvío (Detour Index)... (puede tardar)")
    S_fisico = construir_grafo_fisico_no_dirigido(S)
    if not nx.is_connected(S_fisico):
        componente_principal = max(nx.connected_components(S_fisico), key=len)
        S_fisico = S_fisico.subgraph(componente_principal).copy()

    avg_detour, pares_validos = calcular_indice_desvio_promedio(S_fisico)
    if avg_detour is not None:
        print(f"Índice de Desvío Promedio: {avg_detour:.2f}")
        print(f"Pares evaluados: {pares_validos:,}")
        print("Un valor de 1 es un recorrido físicamente directo. Valores más altos indican rutas más indirectas.")
    else:
        print("No se pudo calcular el índice de desvío.")

if __name__ == '__main__':
    analizar_eficiencia()
