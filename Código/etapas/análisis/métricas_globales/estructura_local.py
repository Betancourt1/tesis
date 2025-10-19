
import networkx as nx
import os

def analizar_estructura_local():
    """
    Carga el grafo consolidado y calcula el coeficiente de clustering global (transitividad).
    """
    # --- 1. CARGA DE DATOS ---
    BASE_DIR = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis"
    GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo_consolidado.gexf")
    
    print(f"Cargando grafo desde {GRAPH_PATH}...")
    if not os.path.exists(GRAPH_PATH):
        print(f"Error: El archivo del grafo no se encontró.")
        return

    G = nx.read_gexf(GRAPH_PATH)
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
