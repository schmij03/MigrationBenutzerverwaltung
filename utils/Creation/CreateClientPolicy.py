import pandas as pd
from datetime import datetime
import requests
import logging
import json
from pathlib import Path
from utils.auth.Authentification import get_auth_headers, get_base_url

# Setzt die Pfade für Arbeitsverzeichnis, Quelldatei und API-Endpunkt
DATA_DIR = Path("_data")
EXCEL_FILE = DATA_DIR / "OBT_Export_Create_ClientPolicies.xlsx"
API_URL = f"{get_base_url()}/api/provisioning-users/v1/policies/mandants"

# Konfiguriert das Logging für konsistente Ausgaben
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_mandant_policies(excel_file, column_mapping, headers):
    """
    Lädt Mandanten-Policies aus einer Excel-Datei,
    wandelt jede Zeile in ein Policy-Objekt um und sendet sie einzeln an die API.
    """
    df = pd.read_excel(excel_file)
    all_policies = []
    for idx, row in df.iterrows():
        # Erzeuge das Policy-Objekt auf Basis der Spaltenzuordnung und Werte der Zeile
        obj = {
            "name": {
                "data": {
                    "de": row[column_mapping['name_data_de']],
                    "de_DE": row[column_mapping['name_data_de']],
                    "en": "",
                    "fr": "",
                    "it": ""
                }
            },
            "negative": row[column_mapping['negative']],
            "force": row[column_mapping['force']],
            "inactive": row[column_mapping['inactive']],
            "userCategories": [],
            "users": [],
            "mandantAccess": {
                "applications": [],
                "range": ""
            },
            "mutationDate": datetime.now().isoformat()
        }
        # Befülle userCategories als Liste, falls vorhanden
        if pd.notna(row[column_mapping['userCategories']]):
            obj["userCategories"] = [u.strip() for u in str(row[column_mapping['userCategories']]).split(",") if u.strip()]
        # Befülle users als Liste, falls vorhanden
        if pd.notna(row[column_mapping['users']]):
            obj["users"] = [u.strip() for u in str(row[column_mapping['users']]).split(",") if u.strip()]
        # Befülle applications als Liste, falls vorhanden
        if pd.notna(row[column_mapping['mandantAccess_Application']]):
            obj["mandantAccess"]["applications"] = [a.strip() for a in str(row[column_mapping['mandantAccess_Application']]).split(",") if a.strip()]
        # Befülle das range-Feld (als kommaseparierte String-Liste, ohne Duplikate), falls vorhanden
        if pd.notna(row[column_mapping['mandantAccess_range']]):
            range_items = [item.strip() for item in str(row[column_mapping['mandantAccess_range']]).split(",") if item.strip()]
            unique_range = list(dict.fromkeys(range_items))
            obj["mandantAccess"]["range"] = ",".join(unique_range)
        all_policies.append(obj)
        # Sende das Policy-Objekt an die API
        create_mandant_policy(obj, headers)
        logging.info("API-Call für Zeile %d ausgeführt.", idx + 1)

def create_mandant_policy(json_data, headers):
    """
    Sendet eine POST-Anfrage zur Erstellung einer Mandanten-Policy an die API
    und loggt das Ergebnis.
    """
    try:
        response = requests.post(API_URL, headers=headers, json=json_data)
        if response.status_code in [200, 201]:
            logging.info("Mandant-Policy erfolgreich erstellt.")
        else:
            logging.error("Fehler: %s - %s", response.status_code, response.text)
    except requests.RequestException as e:
        logging.error("Netzwerkfehler: %s", e)

def main():
    """
    Prüft die Authentifizierung, definiert die Spaltenzuordnung
    und startet die Verarbeitung aller Policies aus der Excel-Datei.
    """
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch: Kein gültiger Token erhalten.")
        return

    # Mapping: Excel-Spaltennamen auf Felder im JSON
    column_mapping = {
        'name_data_de': 'name_data_de',
        'negative': 'negative',
        'force': 'force',
        'inactive': 'inactive',
        'userCategories': 'userCategories',
        'users': 'users',
        'mandantAccess_range': 'mandantAccess_range',
        'mandantAccess_Application': 'mandantAccess_applications',
    }

    load_mandant_policies(EXCEL_FILE, column_mapping, headers)

if __name__ == "__main__":
    main()