import pandas as pd
import networkx as nx
import os

# Definir la ruta base a la carpeta de datos
# Se recomienda usar rutas relativas o variables de entorno para mayor portabilidad
BASE_PATH = r'C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis\Datasets\gtfs_amg_20240312\Datos'

# Cargar los archivos GTFS en DataFrames de pandas
try:
    routes_df = pd.read_csv(os.path.join(BASE_PATH, 'routes.csv'))
    trips_df = pd.read_csv(os.path.join(BASE_PATH, 'trips.csv'))
    stop_times_df = pd.read_csv(os.path.join(BASE_PATH, 'stop_times_cleaned.csv'))
    stops_df = pd.read_csv(os.path.join(BASE_PATH, 'stops.csv'))

    # Convertir columnas de tiempo a formato timedelta para poder realizar cálculos
    stop_times_df['arrival_time'] = pd.to_timedelta(stop_times_df['arrival_time'])
    stop_times_df['departure_time'] = pd.to_timedelta(stop_times_df['departure_time'])

except FileNotFoundError as e:
    print(f"Error: Asegúrate de que los archivos CSV ({e.filename}) estén en el mismo directorio que el notebook.")
    # Detener la ejecución si los archivos no se encuentran
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
print(f"Número de nodos (paradas): {G.number_of_nodes()}")
print(f"Número de aristas (segmentos de viaje): {G.number_of_edges()}")

# Ejemplo de cómo acceder a los datos de un nodo
if G.number_of_nodes() > 0:
    sample_node = list(G.nodes())[0]
    print(f"\nDatos del nodo de ejemplo '{sample_node}': {G.nodes[sample_node]}")

# Ejemplo de cómo acceder a los datos de una arista
if G.number_of_edges() > 0:
    sample_edge = list(G.edges(data=True))[0]
    print(f"\nDatos de la arista de ejemplo: De '{sample_edge[0]}' a '{sample_edge[1]}' -> {sample_edge[2]}")

# Nombre del archivo de salida
OUTPUT_DIR = r"C:\Users\fbetancourt\Documents\GitHub\Tesis\QGIS"
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Asegura que el directorio de salida exista
output_filename = os.path.join(OUTPUT_DIR, "transporte_publico_grafo.gexf")

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

    nx.write_gexf(G, output_filename)
    print(f"\nGrafo exportado exitosamente como '{output_filename}'.")
    print("Puedes importar este archivo directamente en Gephi.")
except NameError:
    print("Error: El grafo 'G' no fue encontrado. Asegúrate de ejecutar la celda anterior primero.")
except Exception as e:
    print(f"Ocurrió un error al exportar el grafo: {e}")