
import networkx as nx
import os
import json
from dotenv import load_dotenv
import pickle
import sys

def calcular_matriz_distancias():
    """
    Carga el grafo consolidado y calcula la matriz de distancias de caminos más cortos
    (Índice de Shimbel) utilizando el tiempo de viaje como peso.
    Guarda la matriz en un archivo JSON.
    """
    # --- 1. CARGA DE DATOS ---
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
    OUTPUT_FILE = os.path.join(project_root, os.getenv("L_SPACE_DISTANCES_MATRIX_PATH"))
    
    if not os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH") or not os.getenv("L_SPACE_DISTANCES_MATRIX_PATH"):
        print("Error: Asegúrate de que las variables L_SPACE_CONSOLIDATED_GRAPH_PATH y L_SPACE_DISTANCES_MATRIX_PATH estén definidas en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        return

    print(f"Cargando grafo desde {GRAPH_PATH}...")
    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
    print("Grafo cargado exitosamente.")

    # --- 2. CÁLCULO DE LA MATRIZ DE DISTANCIAS (ÍNDICE DE SHIMBEL) ---
    print("Calculando la matriz de distancias de caminos más cortos (Índice de Shimbel)...")
    print("Esto puede tardar bastante dependiendo del tamaño del grafo.")

    # shortest_path_length devuelve un diccionario de diccionarios: {nodo_origen: {nodo_destino: distancia}}
    # Usamos 'travel_time_minutes' como el peso de las aristas.
    try:
        distancias = dict(nx.all_pairs_dijkstra_path_length(G, weight='travel_time_minutes'))
        print("Cálculo completado.")

        # --- 3. GUARDADO DE RESULTADOS ---
        print(f"Guardando la matriz de distancias en {OUTPUT_FILE}...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(distancias, f, indent=4)
        
        print("\n--- ANÁLISIS DE DISTANCIAS (ÍNDICE DE SHIMBEL) ---")
        print(f"La matriz de distancias ha sido calculada y guardada exitosamente.")
        print("El archivo contiene las rutas más cortas (en minutos) entre todos los pares de nodos alcanzables.")
        
        # Imprimir un pequeño ejemplo
        if distancias:
            sample_origin = list(distancias.keys())[0]
            sample_destinations = list(distancias[sample_origin].items())[:3]
            print(f"\nEjemplo de datos para el nodo '{sample_origin}':")
            for dest, time in sample_destinations:
                print(f"  -> Destino '{dest}': {time:.2f} minutos")

    except Exception as e:
        print(f"Ocurrió un error durante el cálculo o guardado: {e}")

if __name__ == '__main__':
    calcular_matriz_distancias()
