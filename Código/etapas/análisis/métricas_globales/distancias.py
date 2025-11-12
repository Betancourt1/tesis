
import networkx as nx
import os
import json

def calcular_matriz_distancias():
    """
    Carga el grafo consolidado y calcula la matriz de distancias de caminos más cortos
    (Índice de Shimbel) utilizando el tiempo de viaje como peso.
    Guarda la matriz en un archivo JSON.
    """
    # --- 1. CARGA DE DATOS ---
    BASE_DIR = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis"
    GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo_consolidado.gexf")
    OUTPUT_DIR = os.path.join(BASE_DIR, "Código", "etapas", "análisis", "métricas_globales")
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "matriz_distancias_shimbel.json")
    
    print(f"Cargando grafo desde {GRAPH_PATH}...")
    G = nx.read_gexf(GRAPH_PATH)
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
