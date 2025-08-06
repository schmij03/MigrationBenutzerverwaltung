import requests
import pandas as pd
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.auth.Authentification import get_auth_headers, get_base_url

# Definiert das Arbeitsverzeichnis und die relevanten Dateipfade
DATA_DIR = Path("_data")
EXCEL_FILE = DATA_DIR / "DeleteClientPolicies.xlsx"
API_URL = f"{get_base_url()}/api/provisioning-users/v1/policies/mandants"

# Initialisiert das Logging für die Konsolenausgabe
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_ClientPolicies():
    # Lädt die Liste der zu löschenden Client-Policy-UIDs aus der Excel-Datei
    try:
        ClientPolicies_df = pd.read_excel(EXCEL_FILE)
        if "UID" not in ClientPolicies_df.columns:
            logging.error("Die Spalte 'UID' wurde in der Datei nicht gefunden.")
            return []
        # Gibt eine Liste aller gültigen UIDs zurück
        return ClientPolicies_df["UID"].dropna().astype(str).tolist()
    except Exception as e:
        logging.error("Fehler beim Laden der Excel-Datei: %s", e)
        return []

def delete_ClientPolicy(uid, headers):
    # Löscht eine einzelne Client-Policy anhand der UID über die API
    try:
        response = requests.delete(f"{API_URL}/{uid}", headers=headers)
        if response.status_code in [200, 204]:
            logging.info("✅ UID '%s' erfolgreich gelöscht.", uid)
        else:
            logging.error("❌ Fehler bei UID '%s': %s - %s", uid, response.status_code, response.text)
    except requests.RequestException as e:
        logging.error("❌ Netzwerkfehler bei UID '%s': %s", uid, e)

def delete_ClientPolicies_concurrently(uids, headers, max_workers=10):
    # Löscht mehrere Client-Policies parallel mithilfe von Threads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(delete_ClientPolicy, uid, headers) for uid in uids]
        for future in as_completed(futures):
            # Ergebnisse werden nicht benötigt, Fehler werden im delete_ClientPolicy geloggt
            pass

def main():
    # Hauptfunktion: lädt UIDs, prüft Token und startet das parallele Löschen
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch: Kein gültiger Token erhalten.")
        return

    uids = load_ClientPolicies()
    if not uids:
        logging.warning("Keine UIDs zum Löschen gefunden.")
        return

    logging.info("Starte paralleles Löschen von %d Policies...", len(uids))
    delete_ClientPolicies_concurrently(uids, headers)

if __name__ == "__main__":
    # Startpunkt des Skripts
    main()
