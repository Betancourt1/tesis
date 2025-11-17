import subprocess
import sys
import os

# Define the base directory for the project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def run_script(script_path, description):
    """Helper function to run a Python script."""
    print(f"\n--- {description} ---")
    full_script_path = os.path.join(BASE_DIR, script_path)
    command = [sys.executable, full_script_path]
    print(f"Executing command: {' '.join(command)}")
    
    # Run the subprocess directly, letting its output go to the console
    result = subprocess.run(command, check=True)
    
    if result.returncode == 0:
        print(f"SUCCESS: {description} completed.")
    else:
        print(f"ERROR: {description} failed with exit code {result.returncode}.")
        sys.exit(1) # Exit if any step fails

def run_l_space_pipeline():
    """
    Orchestrates the L-space graph construction pipeline.
    """
    print("=============================================")
    print("=== Starting L-Space Graph Construction =====")
    print("=============================================")

    # Step 1: Initial graph construction from GTFS
    run_script(r"Código\l_space\construcción\construcción_de_grafo.py", "Construcción inicial del grafo L-espacio desde GTFS")

    # Step 2: Consolidate stops using DBSCAN
    run_script(r"Código\l_space\construcción\consolidación.py", "Consolidación de paradas para el grafo L-espacio")

    print("=============================================")
    print("=== L-Space Graph Construction Completed ====")
    print("=============================================")

    print("\n=============================================")
    print("=== Starting L-Space Graph Analysis =========")
    print("=============================================")

    # Analysis Step 1: Calculate Centralities
    run_script(r"Código\l_space\análisis\centralidades\calcular_centralidades.py", "Cálculo de centralidades para el grafo L-espacio")

    # Analysis Step 2: Detect Communities
    run_script(r"Código\l_space\análisis\comunidades\detectar_comunidades.py", "Detección de comunidades para el grafo L-espacio")

    # Analysis Step 3: Analyze Communities
    run_script(r"Código\l_space\análisis\comunidades\analizar_comunidades.py", "Análisis de las comunidades detectadas en el grafo L-espacio")

    # Analysis Step 4: Analyze Connectivity
    run_script(r"Código\l_space\análisis\métricas_globales\conectividad.py", "Análisis de conectividad del grafo L-espacio")

    # Analysis Step 5: Calculate Distances
    run_script(r"Código\l_space\análisis\métricas_globales\distancias.py", "Cálculo de la matriz de distancias del grafo L-espacio")

    # Analysis Step 6: Analyze Distances Matrix
    run_script(r"Código\l_space\análisis\métricas_globales\analisis_matriz_distancias.py", "Análisis de la matriz de distancias del grafo L-espacio")

    # Analysis Step 7: Analyze Efficiency
    run_script(r"Código\l_space\análisis\métricas_globales\eficiencia.py", "Análisis de eficiencia del grafo L-espacio")

    # Analysis Step 8: Analyze Local Structure
    run_script(r"Código\l_space\análisis\métricas_globales\estructura_local.py", "Análisis de la estructura local del grafo L-espacio")

    # Analysis Step 9: Analyze Robustness
    run_script(r"Código\l_space\análisis\robustez\analisis_robustez.py", "Análisis de robustez del grafo L-espacio")

    print("=============================================")
    print("=== L-Space Graph Analysis Completed ========")
    print("=============================================")

if __name__ == '__main__':
    run_l_space_pipeline()