import networkx as nx
import os
import pandas as pd
from dotenv import load_dotenv
import pickle
import sys

def calcular_centralidades_y_enriquecer():
    """
    Carga el grafo consolidado, calcula varias métricas de centralidad y
    las añade directamente como atributos a los nodos del grafo.
    El grafo modificado se guarda sobrescribiendo el archivo original.
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

    # --- 2. CÁLCULO DE CENTRALIDADES ---
    print("Calculando centralidades... (esto puede tardar)")

    # a) Centralidad de Grado (Ponderada por número de rutas originales)
    degree_in = dict(G.in_degree(weight='original_edge_count'))
    degree_out = dict(G.out_degree(weight='original_edge_count'))

    # b) Centralidad de Intermediación (Ponderada por tiempo de viaje)
    betweenness = nx.betweenness_centrality(G, weight='travel_time_minutes', normalized=True)

    # c) Centralidad de Cercanía (usa el tiempo de viaje como 'distancia')
    # NetworkX calcula cercanía entrante en grafos dirigidos. Para interpretar
    # la métrica como accesibilidad desde el nodo hacia el resto de la red, se
    # calcula sobre el grafo reverso y se conserva el resultado como "closeness".
    closeness_out = nx.closeness_centrality(G.reverse(copy=False), distance='travel_time_minutes')
    closeness_in = nx.closeness_centrality(G, distance='travel_time_minutes')

    # d) Centralidad de Eigenvector (Ponderada por número de rutas originales)
    try:
        eigenvector = nx.eigenvector_centrality(G, weight='original_edge_count', max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        print("La centralidad de Eigenvector no convergió. Se omitirá y asignará 0.")
        eigenvector = {node: 0.0 for node in G.nodes()}

    print("Cálculos completados.")

    # --- 3. AÑADIR ATRIBUTOS AL GRAFO ---
    print("Añadiendo atributos de centralidad a los nodos del grafo...")
    nx.set_node_attributes(G, degree_in, name='in_degree_weighted')
    nx.set_node_attributes(G, degree_out, name='out_degree_weighted')
    nx.set_node_attributes(G, betweenness, name='betweenness')
    nx.set_node_attributes(G, closeness_out, name='closeness')
    nx.set_node_attributes(G, closeness_out, name='closeness_out')
    nx.set_node_attributes(G, closeness_in, name='closeness_in')
    nx.set_node_attributes(G, eigenvector, name='eigenvector')
    print("Atributos añadidos correctamente.")

    # --- 4. GUARDAR EL GRAFO ENRIQUECIDO ---
    print(f"Guardando el grafo enriquecido en {GRAPH_PATH} (sobrescribiendo)...")
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    print("¡Proceso completado!")

    # --- 5. MOSTRAR TOP 10 DE CADA MÉTRICA ---
    print("\n--- TOP 10 NODOS POR CENTRALIDAD ---")
    # Crear un DataFrame para el análisis a partir de los atributos del grafo
    node_data = {node: data for node, data in G.nodes(data=True)}
    df = pd.DataFrame.from_dict(node_data, orient='index')
    
    for metrica in ['in_degree_weighted', 'out_degree_weighted', 'betweenness', 'closeness', 'closeness_in', 'eigenvector']:
        if metrica in df.columns:
            print(f"\n--- Top 10 por: {metrica} ---")
            top_10 = df.nlargest(10, metrica)
            for index, row in top_10.iterrows():
                # Use .get() for lat/lon to avoid errors if they are missing
                lat = row.get('stop_lat', 'N/A')
                lon = row.get('stop_lon', 'N/A')
                if isinstance(lat, str) or isinstance(lon, str):
                    print(f"  - Nodo {index}: {row[metrica]:.4f}")
                else:
                    print(f"  - Nodo {index} (Lat: {lat:.4f}, Lon: {lon:.4f}): {row[metrica]:.4f}")
        else:
            print(f"\n--- Métrica '{metrica}' no encontrada en el grafo ---")


if __name__ == '__main__':
    calcular_centralidades_y_enriquecer()
