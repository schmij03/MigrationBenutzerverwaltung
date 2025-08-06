import pandas as pd
from datetime import datetime
import requests
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from utils.auth.Authentification import get_auth_headers, get_base_url

# Definiert Arbeits- und API-Pfade
DATA_DIR = Path("_data")
EXCEL_FILE = DATA_DIR / "OBT_Export_Create_ProgrammPolicies.xlsx"
API_URL = f"{get_base_url()}/api/provisioning-users/v1/policies/programs"

# Setzt Logging-Format für Konsolenausgaben
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_programm_policies(excel_file, column_mapping, headers):
    """
    Liest Programm-Policies aus Excel, baut pro Zeile das passende JSON-Objekt
    und sendet alle Policies parallelisiert an die API.
    """
    df = pd.read_excel(excel_file)
    json_objects = []
    for _, row in df.iterrows():
        # Grundstruktur für eine Policy (leere Listen, leere Felder nach Vorgabe)
        obj = {
            "name": {
                "data": {
                    "de": row[column_mapping['name_data_de']],
                    "de_DE": row[column_mapping['name_data_de']],
                    "en": "",
                    "fr": "",
                    "it": "",
                }
            },
            "negative": row[column_mapping['negative']],
            "force": row[column_mapping['force']],
            "inactive": row[column_mapping['inactive']],
            "userCategories": [],
            "users": [],
            "programAccess": [],
            "mutationDate": datetime.now().isoformat()
        }
        # Lese userCategories aus Excel-Spalte und wandle in Liste um (falls Werte gesetzt)
        if pd.notna(row[column_mapping['userCategories']]):
            obj["userCategories"] = [u.strip() for u in str(row[column_mapping['userCategories']]).split(",") if u.strip()]
        # Lese users aus Excel-Spalte und wandle in Liste um (falls Werte gesetzt)
        if pd.notna(row[column_mapping['users']]):
            obj["users"] = [u.strip() for u in str(row[column_mapping['users']]).split(",") if u.strip()]
        # Suche alle Spalten, die Zugriff auf Anwendungen beschreiben
        for col in df.columns:
            if col.startswith('programmAcces_application_'):
                app_name = col.split('_')[-1]
                raw_range = str(row[col]).replace(" ", "")
                # Debug: print(raw_range)
                if not raw_range:
                    continue
                # Filtere leere Werte und "0" heraus
                ranges = [r for r in raw_range.split(",") if r and r != '0']
                # Für alle Anwendungen außer "df": Füge Extrawerte hinzu (Bereiche 70-79, 700-799, 7000-7999)
                if app_name != 'df' and ranges:
                    extra = [str(i) for i in list(range(70, 80)) + list(range(700, 800)) + list(range(7000, 8000))]
                    ranges.extend(extra)
                # Falls noch Bereiche vorhanden, füge sie zum programAccess-Array hinzu
                if ranges:  
                    obj["programAccess"].append({
                        "application": app_name,
                        "range": ",".join(ranges)
                    })
        json_objects.append(obj)
    # Sende alle Policies parallelisiert an die API
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(create_programm_policy, obj, headers) for obj in json_objects]
    logging.info("%d Program-Policies werden parallel gesendet.", len(json_objects))

def create_programm_policy(json_data, headers):
    """
    Sendet eine einzelne Programm-Policy per POST-Request an die API und loggt das Ergebnis.
    """
    try:
        response = requests.post(API_URL, headers=headers, json=json_data)
        if response.status_code in [200, 201]:
            logging.info("Program-Policy erfolgreich erstellt.")
        else:
            logging.error("Fehler: %s - %s", response.status_code, response.text)
    except requests.RequestException as e:
        logging.error("Netzwerkfehler: %s", e)

def main():
    """
    Holt Auth-Header, legt das Spalten-Mapping fest und verarbeitet die Excel.
    """
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch  Kein gültiger Token erhalten.")
        return

    column_mapping = {
        'name_data_de': 'name_data_de',
        'negative': 'negative',
        'force': 'force',
        'inactive': 'inactive',
        'userCategories': 'userCategories',
        'users': 'users'
    }

    load_programm_policies(EXCEL_FILE, column_mapping, headers)

if __name__ == "__main__":
    main()