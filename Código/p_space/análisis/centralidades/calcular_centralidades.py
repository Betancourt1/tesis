import networkx as nx
import os
import pandas as pd
from dotenv import load_dotenv
import pickle
import sys

def calcular_centralidades_p_space():
    """
    Carga el grafo P-space, calcula varias métricas de centralidad y
    las añade como atributos a los nodos del grafo.
    El grafo enriquecido se guarda sobrescribiendo el archivo original.
    """
    def _parse_original_stops(value):
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            return [stop for stop in value.split(',') if stop]
        return []

    def _build_routes_by_supernode(G_obj, project_root_path):
        """
        Devuelve un diccionario {supernode_id: [rutas]} usando GTFS.
        Si falta información GTFS, devuelve un diccionario vacío y muestra advertencias.
        """
        if not os.getenv("GTFS_DIR"):
            print("Advertencia: La variable GTFS_DIR no está definida en .env. No se listarán rutas por nodo.")
            return {}

        gtfs_dir = os.path.join(project_root_path, os.getenv("GTFS_DIR"))
        if not os.path.exists(gtfs_dir):
            print(f"Advertencia: No se encontró el directorio GTFS en {gtfs_dir}. No se listarán rutas por nodo.")
            return {}

        try:
            stop_times_df = pd.read_csv(os.path.join(gtfs_dir, 'stop_times.csv'), dtype={'trip_id': str, 'stop_id': str})
            trips_df = pd.read_csv(os.path.join(gtfs_dir, 'trips.csv'), dtype={'trip_id': str, 'route_id': str})
        except FileNotFoundError as e:
            print(f"Advertencia: No se pudo cargar {e.filename}. No se listarán rutas por nodo.")
            return {}

        stop_to_supernode = {}
        for supernode_id, data in G_obj.nodes(data=True):
            for stop_id in _parse_original_stops(data.get('original_stops', [])):
                stop_to_supernode[str(stop_id)] = str(supernode_id)

        if not stop_to_supernode:
            print("Advertencia: No se pudieron mapear paradas a supernodos. No se listarán rutas por nodo.")
            return {}

        route_stops_df = pd.merge(stop_times_df, trips_df, on='trip_id')[['route_id', 'stop_id']].drop_duplicates()
        route_stops_df['supernode_id'] = route_stops_df['stop_id'].map(stop_to_supernode)
        route_stops_df.dropna(subset=['supernode_id'], inplace=True)

        grouped = route_stops_df.groupby('supernode_id')['route_id'].apply(lambda s: sorted(set(s)))
        print(f"Mapa de rutas por supernodo construido para {len(grouped)} nodos.")
        return grouped.to_dict()

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

    GRAPH_PATH = os.path.join(project_root, os.getenv("P_SPACE_GRAPH_PATH"))

    if not os.getenv("P_SPACE_GRAPH_PATH"):
        print(f"Error: La variable P_SPACE_GRAPH_PATH no está definida en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        print("Asegúrate de haber ejecutado primero el script de construcción del grafo P-space.")
        return

    print(f"Cargando grafo P-space desde {GRAPH_PATH}...")
    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
    print("Grafo cargado.")

    # Mapa auxiliar para enriquecer la impresión de resultados
    rutas_por_supernodo = _build_routes_by_supernode(G, project_root)

    # --- 2. CÁLCULO DE CENTRALIDADES ---
    print("Calculando centralidades... (esto puede tardar)")

    # a) Centralidad de Grado (no dirigido)
    degree = dict(G.degree())

    # b) Centralidad de Intermediación
    betweenness = nx.betweenness_centrality(G, normalized=True)

    # c) Centralidad de Cercanía
    closeness = nx.closeness_centrality(G)

    # d) Centralidad de Eigenvector
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        print("La centralidad de Eigenvector no convergió. Se asignará 0 a todos los nodos.")
        eigenvector = {node: 0.0 for node in G.nodes()}

    print("Cálculos completados.")

    # --- 3. AÑADIR ATRIBUTOS AL GRAFO ---
    print("Añadiendo atributos de centralidad a los nodos del grafo...")
    nx.set_node_attributes(G, degree, name='degree')
    nx.set_node_attributes(G, betweenness, name='betweenness')
    nx.set_node_attributes(G, closeness, name='closeness')
    nx.set_node_attributes(G, eigenvector, name='eigenvector')
    print("Atributos añadidos correctamente.")

    # --- 4. GUARDAR EL GRAFO ENRIQUECIDO ---
    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    print(f"Guardando el grafo P-space enriquecido en {GRAPH_PATH} (sobrescribiendo)...")
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    print("¡Proceso completado!")

    # --- 5. MOSTRAR TOP 10 DE CADA MÉTRICA ---
    print("\n--- TOP 10 RUTAS POR CENTRALIDAD ---")
    node_data = {node: data for node, data in G.nodes(data=True)}
    df = pd.DataFrame.from_dict(node_data, orient='index')
    if rutas_por_supernodo:
        df['routes_serving'] = df.index.map(lambda idx: rutas_por_supernodo.get(str(idx)))

    def _format_routes(routes):
        if not routes:
            return "N/D"
        preview = routes[:5]
        extra = len(routes) - len(preview)
        suffix = f" (+{extra})" if extra > 0 else ""
        return ', '.join(map(str, preview)) + suffix

    def _format_coords(row):
        lat = row.get('stop_lat')
        lon = row.get('stop_lon')
        if pd.notna(lat) and pd.notna(lon):
            return f"({lat:.5f}, {lon:.5f})"
        return "N/D"

    def _ruta_repr(row, index):
        rid = row.get('route_id') or row.get('route_short_name')
        if rid is not None:
            return f"Ruta {rid}"
        stop_count = row.get('stop_count')
        stop_count_str = f" | paradas:{int(stop_count)}" if pd.notna(stop_count) else ""
        return f"Supernodo {index}{stop_count_str}"

    for metrica in ['degree', 'betweenness', 'closeness', 'eigenvector']:
        if metrica in df.columns:
            print(f"\n--- Top 10 por: {metrica} ---")
            top_10 = df.nlargest(10, metrica)
            for index, row in top_10.iterrows():
                rutas_texto = _format_routes(row.get('routes_serving'))
                coords_texto = _format_coords(row)
                print(f"  - {_ruta_repr(row, index)}: {row[metrica]:.4f} | rutas: {rutas_texto} | coords: {coords_texto}")
        else:
            print(f"\n--- Métrica '{metrica}' no encontrada en el grafo ---")


if __name__ == "__main__":
    calcular_centralidades_p_space()
