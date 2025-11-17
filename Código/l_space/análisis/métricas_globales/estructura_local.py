
import networkx as nx
import os
from dotenv import load_dotenv
import pickle
import sys

def analizar_estructura_local():
    """
    Carga el grafo consolidado y calcula el coeficiente de clustering global (transitividad).
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
    
    print(f"Cargando grafo desde {GRAPH_PATH}...")
    if not os.getenv("L_SPACE_CONSOLIDATED_GRAPH_PATH"):
        print(f"Error: La variable L_SPACE_CONSOLIDATED_GRAPH_PATH no está definida en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: El archivo del grafo no se encontró en la ruta especificada en .env: {GRAPH_PATH}")
        return

    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
    print("Grafo cargado exitosamente.")

    # --- 2. CÁLCULO DEL COEFICIENTE DE CLUSTERING GLOBAL ---
    # La transitividad mide la probabilidad de que dos vecinos de un nodo sean también vecinos.
    # Es la fracción de todos los "triángulos" posibles sobre los "tripletes conectados".
    # Un valor alto indica una red con clústeres densos.
    transitividad = nx.transitivity(G)

    # --- 3. IMPRESIÓN DE RESULTADOS ---
    print("\n--- ANÁLISIS DE ESTRUCTURA LOCAL ---")
    print(f"Coeficiente de Clustering Global (Transitividad): {transitividad:.6f}")
    print("Este valor representa la probabilidad de que dos paradas conectadas a una tercera estén también conectadas entre sí.")
    print("Un valor más cercano a 1 indica una mayor tendencia a la formación de clústeres locales en la red.")

if __name__ == '__main__':
    analizar_estructura_local()
