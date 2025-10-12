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
OUTPUT_MAPPING_JSON_PATH = os.path.join(OUTPUT_DIR, "mapeo_consolidation.json")

def consolidar_grafo():
    """
    Carga un grafo de transporte, consolida paradas cercanas en "supernodos" usando DBSCAN,
    y genera un nuevo grafo simplificado y un archivo de mapeo.
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
    # Convertir umbral de metros a radianes para la métrica haversine
    eps_rad = UMBRAL_DISTANCIA_METROS / RADIO_TIERRA_METROS

    # Convertir coordenadas de grados a radianes
    coords_rad = np.radians(coords[['lat', 'lon']])

    # Aplicar DBSCAN
    db = DBSCAN(eps=eps_rad, min_samples=1, algorithm='ball_tree', metric='haversine').fit(coords_rad)
    
    # Añadir etiqueta de clúster a cada parada
    coords['cluster_id'] = db.labels_
    print(f"Se encontraron {len(set(db.labels_))} clústeres (supernodos).")

    # --- 3. CREACIÓN DE MAPEADOS Y SUPER NODOS ---
    print("Generando mapeos y propiedades de supernodos...")
    # Mapeo de ID de parada original a ID de clúster
    stop_to_cluster_map = coords['cluster_id'].to_dict()

    # Calcular propiedades de los supernodos (centroide y paradas contenidas)
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

    # Añadir supernodos al nuevo grafo
    for cluster_id, data in supernodos_info.items():
        G_consolidado.add_node(cluster_id, **data['centroid'], stop_count=data['stop_count'])

    # Agrupar aristas originales por las nuevas aristas consolidadas
    new_edges_aggregation = {}
    for u, v, data in G.edges(data=True):
        cluster_u = str(stop_to_cluster_map.get(u))
        cluster_v = str(stop_to_cluster_map.get(v))

        # Ignorar aristas dentro del mismo clúster (bucles)
        if cluster_u and cluster_v and cluster_u != cluster_v:
            edge_key = (cluster_u, cluster_v)
            if edge_key not in new_edges_aggregation:
                new_edges_aggregation[edge_key] = []
            new_edges_aggregation[edge_key].append(data)

    # --- 5. AGREGACIÓN DE ATRIBUTOS Y CREACIÓN DE NUEVAS ARISTAS ---
    print("Agregando atributos y creando nuevas aristas...")
    aristas_mapeadas_json = {}
    for (u, v), original_edges_data in new_edges_aggregation.items():
        # Calcular promedio de travel_time
        valid_times = [d.get('travel_time_minutes', 0.0) for d in original_edges_data if d.get('travel_time_minutes', -1.0) >= 0]
        avg_travel_time = sum(valid_times) / len(valid_times) if valid_times else 0.0

        # Añadir arista consolidada al grafo
        G_consolidado.add_edge(u, v, travel_time_minutes=avg_travel_time, original_edge_count=len(original_edges_data))

        # Guardar todas las propiedades originales para el JSON
        json_key = f"{u}_to_{v}"
        aristas_mapeadas_json[json_key] = original_edges_data

    # --- 6. GUARDAR RESULTADOS ---
    print(f"Guardando grafo consolidado en {OUTPUT_GRAPH_PATH}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nx.write_gexf(G_consolidado, OUTPUT_GRAPH_PATH)

    # Crear el objeto JSON final
    output_json = {
        "descripcion": "Mapeo de la consolidación del grafo de transporte. Contiene la información de los supernodos y las aristas originales que componen las nuevas aristas consolidadas.",
        "supernodos": supernodos_info,
        "aristas_mapeadas": aristas_mapeadas_json
    }

    print(f"Guardando mapeo de consolidación en {OUTPUT_MAPPING_JSON_PATH}...")
    with open(OUTPUT_MAPPING_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)

    print("\nProceso completado.")
    print(f"Nodos en grafo original: {G.number_of_nodes()}")
    print(f"Nodos en grafo consolidado: {G_consolidado.number_of_nodes()}")
    print(f"Aristas en grafo original: {G.number_of_edges()}")
    print(f"Aristas en grafo consolidado: {G_consolidado.number_of_edges()}")

if __name__ == '__main__':
    # Para ejecutar este script, asegúrate de tener las bibliotecas necesarias instaladas:
    # pip install pandas networkx numpy scikit-learn
    consolidar_grafo()