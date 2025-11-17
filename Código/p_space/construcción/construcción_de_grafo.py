
import pandas as pd
import networkx as nx
from itertools import combinations
import os

def construir_grafo_p_space(gtfs_path, output_path):
    """
    Construye un grafo en P-space a partir de datos GTFS.

    En P-space, los nodos son las rutas de transporte y se crea una arista
    entre dos rutas si comparten al menos una parada.

    Args:
        gtfs_path (str): Ruta al directorio que contiene los archivos GTFS.
        output_path (str): Ruta donde se guardará el grafo GEXF resultante.
    """
    # Cargar los datos necesarios
    try:
        stops = pd.read_csv(os.path.join(gtfs_path, 'stops.csv'))
        stop_times = pd.read_csv(os.path.join(gtfs_path, 'stop_times.csv'))
        trips = pd.read_csv(os.path.join(gtfs_path, 'trips.csv'))
        routes = pd.read_csv(os.path.join(gtfs_path, 'routes.csv'))
    except FileNotFoundError as e:
        print(f"Error: No se encontró el archivo GTFS: {e.filename}")
        return

    # Unir los dataframes para obtener las paradas por ruta
    df = stop_times.merge(trips, on='trip_id')
    df = df.merge(routes, on='route_id')

    # Crear un diccionario de rutas y sus paradas
    paradas_por_ruta = df.groupby('route_id')['stop_id'].apply(set).to_dict()

    # Crear el grafo P-space
    G = nx.Graph()

    # Añadir nodos (rutas)
    for route_id, route_info in routes.iterrows():
        G.add_node(route_id, 
                   route_short_name=route_info['route_short_name'], 
                   route_long_name=route_info['route_long_name'],
                   route_type=route_info['route_type'])

    # Añadir aristas si las rutas comparten paradas
    for ruta1, ruta2 in combinations(paradas_por_ruta.keys(), 2):
        if not paradas_por_ruta[ruta1].isdisjoint(paradas_por_ruta[ruta2]):
            G.add_edge(ruta1, ruta2)

    # Guardar el grafo
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nx.write_gexf(G, output_path)
    print(f"Grafo P-space construido y guardado en: {output_path}")
    print(f"Nodos: {G.number_of_nodes()}, Aristas: {G.number_of_edges()}")

if __name__ == '__main__':
    # Rutas de entrada y salida
    GTFS_DIR = 'Datasets/gtfs_amg_20240312/Datos'
    OUTPUT_DIR = 'out/p_space'
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'transporte_publico_grafo_p_space.gexf')

    construir_grafo_p_space(GTFS_DIR, OUTPUT_FILE)
