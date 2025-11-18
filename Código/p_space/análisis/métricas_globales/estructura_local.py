import pickle
import networkx as nx
import os
from dotenv import load_dotenv

def analizar_estructura_local_p_space():
    """
    Carga el grafo P-space y calcula el coeficiente de clustering global (transitividad).
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
    
    print(f"Cargando grafo P-space desde {GRAPH_PATH}...")
    if not os.getenv("P_SPACE_GRAPH_PATH"):
        print(f"Error: La variable P_SPACE_GRAPH_PATH no está definida en .env")
        return
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: No se encontró el archivo del grafo en la ruta especificada en .env: {GRAPH_PATH}")
        return

    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
    print("Grafo P-space cargado exitosamente.")

    # --- 2. CÁLCULO DEL COEFICIENTE DE CLUSTERING GLOBAL ---
    # La transitividad mide la probabilidad de que dos vecinos de un nodo sean también vecinos.
    # En P-space, esto significa que si la Ruta A se conecta con la B y la C,
    # cuál es la probabilidad de que B y C también se conecten directamente.
    transitividad = nx.transitivity(G)

    # --- 3. IMPRESIÓN DE RESULTADOS ---
    print("\n--- ANÁLISIS DE ESTRUCTURA LOCAL (P-SPACE) ---")
    print(f"Coeficiente de Clustering Global (Transitividad): {transitividad:.6f}")
    print("Este valor representa la probabilidad de que dos rutas que comparten paradas con una tercera, también compartan paradas entre sí.")
    print("Un valor más cercano a 1 indica una mayor tendencia a la formación de clústeres de rutas (zonas de alta conectividad).")

if __name__ == '__main__':
    analizar_estructura_local_p_space()
