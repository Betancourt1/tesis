
import json
import os
import numpy as np
import networkx as nx
from dotenv import load_dotenv
import pickle
import sys

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

    INPUT_FILE = os.path.join(project_root, os.getenv("L_SPACE_DISTANCES_MATRIX_PATH"))
    GRAPH_PATH = os.path.join(project_root, os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"))

    if not os.getenv("L_SPACE_DISTANCES_MATRIX_PATH") or not os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"):
        print("Error: Asegúrate de que las variables L_SPACE_DISTANCES_MATRIX_PATH y L_SPACE_CONSOLIDATED_GRAPH_PATH estén definidas en tu archivo .env")
        return
    if not os.path.exists(INPUT_FILE):
        print(f"Error: No se encontró el archivo de la matriz de distancias en la ruta especificada en .env: {INPUT_FILE}")
        print("Ejecuta 'distancias.py' primero.")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        return

    print(f"Cargando la matriz de distancias desde {INPUT_FILE}...")
    with open(INPUT_FILE, 'r') as f:
        distancias = json.load(f)
    print("Matriz cargada.")

    print(f"Cargando el grafo para obtener atributos de nodos desde {GRAPH_PATH}...")
    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
    print("Grafo cargado.")

    # --- 2. ANÁLISIS DE ACCESIBILIDAD ---
    print("\nCalculando accesibilidad promedio por nodo...")
    accesibilidad_promedio = {}
    for origen, destinos in distancias.items():
        tiempos = [tiempo for tiempo in destinos.values() if tiempo > 0]
        if tiempos:
            accesibilidad_promedio[origen] = np.mean(tiempos)

    # Ordenar nodos por accesibilidad
    nodos_mas_accesibles = sorted(accesibilidad_promedio.items(), key=lambda item: item[1])[:10]
    nodos_menos_accesibles = sorted(accesibilidad_promedio.items(), key=lambda item: item[1], reverse=True)[:10]

    print("\n--- ANÁLISIS DE ACCESIBILIDAD ---")
    print("\nTop 10 nodos más accesibles (mejor conectados):")
    for nodo, tiempo in nodos_mas_accesibles:
        lat, lon = G.nodes[nodo].get('stop_lat', 0), G.nodes[nodo].get('stop_lon', 0)
        print(f"  - Nodo {nodo}: {tiempo:.2f} min en promedio a otros nodos. (Lat: {lat:.4f}, Lon: {lon:.4f})")

    print("\nTop 10 nodos menos accesibles (peor conectados):")
    for nodo, tiempo in nodos_menos_accesibles:
        lat, lon = G.nodes[nodo].get('stop_lat', 0), G.nodes[nodo].get('stop_lon', 0)
        print(f"  - Nodo {nodo}: {tiempo:.2f} min en promedio a otros nodos. (Lat: {lat:.4f}, Lon: {lon:.4f})")

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
