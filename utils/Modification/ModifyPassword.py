import base64
import pandas as pd
import requests
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from utils.auth.Authentification import get_auth_headers, get_base_url

# Verzeichnis- und Dateipfade
DATA_DIR = Path("_data")
EXCEL_FILE = DATA_DIR / "OBT_Export_Modify_Passwords_Users.xlsx"
RESULT_FILE = DATA_DIR / "results/result_modify_passwords.xlsx"
BASE_URL = f"{get_base_url()}/api/provisioning-users/v1/users"

# Logging-Konfiguration für Konsolenausgaben
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Speichert Ergebnisse jeder Passwortänderung für die spätere Auswertung
results = []

def clean_user_id(user_id):
    """
    Entfernt Klammern und Leerzeichen aus einer UserId.
    """
    return user_id.replace("{", "").replace("}", "").strip()

def encode_password(password):
    """
    Kodiert das Passwort im Base64-Format, wie es die API erwartet.
    """
    return base64.b64encode(password.encode('utf-8')).decode('utf-8')

def update_password(user_id, password, headers):
    """
    Setzt das neue Passwort für einen Benutzer per API-Call.
    Ergebnisse werden im globalen 'results'-Array gespeichert.
    """
    user_id = clean_user_id(user_id)
    url = f"{BASE_URL}/{user_id}/password"
    encoded_password = encode_password(password)

    # Prüfe auf fehlende UserId oder Passwort
    if not user_id or not password:
        logging.warning("Ungültige Daten für UserID: %s", user_id)
        results.append({
            "Benutzer-ID": user_id,
            "Status": "Fehlgeschlagen",
            "Status-Code": "Ungültige Daten",
            "Nachricht": "UserID oder Passwort fehlt."
        })
        return

    try:
        # Passwortänderung via API (PUT-Request)
        response = requests.put(url, headers=headers, data=encoded_password, timeout=10)
        if response.status_code == 200:
            logging.info("Passwort aktualisiert: %s", user_id)
            results.append({
                "Benutzer-ID": user_id,
                "Status": "Erfolgreich",
                "Status-Code": response.status_code,
                "Nachricht": "Passwort erfolgreich aktualisiert."
            })
        else:
            logging.error("Fehler %s für %s: %s", response.status_code, user_id, response.text)
            results.append({
                "Benutzer-ID": user_id,
                "Status": "Fehlgeschlagen",
                "Status-Code": response.status_code,
                "Nachricht": response.text
            })
    except requests.RequestException as e:
        # Fehlerbehandlung bei Netzwerkproblemen oder Timeouts
        logging.error("Netzwerkfehler bei %s: %s", user_id, e)
        results.append({
            "Benutzer-ID": user_id,
            "Status": "Fehlgeschlagen",
            "Status-Code": "Netzwerkfehler",
            "Nachricht": str(e)
        })

def process_password_updates(df, headers):
    """
    Führt die Passwortänderung für alle Benutzer mit mehreren Threads parallel aus.
    """
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(
            lambda row: update_password(str(row.UserId), str(row.Password).strip(), headers),
            df.itertuples(index=False)
        )

def save_results():
    """
    Schreibt das Ergebnis aller Passwortänderungen in eine Excel-Datei.
    """
    try:
        df = pd.DataFrame(results)
        df.to_excel(RESULT_FILE, index=False)
        logging.info("Ergebnisse gespeichert in '%s'", RESULT_FILE)
    except Exception as e:
        logging.error("Fehler beim Speichern der Ergebnisse: %s", e)

def main():
    """
    Hauptablauf: Authentifiziert, lädt Userdaten, ändert Passwörter und speichert das Ergebnis.
    """
    headers = get_auth_headers()
    if not headers:
        logging.error("Abbruch: Kein gültiger Token erhalten.")
        return
    headers["Content-Type"] = "text/plain"
    try:
        df = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        logging.error("Fehler beim Laden der Excel-Datei: %s", e)
        return

    process_password_updates(df, headers)
    save_results()

if __name__ == "__main__":
    main()
