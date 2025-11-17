
import pandas as pd
import networkx as nx
import pickle
from itertools import combinations
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env en la raíz del proyecto
try:
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))
    if not os.path.exists(dotenv_path):
        raise FileNotFoundError
    load_dotenv(dotenv_path=dotenv_path)
    project_root = os.path.dirname(dotenv_path)
except FileNotFoundError:
    print("Error: No se pudo encontrar el archivo .env en la raíz del proyecto.")
    sys.exit(1)

# --- DESCRIPCIÓN ---
# Este script construye el grafo P-espacio de acuerdo a la metodología de la tesis.
# 1. Carga el grafo consolidado (L-espacio) para obtener los "supernodos".
# 2. Crea un mapa que asocia cada parada original con su supernodo correspondiente.
# 3. Usa los datos GTFS para determinar qué supernodos son servidos por cada ruta.
# 4. Construye el grafo P-espacio:
#    - Los nodos son los 4,203 supernodos.
#    - Una arista conecta dos supernodos si comparten al menos una ruta.
#    - El peso de la arista es el número de rutas que comparten.
# 5. Guarda el grafo resultante en formato gpickle para preservar los tipos de datos.

# --- RUTAS DE ARCHIVOS ---
CONSOLIDATED_GRAPH_PATH = os.path.join(project_root, os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"))
GTFS_DIR = os.path.join(project_root, os.getenv("GTFS_DIR"))
OUTPUT_GRAPH_PATH = os.path.join(project_root, os.getenv("P_SPACE_GRAPH_PATH"))

if not os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH") or not os.getenv("GTFS_DIR") or not os.getenv("P_SPACE_GRAPH_PATH"):
    raise ValueError("Asegúrate de que las variables L_SPACE_CONSOLIDATED_GRAPH_PATH, GTFS_DIR y P_SPACE_GRAPH_PATH estén definidas en tu archivo .env")



def construir_p_space_correcto():
    """
    Construye y guarda el grafo P-espacio siguiendo la metodología de la tesis.
    """
    print("--- Iniciando la construcción del P-espacio (metodología de tesis) ---")

    # --- 1. Cargar grafo consolidado y crear mapa de paradas ---
    print(f"Cargando grafo consolidado desde {CONSOLIDATED_GRAPH_PATH}...")
    if not os.path.exists(CONSOLIDATED_GRAPH_PATH):
        print(f"Error: No se encontró el grafo consolidado en {CONSOLIDATED_GRAPH_PATH}.")
        print("Asegúrate de ejecutar primero el pipeline de construcción del L-espacio.")
        return
    
    with open(CONSOLIDATED_GRAPH_PATH, "rb") as f:
        G_consolidado = pickle.load(f)

    stop_to_supernode_map = {}
    print("Creando mapa de paradas a supernodos...")
    for supernode_id, data in G_consolidado.nodes(data=True):
        # El atributo puede tener nombres diferentes dependiendo del script que lo generó
        original_stops_str = data.get('original_stops', '')
        if isinstance(original_stops_str, list): # Si ya es una lista
            original_stops = original_stops_str
        else: # Si es un string separado por comas
            original_stops = original_stops_str.split(',')
            
        for stop_id in original_stops:
            stop_to_supernode_map[str(stop_id)] = str(supernode_id)
    print(f"Mapa creado con {len(stop_to_supernode_map)} paradas originales.")

    # --- 2. Cargar datos GTFS y mapear rutas a supernodos ---
    print("Cargando datos GTFS...")
    try:
        stop_times_df = pd.read_csv(os.path.join(GTFS_DIR, 'stop_times.csv'), dtype={'trip_id': str, 'stop_id': str})
        trips_df = pd.read_csv(os.path.join(GTFS_DIR, 'trips.csv'), dtype={'trip_id': str, 'route_id': str})
    except FileNotFoundError as e:
        print(f"Error: No se encontró el archivo GTFS: {e.filename}")
        return

    # Unir dataframes para obtener route_id por cada stop_id
    route_stops_df = pd.merge(stop_times_df, trips_df, on='trip_id')[['route_id', 'stop_id']].drop_duplicates()

    print("Agrupando supernodos por ruta...")
    supernodes_por_ruta = {}
    # Mapear stop_id a supernode_id
    route_stops_df['supernode_id'] = route_stops_df['stop_id'].map(stop_to_supernode_map)
    # Eliminar paradas que no están en el grafo consolidado
    route_stops_df.dropna(subset=['supernode_id'], inplace=True)
    
    # Agrupar por ruta para obtener el conjunto de supernodos
    grouped = route_stops_df.groupby('route_id')['supernode_id'].apply(set)
    supernodes_por_ruta = grouped.to_dict()
    print(f"Se procesaron {len(supernodes_por_ruta)} rutas.")

    # --- 3. Construir el grafo P-espacio ---
    print("Construyendo el grafo P-espacio...")
    G_pspace = nx.Graph()
    
    # Añadir todos los supernodos para asegurar consistencia con L-espacio
    G_pspace.add_nodes_from(G_consolidado.nodes(data=True))

    # Generar aristas creando cliques por cada ruta
    for route_id, supernodes_in_route in supernodes_por_ruta.items():
        if len(supernodes_in_route) >= 2:
            for u, v in combinations(supernodes_in_route, 2):
                if G_pspace.has_edge(u, v):
                    G_pspace[u][v]['weight'] += 1
                else:
                    G_pspace.add_edge(u, v, weight=1)
    
    print("Grafo P-espacio construido.")
    print(f"Nodos: {G_pspace.number_of_nodes()}")
    print(f"Aristas: {G_pspace.number_of_edges()}")

    # --- 4. Guardar el grafo ---
    print(f"Guardando el grafo P-espacio en {OUTPUT_GRAPH_PATH}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_GRAPH_PATH, "wb") as f:
        pickle.dump(G_pspace, f, pickle.HIGHEST_PROTOCOL)

    print("--- Proceso de construcción de P-espacio finalizado. ---")

if __name__ == '__main__':
    construir_p_space_correcto()
