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