import asyncio
import aiohttp
import pandas as pd
import json
import logging
from pathlib import Path
from collections import defaultdict
from utils.auth.Authentification import get_auth_headers, get_base_url

# Definition aller relevanten Datei- und API-Pfade
DATA_DIR = Path("_data")
JSON_FILE = DATA_DIR / "OBT_Export_Modify_Users.json"
CLIENTUSERCLASSES_FILE = DATA_DIR / "OBT_Export_sub_ClientUserClasses.xlsx"
CLIENTAPPLICATIONSUPPERVISOR_FILE = DATA_DIR / "OBT_Export_sub_ClientApplicationSupervisor.xlsx"
RESULT_FILE = DATA_DIR / "results/result_modify_users.xlsx"
DUPLICATES_FILE = DATA_DIR / "results/duplicates_modify_users.xlsx"
EXCLUDE_ID = "00000000-0000-0000-0000-000000000000"
API_URL = f"{get_base_url()}/api/provisioning-users/v1/users"

# Logging-Format für einheitliche Ausgaben
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def map_excel_to_dict(filepath, user_col, mandant_col, value_columns):
    """
    Wandelt eine Excel-Datei in ein Mapping von UserUID → Mandantenberechtigungen um.
    Nur Datensätze, bei denen mindestens eine Berechtigung aktiv ist, werden übernommen.
    """
    df = pd.read_excel(filepath, dtype=str).fillna("0")
    result = defaultdict(list)
    for _, row in df.iterrows():
        # Entferne Klammern aus UserUID (wie sie im JSON fehlen)
        uid = row[user_col].replace("{", "").replace("}", "")
        try:
            mandant = int(row[mandant_col])
        except Exception:
            continue  # Zeile überspringen, wenn Mandant ungültig
        entry = {"mandantNumber": mandant}
        # Berechtigungen als Boolean abbilden
        for col in value_columns:
            entry[col] = row[col] == "1"
        # Nur speichern, wenn mindestens eine Berechtigung gesetzt ist
        if any(entry[col] for col in value_columns):
            result[uid].append(entry)
    return result

def remove_empty_values(d):
    """
    Entfernt rekursiv alle Felder mit None, leeren Strings, leeren Dicts oder Listen.
    So werden ungültige/leere Daten vor dem API-Call entfernt.
    """
    if isinstance(d, dict):
        return {k: remove_empty_values(v) for k, v in d.items() if v not in [None, "", {}, []]}
    elif isinstance(d, list):
        return [remove_empty_values(x) for x in d if x not in [None, "", {}, []]]
    return d

def load_and_prepare_users():
    """
    Lädt das User-JSON ein, bereinigt Userdaten, entfernt Duplikate,
    mapped User- und Supervisor-Mandanten aus Excel und liefert die User als Liste von Dicts zurück.
    """
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    # Falls nur ein Userobjekt (statt Liste) im JSON steht, Liste daraus machen
    if isinstance(users, dict):
        users = [users]
    df = pd.DataFrame(users)
    # Entferne Klammern aus UserId und DefaultUserCategory
    df["userId"] = df["userId"].str.replace("{", "").str.replace("}", "", regex=False)
    df["defaultUserCategory"] = df["defaultUserCategory"].str.replace("{", "").str.replace("}", "", regex=False)
    # Zerlege die UserCategories-Liste korrekt
    df["userCategories"] = df["userCategories"].apply(
        lambda x: [cat.strip() for cat in x[0].split(",")] if isinstance(x, list) and len(x) > 0 else [])
    # Schließe explizit auszuschließende IDs aus
    df = df[df["userId"] != EXCLUDE_ID]
    # Doppelte Namen finden und eindeutig machen (Name_1, Name_2, ...)
    name_counter, new_names = defaultdict(int), []
    for name in df["name"]:
        count = name_counter[name]
        new_names.append(f"{name}_{count}" if count > 0 else name)
        name_counter[name] += 1
    df["name"] = new_names
    df = df.drop_duplicates(subset="userId")
    users = df.to_dict(orient="records")
    # Spaltennamen aus Excel für das Mapping
    class_cols = [
        "divisions", "accounts", "costCentres", "employeePayrollAccounting", "employeeHrms",
        "releasePayrollHr", "swiss21Salary", "saveMandant", "restoreMandant", "abaAuditAdmin",
        "abaAuditView", "abaClockMonitor", "abaTrak"
    ]
    sup_cols = [
        "fibu", "debi", "kred", "lohn", "adre", "orde", "hrms", "inve",
        "proj", "epay", "shop", "upps", "sccm", "info", "immo", "norm"
    ]
    # Excel-Mappings für User-Klassen und App-Supervisor
    user_classes = map_excel_to_dict(CLIENTUSERCLASSES_FILE, "UserUID", "mandantNumber", class_cols)
    user_sup = map_excel_to_dict(CLIENTAPPLICATIONSUPPERVISOR_FILE, "UserUID", "Client", sup_cols)
    # Je User: Arrays anhängen, ggf. leer wenn kein Mapping
    for user in users:
        uid = user["userId"]
        user["userClassMandants"] = [m for m in user_classes[uid] if m.get("mandantNumber") is not None]
        user["userAppSupervisorMandants"] = [m for m in user_sup[uid] if m.get("mandantNumber") is not None]
    return users

semaphore = asyncio.Semaphore(1)
LIMIT_PER_APP = 70
app_counters = defaultdict(int)
over_limit_records = []

async def modify_user(session, user_data, headers):
    """
    Führt das Update für einen User via API aus.
    Prüft, ob Applikations-Limits überschritten sind, entfernt leere Werte vor dem Request,
    gibt ein Dict mit dem Update-Status zurück.
    """
    user_id = user_data["userId"]
    user_data = remove_empty_values(user_data)
    over_limit = False
    # Limitiere, wie oft pro Applikation "True" gesetzt werden darf
    if "applicationAccess" in user_data:
        for app, value in user_data["applicationAccess"].items():
            if value is True:
                if app_counters[app] < LIMIT_PER_APP:
                    app_counters[app] += 1
                else:
                    user_data["applicationAccess"][app] = False
                    over_limit = True
    if over_limit:
        record = {"userId": user_id, "name": user_data.get("name"), "fullName": user_data.get("fullName")}
        record.update(user_data.get("applicationAccess", {}))
        over_limit_records.append(record)
    async with semaphore:
        try:
            async with session.put(f"{API_URL}/{user_id}", headers=headers, json=user_data) as response:
                resp_text = await response.text()
                return {
                    "Benutzer-ID": user_id,
                    "Benutzername": user_data.get("name", ""),
                    "Status": "Erfolgreich" if response.status in [200, 204] else "Fehlgeschlagen",
                    "Status-Code": response.status,
                    "Nachricht": "Benutzer erfolgreich aktualisiert." if response.status in [200, 204] else resp_text
                }
        except Exception as e:
            return {
                "Benutzer-ID": user_id,
                "Benutzername": user_data.get("name", ""),
                "Status": "Fehlgeschlagen",
                "Status-Code": "Netzwerkfehler",
                "Nachricht": str(e)
            }

def save_results(results, filepath):
    """
    Speichert Ergebnisse als Excel-Datei.
    """
    try:
        pd.DataFrame(results).to_excel(filepath, index=False)
        logging.info(f"Ergebnisse gespeichert in '{filepath}'")
    except Exception as e:
        logging.error(f"Fehler beim Speichern: {e}")

async def main_async():
    """
    Gesamter Ablauf: 
    - Authentifizieren
    - Userdaten inkl. Mappings laden
    - Alle Updates asynchron ausführen
    - Ergebnisse speichern
    """
    headers = get_auth_headers()
    if not headers:
        logging.error("Kein gültiger Header (Token) erhalten.")
        return
    users = load_and_prepare_users()
    if not users:
        logging.warning("Keine gültigen Benutzer gefunden.")
        return
    results = []
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [modify_user(session, user, headers) for user in users]
        for future in asyncio.as_completed(tasks):
            results.append(await future)
    save_results(results, RESULT_FILE)
    save_results(over_limit_records, DATA_DIR / "results/users_over_limit.xlsx")

def main():
    """
    Startet das asynchrone Hauptprogramm.
    """
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
