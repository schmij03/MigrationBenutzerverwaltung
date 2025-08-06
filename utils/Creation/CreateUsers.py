import asyncio
import aiohttp
import pandas as pd
import json
import logging
from pathlib import Path
from collections import defaultdict
from utils.auth.Authentification import get_auth_headers, get_base_url

# Zentrale Steuerung für parallele Requests
MAX_PARALLEL_REQUESTS = 5

DATA_DIR = Path("_data")
JSON_FILE = DATA_DIR / "OBT_Export_Create_Users.json"
RESULT_FILE = DATA_DIR / "results/result_create_users.xlsx"
DUPLICATES_FILE = DATA_DIR / "results/duplicates_create_users.xlsx"

API_URL = f"{get_base_url()}/api/provisioning-users/v1/users"
EXCLUDE_ID = "00000000-0000-0000-0000-000000000000"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_and_filter_users():
    """
    Lädt Benutzer aus einer JSON-Datei, filtert ungültige und doppelte Einträge,
    macht doppelte Namen eindeutig und gibt eine Liste von Dictionaries zurück.
    """
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            data = [data]
        df = pd.DataFrame(data)
        df["userId"] = df["userId"].str.replace("{", "").str.replace("}", "")
        df["defaultUserCategory"] = df["defaultUserCategory"].str.replace("{", "").str.replace("}", "")
        df["userCategories"] = df["userCategories"].apply(
            lambda x: [cat.strip() for cat in x[0].split(",")] if isinstance(x, list) and len(x) > 0 else []
        )
        df = df[df["userId"] != EXCLUDE_ID]
        duplicated_names = df[df.duplicated(subset="name", keep=False)]
        if not duplicated_names.empty:
            duplicated_names.to_excel(DUPLICATES_FILE, index=False)
            logging.info("Duplikate gespeichert in '%s'", DUPLICATES_FILE)
        name_counter = defaultdict(int)
        new_names = []
        for name in df["name"]:
            count = name_counter[name]
            new_name = f"{name}_{count}" if count > 0 else name
            new_names.append(new_name)
            name_counter[name] += 1
        df["name"] = new_names
        df = df.drop_duplicates(subset="userId")
        return df.to_dict(orient="records")
    except Exception as e:
        logging.error("Fehler beim Lesen der JSON-Datei: %s", e)
        return []

# Nutze zentrale Variable für parallele Requests
semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

async def create_user(session, user_data, headers):
    """
    Erstellt einen Benutzer über die API asynchron und gibt das Ergebnis als Dictionary zurück.
    """
    async with semaphore:
        try:
            async with session.post(API_URL, headers=headers, json=user_data) as response:
                resp_text = await response.text()
                return {
                    "Benutzer-ID": user_data.get("userId", ""),
                    "Benutzername": user_data.get("name", ""),
                    "Status": "Erfolgreich" if response.status in [200, 201] else "Fehlgeschlagen",
                    "Status-Code": response.status,
                    "Nachricht": "Benutzer erfolgreich erstellt." if response.status in [200, 201] else resp_text
                }
        except Exception as e:
            return {
                "Benutzer-ID": user_data.get("userId", ""),
                "Benutzername": user_data.get("name", ""),
                "Status": "Fehlgeschlagen",
                "Status-Code": "Netzwerkfehler",
                "Nachricht": str(e)
            }

def save_results(results):
    """
    Speichert die Ergebnisse aller Benutzer-Erstellungen als Excel-Datei.
    """
    try:
        df = pd.DataFrame(results)
        df.to_excel(RESULT_FILE, index=False)
        logging.info("Ergebnisse gespeichert in '%s'", RESULT_FILE)
    except Exception as e:
        logging.error("Fehler beim Speichern der Ergebnisse: %s", e)

async def main_async():
    """
    Hauptfunktion für die asynchrone Verarbeitung: Authentifiziert,
    lädt Benutzer, schickt sie asynchron an die API und speichert die Ergebnisse.
    """
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch: Kein gültiger Header (Token) erhalten.")
        return
    users = load_and_filter_users()
    if not users:
        logging.warning("Keine gültigen Benutzer gefunden.")
        return
    results = []
    connector = aiohttp.TCPConnector(limit=MAX_PARALLEL_REQUESTS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [create_user(session, user, headers) for user in users]
        for future in asyncio.as_completed(tasks):
            result = await future
            results.append(result)
    save_results(results)

def main():
    """
    Einstiegspunkt für das Skript, startet das asynchrone Hauptprogramm.
    """
    asyncio.run(main_async())

if __name__ == "__main__":
    main()