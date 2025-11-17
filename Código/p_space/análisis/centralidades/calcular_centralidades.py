
import networkx as nx
import os
import pandas as pd

def calcular_centralidades_p_space():
    """
    Carga el grafo P-space, calcula varias métricas de centralidad y
    las añade como atributos a los nodos del grafo.
    El grafo enriquecido se guarda en un nuevo archivo.
    """
    # --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
    BASE_DIR = '.'
    INPUT_GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo_p_space.gexf")
    OUTPUT_GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo_p_space_centralidades.gexf")

    print(f"Cargando grafo P-space desde {INPUT_GRAPH_PATH}...")
    try:
        G = nx.read_gexf(INPUT_GRAPH_PATH)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo del grafo en {INPUT_GRAPH_PATH}.")
        print("Asegúrate de haber ejecutado primero el script de construcción del grafo P-space.")
        return
    print("Grafo cargado.")

    # --- 2. CÁLCULO DE CENTRALIDADES ---
    print("Calculando centralidades para el grafo P-space...")

    # a) Centralidad de Grado (no ponderada)
    degree = dict(G.degree())

    # b) Centralidad de Intermediación (no ponderada)
    betweenness = nx.betweenness_centrality(G, normalized=True)

    # c) Centralidad de Cercanía (no ponderada)
    closeness = nx.closeness_centrality(G)

    # d) Centralidad de Eigenvector (no ponderada)
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        print("La centralidad de Eigenvector no convergió. Se asignará 0.")
        eigenvector = {node: 0.0 for node in G.nodes()}

    print("Cálculos completados.")

    # --- 3. AÑADIR ATRIBUTOS AL GRAFO ---
    print("Añadiendo atributos de centralidad a los nodos (supernodos)...")
    nx.set_node_attributes(G, degree, name='degree')
    nx.set_node_attributes(G, betweenness, name='betweenness')
    nx.set_node_attributes(G, closeness, name='closeness')
    nx.set_node_attributes(G, eigenvector, name='eigenvector')
    print("Atributos añadidos correctamente.")

    # --- 4. GUARDAR EL GRAFO ENRIQUECIDO ---
    os.makedirs(os.path.dirname(OUTPUT_GRAPH_PATH), exist_ok=True)
    print(f"Guardando el grafo P-space enriquecido en {OUTPUT_GRAPH_PATH}...")
    nx.write_gexf(G, OUTPUT_GRAPH_PATH)
    print("¡Proceso completado!")

    # --- 5. MOSTRAR TOP 10 DE CADA MÉTRICA ---
    print("\n--- TOP 10 SUPERNODOS POR CENTRALIDAD ---")
    node_data = {node: data for node, data in G.nodes(data=True)}
    df = pd.DataFrame.from_dict(node_data, orient='index')
    
    for metrica in ['degree', 'betweenness', 'closeness', 'eigenvector']:
        if metrica in df.columns:
            print(f"\n--- Top 10 por: {metrica} ---")
            top_10 = df.nlargest(10, metrica)
            for index, row in top_10.iterrows():
                # El 'index' del DataFrame ahora corresponde al ID del supernodo (como string)
                print(f"  - Supernodo ID '{index}': {row[metrica]:.4f}")
        else:
            print(f"\n--- Métrica '{metrica}' no encontrada en el grafo ---")

if __name__ == '__main__':
    calcular_centralidades_p_space()
