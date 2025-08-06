import requests
import json
import pandas as pd
import logging
from pathlib import Path
from utils.auth.Authentification import get_bearer_token, get_auth_headers, get_base_url

# Setzt die Pfade zu Daten und API-Endpunkt
DATA_DIR = Path("_data")
JSON_FILE = DATA_DIR / "OBT_Export_Create_Categories.json"
EXCLUDE_ID = "{00000000-0000-0000-0000-000000000000}"
API_URL = f"{get_base_url()}/api/provisioning-users/v1/categories"

# Logging-Format festlegen (Konsole)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_and_filter_categories():
    """
    Liest die Kategorien-JSON ein, filtert ungültige oder doppelte Einträge
    und gibt eine Liste von Dictionaries zurück.
    """
    try:
        df = pd.read_json(JSON_FILE)
        # Entferne Kategorien mit EXCLUDE_ID als eigene oder Parent-ID
        df = df[
            (df["userCategoryId"] != EXCLUDE_ID) &
            (df["parentUserCategoryId"] != EXCLUDE_ID)
        ]
        # Doppelte Kategorien nach userCategoryId entfernen
        df = df.drop_duplicates(subset="userCategoryId")
        return df.to_dict(orient="records")
    except Exception as e:
        logging.error("Fehler beim Lesen der JSON-Datei: %s", e)
        return []

def create_user_category(category_data, headers):
    """
    Sendet eine POST-Anfrage zum Erstellen einer Benutzerkategorie.
    Loggt das Ergebnis (Erfolg oder Fehler).
    """
    try:
        response = requests.post(API_URL, headers=headers, json=category_data)
        # Hole den deutschsprachigen Kategorienamen für Logging
        name_de = category_data.get("name", {}).get("data", {}).get("de", "Unbekannt")
        if response.status_code in [200, 201]:
            logging.info("Benutzerkategorie '%s' erfolgreich erstellt.", name_de)
        else:
            logging.error("Fehler bei '%s': %s - %s", name_de, response.status_code, response.text)
    except requests.RequestException as e:
        logging.error("Netzwerkfehler bei Kategorie '%s': %s", name_de, e)

def main():
    """
    Holt Auth-Header, lädt und filtert Kategorien,
    und sendet diese einzeln an die API.
    """
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch  Kein gültiger Token erhalten.")
        return

    categories = load_and_filter_categories()
    if not categories:
        logging.warning("Keine gültigen Benutzerkategorien gefunden.")
        return

    for category in categories:
        # Zeigt die verarbeitete Kategorie im Debug-Modus an
        logging.debug("Verarbeite Kategorie: %s", json.dumps(category, indent=2, ensure_ascii=False))
        create_user_category(category, headers)

if __name__ == "__main__":
    main()