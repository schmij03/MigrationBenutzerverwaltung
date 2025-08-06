import asyncio
import aiohttp
import pandas as pd
import json
import logging
from pathlib import Path
from collections import defaultdict
from utils.auth.Authentification import get_auth_headers, get_base_url

# Zentrales Limit für parallele Requests
MAX_PARALLEL_REQUESTS = 5

DATA_DIR = Path("_data")
JSON_FILE = DATA_DIR / "OBT_Export_Create_ServiceUsers.json"
RESULT_FILE = DATA_DIR / "results/result_create_serviceusers.xlsx"
DUPLICATES_FILE = DATA_DIR / "results/duplicates_create_serviceusers.xlsx"
EXCLUDE_ID = "00000000-0000-0000-0000-000000000000"

API_URL = f"{get_base_url()}/api/provisioning-users/v1/users/serviceusers"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_and_filter_users():
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            data = [data]
        df = pd.DataFrame(data)
        df["userId"] = df["userId"].str.replace("{", "").str.replace("}", "", regex=False)
        df["defaultUserCategory"] = df["defaultUserCategory"].str.replace("{", "").str.replace("}", "", regex=False)
        df["userCategories"] = df["userCategories"].apply(
            lambda x: [cat.strip() for cat in x[0].split(",")] if isinstance(x, list) and len(x) > 0 else [])
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
        logging.error("Fehler beim Laden der JSON-Datei: %s", e)
        return []

def clean_user_data(user):
    if "userClassMandants" in user:
        user["userClassMandants"] = [
            m for m in user["userClassMandants"] if m.get("mandantNumber") is not None
        ]
        if not user["userClassMandants"]:
            user["userClassMandants"] = []
    return user

# Nutze die zentrale Konstante für die Semaphore
semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

async def modify_user(session, user_data, headers):
    user_data = clean_user_data(user_data)
    user_id = user_data["userId"]
    async with semaphore:
        try:
            async with session.post(f"{API_URL}/{user_id}", headers=headers, json=user_data) as response:
                resp_text = await response.text()
                return {
                    "Benutzer-ID": user_id,
                    "Benutzername": user_data["name"],
                    "Status": "Erfolgreich" if response.status in [200, 204] else "Fehlgeschlagen",
                    "Status-Code": response.status,
                    "Nachricht": "Benutzer erfolgreich aktualisiert." if response.status in [200, 204] else resp_text
                }
        except Exception as e:
            return {
                "Benutzer-ID": user_id,
                "Benutzername": user_data["name"],
                "Status": "Fehlgeschlagen",
                "Status-Code": "Netzwerkfehler",
                "Nachricht": str(e)
            }

def save_results(results):
    try:
        df = pd.DataFrame(results)
        df.to_excel(RESULT_FILE, index=False)
        logging.info("Ergebnisse gespeichert in '%s'", RESULT_FILE)
    except Exception as e:
        logging.error("Fehler beim Speichern der Ergebnisse: %s", e)

async def main_async():
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch  Kein gültiger Header (Token) erhalten.")
        return
    users = load_and_filter_users()
    if not users:
        logging.warning("Keine gültigen Benutzer gefunden.")
        return
    results = []
    # Nutze die zentrale Konstante auch im TCPConnector
    connector = aiohttp.TCPConnector(limit=MAX_PARALLEL_REQUESTS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [modify_user(session, user, headers) for user in users]
        for future in asyncio.as_completed(tasks):
            result = await future
            results.append(result)
    save_results(results)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()