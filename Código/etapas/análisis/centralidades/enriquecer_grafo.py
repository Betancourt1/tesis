
import networkx as nx
import os
import pandas as pd

def enriquecer_grafo_con_centralidades():
    """
    Carga el grafo consolidado y el archivo CSV con las centralidades,
    y añade estas últimas como atributos a los nodos del grafo.
    Guarda el resultado como un nuevo archivo GEXF.
    """
    # --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
    BASE_DIR = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis"
    
    # Rutas de entrada
    GRAPH_PATH = os.path.join(BASE_DIR, "QGIS", "transporte_publico_grafo_consolidado.gexf")
    CENTRALIDADES_PATH = os.path.join(BASE_DIR, "Código", "etapas", "análisis", "centralidades", "centralidades.csv")
    
    # Ruta de salida
    OUTPUT_DIR = os.path.join(BASE_DIR, "QGIS")
    OUTPUT_GRAPH_PATH = os.path.join(OUTPUT_DIR, "transporte_publico_grafo_enriquecido.gexf")

    print(f"Cargando grafo original desde {GRAPH_PATH}...")
    G = nx.read_gexf(GRAPH_PATH)
    print("Grafo cargado.")

    print(f"Cargando datos de centralidad desde {CENTRALIDADES_PATH}...")
    if not os.path.exists(CENTRALIDADES_PATH):
        print("Error: No se encontró el archivo centralidades.csv. Ejecuta 'calcular_centralidades.py' primero.")
        return
    df_centralidades = pd.read_csv(CENTRALIDADES_PATH)
    print("Datos de centralidad cargados.")

    # --- 2. AÑADIR ATRIBUTOS AL GRAFO ---
    print("Añadiendo atributos de centralidad a los nodos del grafo...")

    # NetworkX requiere que los IDs de los nodos sean del tipo correcto (en este caso, strings)
    df_centralidades['node_id'] = df_centralidades['node_id'].astype(str)
    
    # Prepara los datos para nx.set_node_attributes
    # El formato debe ser un diccionario: {id_nodo: valor_atributo}
    metricas = ['in_degree_weighted', 'out_degree_weighted', 'betweenness', 'closeness', 'eigenvector']
    for metrica in metricas:
        # Crea un diccionario para la métrica actual
        atributo = pd.Series(df_centralidades[metrica].values, index=df_centralidades.node_id).to_dict()
        # Añade el atributo al grafo
        nx.set_node_attributes(G, atributo, name=metrica)
    
    print("Atributos añadidos correctamente.")

    # --- 3. GUARDAR EL GRAFO ENRIQUECIDO ---
    print(f"Guardando el grafo enriquecido en {OUTPUT_GRAPH_PATH}...")
    nx.write_gexf(G, OUTPUT_GRAPH_PATH)
    print("¡Proceso completado!")
    print("El nuevo archivo GEXF ahora contiene las centralidades como atributos de nodo.")
    print("Puedes usar estos atributos en Gephi/QGIS para visualizar el tamaño o color de los nodos.")

if __name__ == '__main__':
    enriquecer_grafo_con_centralidades()
