
import networkx as nx
import os
import pandas as pd

def calcular_centralidades():
    """
    Carga el grafo consolidado y calcula varias métricas de centralidad,
    considerando las ponderaciones de las aristas donde sea apropiado.
    Guarda los resultados en un archivo CSV.
    """
    # --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
    BASE_DIR = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis"
    GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo_consolidado.gexf")
    OUTPUT_DIR = os.path.join(BASE_DIR, "Código", "etapas", "análisis", "centralidades")
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "centralidades.csv")

    print(f"Cargando grafo desde {GRAPH_PATH}...")
    G = nx.read_gexf(GRAPH_PATH)
    print("Grafo cargado.")

    # --- 2. CÁLCULO DE CENTRALIDADES ---
    print("Calculando centralidades... (esto puede tardar)")

    # a) Centralidad de Grado (Ponderada por número de rutas originales)
    # Usamos el atributo 'original_edge_count' que definimos en la consolidación.
    degree_in = dict(G.in_degree(weight='original_edge_count'))
    degree_out = dict(G.out_degree(weight='original_edge_count'))

    # b) Centralidad de Intermediación (Ponderada por tiempo de viaje)
    # Mide puentes en los caminos MÁS RÁPIDOS.
    betweenness = nx.betweenness_centrality(G, weight='travel_time_minutes', normalized=True)

    # c) Centralidad de Cercanía (usa el tiempo de viaje como 'distancia')
    closeness = nx.closeness_centrality(G, distance='travel_time_minutes')

    # d) Centralidad de Eigenvector (Ponderada por número de rutas originales)
    # Mide la influencia en corredores importantes. Puede fallar en grafos no fuertemente conectados.
    try:
        eigenvector = nx.eigenvector_centrality(G, weight='original_edge_count', max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        print("La centralidad de Eigenvector no convergió. Se omitirá.")
        eigenvector = {node: 0.0 for node in G.nodes()}

    print("Cálculos completados.")

    # --- 3. CONSOLIDACIÓN Y GUARDADO DE RESULTADOS ---
    print("Consolidando resultados en un DataFrame...")
    
    # Extraer coordenadas y stop_count de los nodos
    node_data = {
        node: {
            'lat': data.get('stop_lat', 0),
            'lon': data.get('stop_lon', 0),
            'stop_count': data.get('stop_count', 0)
        } for node, data in G.nodes(data=True)
    }
    df_nodes = pd.DataFrame.from_dict(node_data, orient='index')

    # Crear DataFrame para cada centralidad
    df_degree_in = pd.DataFrame(degree_in.items(), columns=['node_id', 'in_degree_weighted'])
    df_degree_out = pd.DataFrame(degree_out.items(), columns=['node_id', 'out_degree_weighted'])
    df_betweenness = pd.DataFrame(betweenness.items(), columns=['node_id', 'betweenness'])
    df_closeness = pd.DataFrame(closeness.items(), columns=['node_id', 'closeness'])
    df_eigenvector = pd.DataFrame(eigenvector.items(), columns=['node_id', 'eigenvector'])

    # Unir todos los DataFrames
    df = df_nodes.reset_index().rename(columns={'index': 'node_id'})
    for df_centrality in [df_degree_in, df_degree_out, df_betweenness, df_closeness, df_eigenvector]:
        df = pd.merge(df, df_centrality, on='node_id', how='left')

    # Guardar en CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Resultados guardados exitosamente en {OUTPUT_FILE}")

    # --- 4. MOSTRAR TOP 10 DE CADA MÉTRICA ---
    print("\n--- TOP 10 NODOS POR CENTRALIDAD ---")
    for metrica in ['in_degree_weighted', 'out_degree_weighted', 'betweenness', 'closeness', 'eigenvector']:
        print(f"\n--- Top 10 por: {metrica} ---")
        top_10 = df.nlargest(10, metrica)
        for _, row in top_10.iterrows():
            print(f"  - Nodo {row['node_id']} (Lat: {row['lat']:.4f}, Lon: {row['lon']:.4f}): {row[metrica]:.4f}")

if __name__ == '__main__':
    calcular_centralidades()
