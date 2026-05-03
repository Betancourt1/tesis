
import json
import os
import numpy as np
import networkx as nx
from dotenv import load_dotenv
import pickle
import sys


MIN_REACHABILITY_RATIO = 0.95

def analizar_matriz_shimbel():
    """
    Carga y analiza la matriz de distancias de Shimbel para extraer métricas
    de accesibilidad, cobertura y tiempos de viaje extremos.
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

    dist_rel_path = os.getenv("L_SPACE_DISTANCES_MATRIX_PATH")
    graph_rel_path = os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH")

    if not dist_rel_path or not graph_rel_path:
        print("Error: Asegúrate de que las variables L_SPACE_DISTANCES_MATRIX_PATH y L_SPACE_CONSOLIDATED_GRAPH_PATH estén definidas en tu archivo .env")
        return

    # Resolver rutas en disco: si es directorio o sin extensión, usar grafos/l_space/matriz_distancias_shimbel.json
    dist_raw = os.path.join(project_root, dist_rel_path)
    graph_path = os.path.join(project_root, graph_rel_path)

    if os.path.isdir(dist_raw) or not os.path.splitext(dist_raw)[1]:
        dist_dir = dist_raw
        dist_file = os.path.join(dist_dir, "matriz_distancias_shimbel.json")
    else:
        dist_dir = os.path.dirname(dist_raw)
        dist_file = dist_raw
    if not dist_dir:
        dist_dir = os.path.join(project_root, "grafos", "l_space")
        dist_file = os.path.join(dist_dir, "matriz_distancias_shimbel.json")

    # Validación robusta de rutas
    if not os.path.exists(dist_file):
        print(f"Error: No se encontró el archivo de la matriz de distancias en la ruta esperada: {dist_file}")
        print("Ejecuta 'distancias.py' primero o ajusta L_SPACE_DISTANCES_MATRIX_PATH para que apunte a grafos/l_space/.")
        return
    if os.path.isdir(dist_file):
        print(f"Error: La ruta L_SPACE_DISTANCES_MATRIX_PATH apunta a un directorio, no a un archivo: {dist_file}")
        print("Actualiza tu archivo .env para que L_SPACE_DISTANCES_MATRIX_PATH apunte al archivo JSON de la matriz de distancias (por ejemplo, 'grafos/l_space/matriz_distancias_shimbel.json').")
        return

    if not os.path.exists(graph_path):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {graph_path}")
        print("Verifica que L_SPACE_CONSOLIDATED_GRAPH_PATH apunte al archivo del grafo (por ejemplo, un .pkl) y no a un directorio.")
        return
    if os.path.isdir(graph_path):
        print(f"Error: La ruta L_SPACE_CONSOLIDATED_GRAPH_PATH apunta a un directorio, no a un archivo: {graph_path}")
        print("Actualiza tu archivo .env para que L_SPACE_CONSOLIDATED_GRAPH_PATH apunte al archivo del grafo consolidado.")
        return

    print(f"Cargando la matriz de distancias desde {dist_file}...")
    with open(dist_file, 'r', encoding='utf-8') as f:
        distancias = json.load(f)
    print("Matriz cargada.")

    print(f"Cargando el grafo para obtener atributos de nodos desde {graph_path}...")
    with open(graph_path, "rb") as f:
        G = pickle.load(f)
    print("Grafo cargado.")

    # --- 2. ANÁLISIS DE ACCESIBILIDAD ---
    print("\nCalculando accesibilidad promedio por nodo...")
    accesibilidad_por_nodo = []
    total_destinos_posibles = max(G.number_of_nodes() - 1, 1)
    for origen, destinos in distancias.items():
        tiempos = [
            tiempo
            for destino, tiempo in destinos.items()
            if destino != origen and tiempo > 0
        ]
        alcanzables = len(tiempos)
        if not tiempos:
            continue
        accesibilidad_por_nodo.append(
            {
                "nodo": origen,
                "tiempo_promedio": float(np.mean(tiempos)),
                "alcanzables": alcanzables,
                "porcentaje_alcanzable": alcanzables / total_destinos_posibles,
            }
        )

    nodos_con_cobertura_suficiente = [
        fila
        for fila in accesibilidad_por_nodo
        if fila["porcentaje_alcanzable"] >= MIN_REACHABILITY_RATIO
    ]
    if not nodos_con_cobertura_suficiente:
        print(
            "Advertencia: ningun nodo alcanza el umbral de cobertura definido; "
            "se usara el conjunto completo de nodos alcanzables."
        )
        nodos_con_cobertura_suficiente = accesibilidad_por_nodo

    nodos_mas_accesibles = sorted(
        nodos_con_cobertura_suficiente,
        key=lambda fila: fila["tiempo_promedio"],
    )[:10]
    nodos_menos_accesibles = sorted(
        nodos_con_cobertura_suficiente,
        key=lambda fila: fila["tiempo_promedio"],
        reverse=True,
    )[:10]

    print("\n--- ANÁLISIS DE ACCESIBILIDAD ---")
    print(
        "\nTop 10 nodos más accesibles "
        f"(cobertura mínima: {MIN_REACHABILITY_RATIO:.0%} de la red):"
    )
    for fila in nodos_mas_accesibles:
        nodo = fila["nodo"]
        tiempo = fila["tiempo_promedio"]
        lat, lon = G.nodes[nodo].get('stop_lat', 0), G.nodes[nodo].get('stop_lon', 0)
        print(
            f"  - Nodo {nodo}: {tiempo:.2f} min en promedio a "
            f"{fila['alcanzables']} nodos ({fila['porcentaje_alcanzable']:.1%}). "
            f"(Lat: {lat:.4f}, Lon: {lon:.4f})"
        )

    print(
        "\nTop 10 nodos menos accesibles "
        f"(cobertura mínima: {MIN_REACHABILITY_RATIO:.0%} de la red):"
    )
    for fila in nodos_menos_accesibles:
        nodo = fila["nodo"]
        tiempo = fila["tiempo_promedio"]
        lat, lon = G.nodes[nodo].get('stop_lat', 0), G.nodes[nodo].get('stop_lon', 0)
        print(
            f"  - Nodo {nodo}: {tiempo:.2f} min en promedio a "
            f"{fila['alcanzables']} nodos ({fila['porcentaje_alcanzable']:.1%}). "
            f"(Lat: {lat:.4f}, Lon: {lon:.4f})"
        )

    # --- 3. ANÁLISIS DE COBERTURA (REACHABILITY) ---
    print("\n--- ANÁLISIS DE COBERTURA ---")
    umbrales = [15, 30, 45, 60]
    cobertura_promedio = {umbral: [] for umbral in umbrales}

    for origen, destinos in distancias.items():
        tiempos = list(destinos.values())
        for umbral in umbrales:
            nodos_alcanzables = sum(1 for t in tiempos if 0 < t <= umbral)
            cobertura_promedio[umbral].append(nodos_alcanzables)

    print("Nodos alcanzables en promedio desde cualquier parada:")
    for umbral, coberturas in cobertura_promedio.items():
        avg_nodos = np.mean(coberturas)
        porcentaje = (avg_nodos / G.number_of_nodes()) * 100
        print(f"  - En {umbral} minutos: {avg_nodos:.0f} nodos ({porcentaje:.1f}% de la red)")

    # --- 4. VIAJE MÁS LARGO ---
    print("\n--- ANÁLISIS DE VIAJES EXTREMOS ---")
    max_tiempo = 0
    viaje_mas_largo = (None, None)

    for origen, destinos in distancias.items():
        for destino, tiempo in destinos.items():
            if tiempo > max_tiempo:
                max_tiempo = tiempo
                viaje_mas_largo = (origen, destino)

    if viaje_mas_largo[0]:
        origen, destino = viaje_mas_largo
        lat1, lon1 = G.nodes[origen].get('stop_lat', 0), G.nodes[origen].get('stop_lon', 0)
        lat2, lon2 = G.nodes[destino].get('stop_lat', 0), G.nodes[destino].get('stop_lon', 0)
        print(f"El viaje más largo en la red es de {max_tiempo:.2f} minutos.")
        print(f"  - Desde el nodo {origen} (Lat: {lat1:.4f}, Lon: {lon1:.4f})")
        print(f"  - Hasta el nodo {destino} (Lat: {lat2:.4f}, Lon: {lon2:.4f})")

if __name__ == '__main__':
    analizar_matriz_shimbel()
