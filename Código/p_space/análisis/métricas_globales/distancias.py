
import networkx as nx
import os
import json
from dotenv import load_dotenv

def calcular_matriz_distancias_p_space():
    """
    Carga el grafo P-space y calcula la matriz de distancias de caminos más cortos
    (número de trasbordos). Guarda la matriz en un archivo JSON.
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

    GRAPH_PATH = os.path.join(project_root, os.getenv("P_SPACE_GRAPH_PATH"))
    OUTPUT_FILE = os.path.join(project_root, os.getenv("P_SPACE_DISTANCES_MATRIX_PATH"))
    
    if not os.getenv("P_SPACE_GRAPH_PATH") or not os.getenv("P_SPACE_DISTANCES_MATRIX_PATH"):
        print("Error: Asegúrate de que las variables P_SPACE_GRAPH_PATH y P_SPACE_DISTANCES_MATRIX_PATH estén definidas en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        return

    print(f"Cargando grafo P-space desde {GRAPH_PATH}...")
    G = nx.read_gpickle(GRAPH_PATH)
    print("Grafo P-space cargado exitosamente.")

    # --- 2. CÁLCULO DE LA MATRIZ DE DISTANCIAS ---
    print("Calculando la matriz de distancias (número de trasbordos)...")
    print("Esto puede tardar dependiendo del tamaño del grafo.")

    # shortest_path_length para grafos no ponderados
    # El resultado es un iterador, lo convertimos a dict
    distancias_iter = nx.all_pairs_shortest_path_length(G)
    distancias = {origen: destinos for origen, destinos in distancias_iter}
    print("Cálculo completado.")

    # --- 3. GUARDADO DE RESULTADOS ---
    print(f"Guardando la matriz de distancias en {OUTPUT_FILE}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(distancias, f, indent=4)
    
    print("\n--- ANÁLISIS DE DISTANCIAS (P-SPACE) ---")
    print("La matriz de distancias ha sido calculada y guardada exitosamente.")
    print("El archivo contiene las rutas más cortas (en número de trasbordos) entre todos los pares de rutas alcanzables.")
    
    # Imprimir un pequeño ejemplo
    if distancias:
        sample_origin = list(distancias.keys())[0]
        sample_destinations = list(distancias[sample_origin].items())[:3]
        print(f"\nEjemplo de datos para la ruta '{sample_origin}':")
        for dest, num_transfers in sample_destinations:
            print(f"  -> Para llegar a la ruta '{dest}': {num_transfers} trasbordo(s)")

if __name__ == '__main__':
    calcular_matriz_distancias_p_space()
