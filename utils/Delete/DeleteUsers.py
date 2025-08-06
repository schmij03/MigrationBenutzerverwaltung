import requests
import pandas as pd
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.auth.Authentification import get_auth_headers, get_base_url

# Definiert das Arbeitsverzeichnis und die relevanten Dateipfade
DATA_DIR = Path("_data")
EXCEL_FILE = DATA_DIR / "DeleteUsers.xlsx"
API_URL = f"{get_base_url()}/api/provisioning-users/v1/users"

# Initialisiert das Logging für die Konsolenausgabe
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_users():
    # Lädt die Liste der zu löschenden Benutzer-UIDs aus der Excel-Datei
    try:
        users_df = pd.read_excel(EXCEL_FILE)
        if "UID" not in users_df.columns:
            logging.error("Die Spalte 'UID' wurde in der Datei nicht gefunden.")
            return []
        # Gibt eine Liste aller gültigen UIDs zurück
        return users_df["UID"].dropna().astype(str).tolist()
    except Exception as e:
        logging.error("Fehler beim Laden der Excel-Datei: %s", e)
        return []

def delete_user(uid, headers):
    # Löscht einen einzelnen Benutzer anhand der UID über die API
    try:
        response = requests.delete(f"{API_URL}/{uid}", headers=headers)
        if response.status_code in [200, 204]:
            logging.info("✅ UID '%s' erfolgreich gelöscht.", uid)
        else:
            logging.error("❌ Fehler bei UID '%s': %s - %s", uid, response.status_code, response.text)
    except requests.RequestException as e:
        logging.error("❌ Netzwerkfehler bei UID '%s': %s", uid, e)

def delete_users_concurrently(uids, headers, max_workers=10):
    # Löscht mehrere Benutzer parallel mithilfe von Threads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(delete_user, uid, headers) for uid in uids]
        for future in as_completed(futures):
            # Ergebnisse werden nicht benötigt, Fehler werden im delete_user geloggt
            pass

def main():
    # Hauptfunktion: lädt UIDs, prüft Token und startet das parallele Löschen
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch: Kein gültiger Token erhalten.")
        return

    uids = load_users()
    if not uids:
        logging.warning("Keine UIDs zum Löschen gefunden.")
        return

    logging.info("Starte paralleles Löschen von %d Usern...", len(uids))
    delete_users_concurrently(uids, headers)

if __name__ == "__main__":
    # Startpunkt des Skripts
    main()
