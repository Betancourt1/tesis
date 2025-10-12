import pandas as pd
import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN
import json
import os

# --- CONFIGURACIÓN ---
# Distancia máxima en metros para considerar que las paradas forman parte de un clúster.
UMBRAL_DISTANCIA_METROS = 100
# Radio de la Tierra en metros
RADIO_TIERRA_METROS = 6371000

# --- RUTAS DE ARCHIVOS ---
BASE_DIR = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis"
INPUT_GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo.gexf")
OUTPUT_DIR = os.path.join(BASE_DIR, "QGIS")
OUTPUT_GRAPH_PATH = os.path.join(OUTPUT_DIR, "transporte_publico_grafo_consolidado.gexf")

def consolidar_grafo():
    """
    Carga un grafo de transporte, consolida paradas cercanas en "supernodos" usando DBSCAN,
    y genera un nuevo grafo simplificado con la información de mapeo en sus atributos.
    """
    # --- 1. CARGA DE DATOS ---
    print(f"Cargando grafo desde {INPUT_GRAPH_PATH}...")
    if not os.path.exists(INPUT_GRAPH_PATH):
        print(f"Error: El archivo del grafo no existe. Ejecuta primero 'construcción_de_grafo.py'.")
        return

    G = nx.read_gexf(INPUT_GRAPH_PATH)
    print("Grafo cargado exitosamente.")

    # Extraer datos de nodos para el clustering
    nodes_data = [
        (node, data['stop_lat'], data['stop_lon'])
        for node, data in G.nodes(data=True)
        if 'stop_lat' in data and 'stop_lon' in data
    ]
    node_ids, lats, lons = zip(*nodes_data)
    coords = pd.DataFrame({'lat': lats, 'lon': lons}, index=node_ids)

    # --- 2. AGRUPAMIENTO CON DBSCAN ---
    print("Iniciando agrupamiento de paradas con DBSCAN...")
    eps_rad = UMBRAL_DISTANCIA_METROS / RADIO_TIERRA_METROS
    coords_rad = np.radians(coords[['lat', 'lon']])
    db = DBSCAN(eps=eps_rad, min_samples=1, algorithm='ball_tree', metric='haversine').fit(coords_rad)
    
    coords['cluster_id'] = db.labels_
    print(f"Se encontraron {len(set(db.labels_))} clústeres (supernodos).")

    # --- 3. CREACIÓN DE MAPEADOS Y SUPER NODOS ---
    print("Generando mapeos y propiedades de supernodos...")
    stop_to_cluster_map = coords['cluster_id'].to_dict()

    supernodos_info = {}
    grouped_clusters = coords.groupby('cluster_id')
    for cluster_id, group in grouped_clusters:
        centroid = {
            'stop_lat': group['lat'].mean(),
            'stop_lon': group['lon'].mean()
        }
        original_stops = list(group.index)
        supernodos_info[str(cluster_id)] = {
            'centroid': centroid,
            'original_stops': original_stops,
            'stop_count': len(original_stops)
        }

    # --- 4. CONSTRUCCIÓN DEL GRAFO CONSOLIDADO ---
    print("Construyendo el nuevo grafo consolidado...")
    G_consolidado = nx.DiGraph()

    # Añadir supernodos al nuevo grafo, incluyendo la lista de paradas originales
    for cluster_id, data in supernodos_info.items():
        # Convertir lista de paradas a string para compatibilidad con GEXF
        original_stops_str = ','.join(map(str, data['original_stops']))
        G_consolidado.add_node(
            cluster_id,
            **data['centroid'],
            stop_count=data['stop_count'],
            original_stops=original_stops_str
        )

    # Agrupar aristas originales por las nuevas aristas consolidadas
    new_edges_aggregation = {}
    for u, v, data in G.edges(data=True):
        cluster_u = str(stop_to_cluster_map.get(u))
        cluster_v = str(stop_to_cluster_map.get(v))

        if cluster_u and cluster_v and cluster_u != cluster_v:
            edge_key = (cluster_u, cluster_v)
            if edge_key not in new_edges_aggregation:
                new_edges_aggregation[edge_key] = []
            new_edges_aggregation[edge_key].append(data)

    # --- 5. AGREGACIÓN DE ATRIBUTOS Y CREACIÓN DE NUEVAS ARISTAS ---
    print("Agregando atributos y creando nuevas aristas...")
    for (u, v), original_edges_data in new_edges_aggregation.items():
        valid_times = [d.get('travel_time_minutes', 0.0) for d in original_edges_data if d.get('travel_time_minutes', -1.0) >= 0]
        avg_travel_time = sum(valid_times) / len(valid_times) if valid_times else 0.0

        # Serializar los datos de las aristas originales a un string JSON
        # Esto asegura que todos los datos complejos se guarden en un solo atributo
        original_edges_json_str = json.dumps(original_edges_data)

        G_consolidado.add_edge(
            u, v,
            travel_time_minutes=avg_travel_time,
            original_edge_count=len(original_edges_data),
            original_edges_properties=original_edges_json_str
        )

    # --- 6. GUARDAR RESULTADOS ---
    print(f"Guardando grafo consolidado en {OUTPUT_GRAPH_PATH}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nx.write_gexf(G_consolidado, OUTPUT_GRAPH_PATH)

    print("\nProceso completado.")
    print(f"Nodos en grafo original: {G.number_of_nodes()}")
    print(f"Nodos en grafo consolidado: {G_consolidado.number_of_nodes()}")
    print(f"Aristas en grafo original: {G.number_of_edges()}")
    print(f"Aristas en grafo consolidado: {G_consolidado.number_of_edges()}")

if __name__ == '__main__':
    consolidar_grafo()