
import networkx as nx
import os
import json

def calcular_matriz_distancias_p_space():
    """
    Carga el grafo P-space y calcula la matriz de distancias de caminos más cortos
    (número de trasbordos). Guarda la matriz en un archivo JSON.
    """
    # --- 1. CARGA DE DATOS ---
    BASE_DIR = '.'
    GRAPH_PATH = os.path.join(BASE_DIR, "out", "p_space", "transporte_publico_grafo_p_space.gexf")
    OUTPUT_DIR = os.path.join(BASE_DIR, "out", "p_space", "analisis")
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "matriz_distancias_p_space.json")
    
    print(f"Cargando grafo P-space desde {GRAPH_PATH}...")
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: El archivo del grafo no se encontró en la ruta especificada.")
        return

    G = nx.read_gexf(GRAPH_PATH)
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
