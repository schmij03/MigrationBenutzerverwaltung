import subprocess
import sys

def run_module(module_path):
    """
    Führt das angegebene Python-Modul als Subprozess aus und gibt die Ausgaben (stdout und stderr) aus.
    """
    print(f"\n--- Running: {module_path} ---")
    # Starte das Modul als Subprozess und sammle dessen Ausgaben
    result = subprocess.run([sys.executable, "-m", module_path], capture_output=True, text=True)
    # Zeige die Standardausgabe des Subprozesses
    print(result.stdout)
    # Zeige die Fehlerausgabe (falls vorhanden)
    if result.stderr:
        print(result.stderr)

if __name__ == "__main__":
    # Liste der zu startenden Delete-Module
    modules = [
        "utils.Delete.DeleteUsers",
        "utils.Delete.DeleteProgrammPolicies",
        "utils.Delete.DeleteClientPolicies",
        "utils.Delete.DeleteCategories",
    ]
    # Starte alle Module nacheinander und zeige deren Ausgaben an
    for mod in modules:
        run_module(mod)
