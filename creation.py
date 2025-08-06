import subprocess
import sys

def run_module(module_path):
    """
    Führt ein angegebenes Python-Modul als Subprozess aus, gibt die Standardausgabe und
    eventuelle Fehlerausgabe aus.
    """
    print(f"\n--- Running: {module_path} ---")
    # Starte das Modul als separaten Prozess und sammle dessen Ausgabe
    result = subprocess.run([sys.executable, "-m", module_path], capture_output=True, text=True)
    # Gib die Standardausgabe des Moduls aus
    print(result.stdout)
    # Gib die Fehlerausgabe aus, falls vorhanden
    if result.stderr:
        print(result.stderr)

if __name__ == "__main__":
    # Liste der Modulpfade, die nacheinander ausgeführt werden sollen
    modules = [
        "utils.Creation.CreateCategory",
        "utils.Creation.CreateServiceUsers",
        "utils.Creation.CreateUsers",
        "utils.Modification.ModifyPassword",
        "utils.Modification.ModifyUsers",
        "utils.Creation.CreateProgramPolicy",
        "utils.Creation.CreateClientPolicy",
    ]
    # Durchlaufe die Liste und führe jedes Modul aus
    for mod in modules:
        run_module(mod)