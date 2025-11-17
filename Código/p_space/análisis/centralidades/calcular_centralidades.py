
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
    print("Atributos añadidos correctamente.")

    # --- 4. GUARDAR EL GRAFO ENRIQUECIDO ---
    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    print(f"Guardando el grafo P-space enriquecido en {GRAPH_PATH} (sobrescribiendo)...")
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    print("¡Proceso completado!")
