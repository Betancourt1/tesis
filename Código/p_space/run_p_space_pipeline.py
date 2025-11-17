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

    try:
        # Run the subprocess directly, letting its output (including tracebacks)
        # go to the console. If the script fails, CalledProcessError is raised.
        result = subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        # In case of error, show a clear message and stop the pipeline
        print(f"ERROR: {description} failed with exit code {e.returncode}.")
        # e.stdout / e.stderr may be None because we're not capturing output,
        # but the child process's traceback will already be printed to the console.
        sys.exit(1)

    if result.returncode == 0:
        print(f"SUCCESS: {description} completed.")

def run_p_space_pipeline():
    """
    Orchestrates the P-space graph construction pipeline.
    """
    print("=============================================")
    print("=== Starting P-Space Graph Construction ===")
    print("=============================================")

    # Step 1: Construct the P-space graph using the corrected script
    # This script expects the consolidated L-space graph to be already generated.
    run_script(
        r"Código\p_space\construcción\construcción_de_grafo.py",
        "Construcción del grafo P-espacio (metodología de tesis)"
    )

    print("=============================================")
    print("=== P-Space Graph Construction Completed ====")
    print("=============================================")

    print("\n=============================================")
    print("=== Starting P-Space Graph Analysis =======")
    print("=============================================")

    # Analysis Step 1: Calculate Centralities
    run_script(
        r"Código\p_space\análisis\centralidades\calcular_centralidades.py",
        "Cálculo de centralidades para el grafo P-espacio"
    )

    # Analysis Step 2: Detect Communities
    run_script(
        r"Código\p_space\análisis\comunidades\detectar_comunidades.py",
        "Detección de comunidades para el grafo P-espacio"
    )

    # Analysis Step 3: Analyze Connectivity
    run_script(
        r"Código\p_space\análisis\métricas_globales\conectividad.py",
        "Análisis de conectividad del grafo P-espacio"
    )

    # Analysis Step 4: Calculate Distances
    run_script(
        r"Código\p_space\análisis\métricas_globales\distancias.py",
        "Cálculo de la matriz de distancias del grafo P-espacio"
    )

    # Analysis Step 5: Analyze Efficiency
    run_script(
        r"Código\p_space\análisis\métricas_globales\eficiencia.py",
        "Análisis de eficiencia del grafo P-espacio"
    )

    # Analysis Step 6: Analyze Local Structure
    run_script(
        r"Código\p_space\análisis\métricas_globales\estructura_local.py",
        "Análisis de la estructura local del grafo P-espacio"
    )

    # Analysis Step 7: Analyze Robustness
    run_script(
        r"Código\p_space\análisis\robustez\analisis_robustez.py",
        "Análisis de robustez del grafo P-espacio"
    )

    print("=============================================")
    print("=== P-Space Graph Analysis Completed =======")
    print("=============================================")

if __name__ == '__main__':
    run_p_space_pipeline()