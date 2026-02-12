import pandas as pd
import networkx as nx
import os
import sys
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE RUTAS ---
# Encontrar la raíz del proyecto (donde se encuentra el .env) y cargar las variables
try:
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))
    if not os.path.exists(dotenv_path):
        raise FileNotFoundError
    load_dotenv(dotenv_path=dotenv_path)
    project_root = os.path.dirname(dotenv_path)
except FileNotFoundError:
    print("Error: No se pudo encontrar el archivo .env en la raíz del proyecto.")
    sys.exit(1)

# Construir rutas absolutas a partir de las variables de entorno
GTFS_DIR = os.path.join(project_root, os.getenv("GTFS_DIR"))
OUTPUT_PATH = os.path.join(project_root, os.getenv("L_SPACE_INITIAL_GRAPH_PATH"))

if not os.getenv("GTFS_DIR") or not os.getenv("L_SPACE_INITIAL_GRAPH_PATH"):
    raise ValueError("Asegúrate de que las variables GTFS_DIR y L_SPACE_INITIAL_GRAPH_PATH estén definidas en tu archivo .env")

# Cargar los archivos GTFS en DataFrames de pandas
try:
    routes_df = pd.read_csv(os.path.join(GTFS_DIR, 'routes.csv'))
    trips_df = pd.read_csv(os.path.join(GTFS_DIR, 'trips.csv'))
    stop_times_df = pd.read_csv(os.path.join(GTFS_DIR, 'stop_times_cleaned.csv'))
    stops_df = pd.read_csv(os.path.join(GTFS_DIR, 'stops.csv'))

    # Convertir columnas de tiempo a formato timedelta para poder realizar cálculos
    stop_times_df['arrival_time'] = pd.to_timedelta(stop_times_df['arrival_time'])
    stop_times_df['departure_time'] = pd.to_timedelta(stop_times_df['departure_time'])

except FileNotFoundError as e:
    print(f"Error: No se encontró el archivo CSV en la ruta especificada en .env: {e.filename}")
    raise SystemExit

# Fusionar los DataFrames
# a. Fusionar stop_times_df con trips_df en 'trip_id'
merged_df = pd.merge(stop_times_df, trips_df, on='trip_id', how='left')
# b. Fusionar el resultado con routes_df en 'route_id'
merged_df = pd.merge(merged_df, routes_df, on='route_id', how='left')
# c. Fusionar el resultado con stops_df en 'stop_id'
merged_df = pd.merge(merged_df, stops_df, on='stop_id', how='left')

# Crear un grafo dirigido vacío
G = nx.DiGraph()

# 1. Añadir todas las paradas como nodos con sus atributos geográficos y de nombre.
# Este enfoque es más limpio y eficiente que verificar la existencia de nodos en cada paso.
print("Añadiendo paradas como nodos...")
for index, stop in stops_df.iterrows():
    G.add_node(
        stop['stop_id'],
        stop_name=stop['stop_name'],
        stop_lat=stop['stop_lat'],
        stop_lon=stop['stop_lon']
    )

# 2. Añadir las aristas que conectan las paradas para cada viaje.
print("Añadiendo segmentos de viaje como aristas...")
grouped_trips = merged_df.groupby('trip_id')

for trip_id, trip_data in grouped_trips:
    # Ordenar las paradas por su secuencia en el viaje
    trip_data_sorted = trip_data.sort_values(by='stop_sequence')

    # Extraer la lista de IDs de parada y el ID de la ruta
    stops_in_trip = trip_data_sorted['stop_id'].tolist()
    route_id = trip_data_sorted['route_id'].iloc[0]  # Es el mismo para todo el viaje

    # Crear aristas entre paradas consecutivas
    for i in range(len(stops_in_trip) - 1):
        from_stop_id = stops_in_trip[i]
        to_stop_id = stops_in_trip[i+1]

        # Obtener los datos de las paradas para calcular el tiempo de viaje
        from_stop_data = trip_data_sorted.iloc[i]
        to_stop_data = trip_data_sorted.iloc[i+1]

        # Calcular el tiempo de viaje en minutos. Si los datos de tiempo no están disponibles,
        # se asigna un valor por defecto.
        travel_time_minutes = -1.0  # Valor por defecto en caso de datos faltantes
        if pd.notna(from_stop_data['departure_time']) and pd.notna(to_stop_data['arrival_time']):
            time_diff = to_stop_data['arrival_time'] - from_stop_data['departure_time']
            travel_time_minutes = time_diff.total_seconds() / 60

        # Los atributos del viaje (trip_id, route_id) y el tiempo de viaje pertenecen a la arista (la conexión)
        G.add_edge(
            from_stop_id,
            to_stop_id,
            trip_id=trip_id,
            route_id=route_id,
            travel_time_minutes=travel_time_minutes
        )

# Imprimir el número de nodos y aristas en el grafo G
print(f"\nGrafo construido.")
print(f"Número de nodos (paradas) antes de la limpieza: {G.number_of_nodes()}")
print(f"Número de aristas (segmentos de viaje): {G.number_of_edges()}")

# 3. Eliminación de nodos aislados
# Un nodo aislado es aquel que no tiene aristas de entrada ni de salida (grado total cero).
# Estos nodos no aportan información sobre las conexiones en la red.
isolated_nodes = [node for node, degree in G.degree() if degree == 0]
G.remove_nodes_from(isolated_nodes)
print(f"Se eliminaron {len(isolated_nodes)} nodos aislados (grado cero).")
print(f"Número de nodos (paradas) final: {G.number_of_nodes()}")

# Ejemplo de cómo acceder a los datos de un nodo
if G.number_of_nodes() > 0:
    sample_node = list(G.nodes())[0]
    print(f"\nDatos del nodo de ejemplo '{sample_node}': {G.nodes[sample_node]}")

# Ejemplo de cómo acceder a los datos de una arista
if G.number_of_edges() > 0:
    sample_edge = list(G.edges(data=True))[0]
    print(f"\nDatos de la arista de ejemplo: De '{sample_edge[0]}' a '{sample_edge[1]}' -> {sample_edge[2]}")

# Asegurarse de que el directorio de salida exista
output_dir = os.path.dirname(OUTPUT_PATH)
os.makedirs(output_dir, exist_ok=True)

# Exportar el grafo a formato GEXF, que Gephi puede importar.
try:
    # Limpiar atributos si es necesario (ejemplo: convertir tipos no estándar a string)
    for node, data in G.nodes(data=True):
        for key, value in data.items():
            if not isinstance(value, (str, int, float, bool)):
                G.nodes[node][key] = str(value)

    for u, v, data in G.edges(data=True):
        for key, value in data.items():
            if not isinstance(value, (str, int, float, bool)):
                G.edges[u, v][key] = str(value)

    nx.write_gexf(G, OUTPUT_PATH)
    print(f"\nGrafo exportado exitosamente como '{OUTPUT_PATH}'.")
    print("Puedes importar este archivo directamente en Gephi.")
except NameError:
    print("Error: El grafo 'G' no fue encontrado. Asegúrate de ejecutar la celda anterior primero.")
except Exception as e:
    print(f"Ocurrió un error al exportar el grafo: {e}")
