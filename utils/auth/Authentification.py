import requests
import base64
import logging

# Konfiguriere das Logging-Format für alle Ausgaben
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def read_client_credentials(file_path="utils/auth/ClientSecret.txt"):
    """
    Liest Client-ID, Client-Secret und Basis-URL aus einer Textdatei im gegebenen Pfad.
    Die Datei muss mindestens drei Zeilen enthalten:
    1. Zeile: Client-ID
    2. Zeile: Client-Secret
    3. Zeile: Basis-URL der API
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            if len(lines) < 3:
                logging.error("Die Datei '%s' muss mindestens drei Zeilen enthalten.", file_path)
                return None, None, None
            client_id = lines[0].strip()
            client_secret = lines[1].strip()
            base_url = lines[2].strip().rstrip("/")
            return client_id, client_secret, base_url
    except FileNotFoundError:
        logging.error("Die Datei '%s' wurde nicht gefunden.", file_path)
        return None, None, None
    except Exception as e:
        logging.error("Fehler beim Lesen der Datei '%s': %s", file_path, e)
        return None, None, None

def get_bearer_token():
    """
    Fordert einen OAuth2-Bearer-Token von der API an.
    Verwendet Client-ID und Secret, die aus der Konfigurationsdatei gelesen werden.
    Gibt das Access-Token als String zurück oder None bei Fehlern.
    """
    client_id, client_secret, base_url = read_client_credentials()
    if not all([client_id, client_secret, base_url]):
        logging.error("Ungültige Konfigurationsdaten.")
        return None

    token_url = f"{base_url}/oauth/oauth2/v1/token"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    try:
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            logging.error("Tokenfehler (%s): %s", response.status_code, response.text)
            return None
    except requests.RequestException as e:
        logging.error("Netzwerkfehler: %s", e)
        return None

def get_auth_headers():
    """
    Erzeugt ein Dictionary mit Authorization-Header für API-Aufrufe.
    Holt sich dazu den Bearer-Token mit get_bearer_token().
    """
    token = get_bearer_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return None

def get_base_url():
    """
    Liefert die Basis-URL für die API aus der Konfigurationsdatei.
    """
    _, _, base_url = read_client_credentials()
    return base_url

if __name__ == "__main__":
    # Testausführung: Prüft, ob ein Token erfolgreich generiert werden kann.
    token = get_bearer_token()
    if token:
        logging.info("Bearer Token erfolgreich erhalten.")
    else:
        logging.error("Token konnte nicht abgerufen werden.")
