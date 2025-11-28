
import networkx as nx
import os
import pickle
import pandas as pd
import numpy as np
from dotenv import load_dotenv

def analizar_comunidades():
    """
    Carga el grafo con atributos de comunidad y realiza un análisis básico:
    - Cuenta el número de comunidades.
    - Calcula el tamaño de cada una.
    - Identifica el centro geográfico de las comunidades más grandes.
    - Imprime un resumen para ser usado en la redacción de la tesis.
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

    print(f"Cargando grafo con comunidades desde {GRAPH_PATH}...")
    if not os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"):
        print("Error: La variable L_SPACE_CONSOLIDATED_GRAPH_PATH no está definida en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        print("Ejecuta 'detectar_comunidades.py' primero.")
        return
    G = pickle.load(open(GRAPH_PATH, "rb"))
    print("Grafo cargado.")

    # --- 2. ANÁLISIS DE COMUNIDADES ---
    print("\nAnalizando las comunidades detectadas...")

    # Extraer los datos de comunidad de los nodos
    node_data = G.nodes(data=True)
    if not any('community' in data for _, data in node_data):
        print("Error: El grafo no contiene el atributo 'community' en los nodos.")
        return

    # Crear un DataFrame para facilitar el análisis
    df_nodes = pd.DataFrame([{'node_id': node, **data} for node, data in node_data])
    
    # a) Conteo de comunidades y tamaños
    community_counts = df_nodes['community'].value_counts().reset_index()
    community_counts.columns = ['community_id', 'node_count']
    num_communities = len(community_counts)

    # b) Identificar comunidades triviales (muy pequeñas)
    trivial_threshold = 5 # Considerar trivial una comunidad con 5 o menos nodos
    num_trivial_communities = community_counts[community_counts['node_count'] <= trivial_threshold].shape[0]

    # c) Análisis de las comunidades principales (las 10 más grandes)
    top_communities = community_counts.nlargest(10, 'node_count')

    # d) Calcular centro geográfico de las comunidades principales
    top_communities_details = []
    for index, row in top_communities.iterrows():
        community_id = row['community_id']
        nodes_in_community = df_nodes[df_nodes['community'] == community_id]
        
        # Convertir lat/lon a numérico, ignorando errores
        latitudes = pd.to_numeric(nodes_in_community['stop_lat'], errors='coerce').dropna()
        longitudes = pd.to_numeric(nodes_in_community['stop_lon'], errors='coerce').dropna()

        if not latitudes.empty and not longitudes.empty:
            center_lat = latitudes.mean()
            center_lon = longitudes.mean()
        else:
            center_lat, center_lon = np.nan, np.nan

        top_communities_details.append({
            'community_id': community_id,
            'node_count': row['node_count'],
            'center_lat': center_lat,
            'center_lon': center_lon
        })

    df_top_details = pd.DataFrame(top_communities_details)

    # --- 3. IMPRESIÓN DE RESULTADOS PARA LA TESIS ---
    print("\n--- RESUMEN DEL ANÁLISIS DE COMUNIDADES ---")
    print(f"\nResultados Generales:")
    print(f"- Número total de comunidades detectadas: {num_communities}")
    print(f"- De estas, {num_trivial_communities} son comunidades pequeñas o aisladas (<= {trivial_threshold} nodos).")
    
    print("\nPrincipales Comunidades (Top 10 por tamaño):")
    for index, row in df_top_details.iterrows():
        print(f"  - Comunidad {int(row['community_id'])}: {int(row['node_count'])} nodos. Centroide aprox: (Lat: {row['center_lat']:.4f}, Lon: {row['center_lon']:.4f})")

    print("\nInterpretación sugerida para la redacción:")
    print("- La modularidad de la red, evidenciada por el algoritmo de Louvain, sugiere una estructura policéntrica.")
    print("- Las comunidades más grandes probablemente corresponden a corredores de transporte principales o zonas geográficas densas (ej. Centro, Zapopan, Tlaquepaque, Tonalá).")
    print("- Las comunidades pequeñas pueden representar rutas alimentadoras o zonas periféricas con conexión limitada.")
    print("- Se recomienda cruzar la ubicación de los centroides con un mapa del AMG para nombrar o caracterizar a las comunidades principales.")

if __name__ == '__main__':
    analizar_comunidades()
