#  User Provisioning mittels Abacus REST-API

Ein Python-basiertes Toolset zur Automatisierung von Benutzer-, Passwort- und Policy-Provisionierung über die Abacus REST-API, inklusive Authentifizierung via OAuth2.

## Projektstruktur

```
--- CreateCategory.py              # Erstellt neue Kategorien via API
--- CreateClientPolicy.py         # Erstellt Client-spezifische Policies
--- CreateProgramPolicy.py        # Erstellt programmbezogene Policies
--- CreateUsers.py                # Erstellt Benutzer:innen asynchron
--- ModifyPassword.py             # Ändert Passwörter bestehender Benutzer:innen
--- ModifyUsers.py                # Aktualisiert Benutzerinformationen
--- auth/
    --- Authentification.py       # OAuth2-Authentifizierung und Tokenverwaltung
    --- ClientSecret.txt          # Sensible Zugangsdaten (nicht versionieren!)
--- data/
    --- OBT_Export_*.json/xlsx    # Eingabedaten für die Skripte
    --- results/
        --- *.xlsx                # Ergebnis- und Duplikatsdateien
--- requirements.txt              # Python-Abhängigkeiten
--- .gitignore                    # Ignoriert sensible/temporäre Dateien
```

## Setup & Installation

1. **Repository klonen und Abhängigkeiten installieren:**

```bash
git clone <repository-url>
cd <projektverzeichnis>
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

2. **Zugangsdaten einrichten:**

Im Ordner `auth/` muss die Datei `ClientSecret.txt` mit folgendem Aufbau vorhanden sein:

```
<client_id>
<client_secret>
<base_url>  # z.?B. http://localhost:40000
```
> ####   Achtung: Diese Datei sollte niemals in ein öffentliches Repository gelangen!



## Nutzung
> #### Die Reihenfolge der Schritte muss beachtet werden.

### 1. AbaReports exportieren und in data directory kopieren
Um die Python Files ausführen zu können, müssen zuerst die Exporte, welche mittels AbaReport erfolgen, in den Ordner "data" kopiert werden. 

### 2. Benutzerkategorien erstellen
```bash
python CreateCategory.py
```

Verwendet `data/OBT_Export_Create_Categories.json`.

### 3. Benutzer erstellen

```bash
python CreateUsers.py
```

Verwendet `data/OBT_Export_Create_Users.json` und speichert Ergebnisse in `data/results/`.

### 4. Benutzerinformationen ändern

```bash
python ModifyUsers.py
```
Verwendet `data/OBT_Export_Modify_Users.json` und speichert Ergebnisse in `data/results/`.

### 5. Passwort ändern

```bash
python ModifyPassword.py
```
Verwendet `data/OBT_Export_Modify_Passwords_Users.xlsx`


### 6. Policies erstellen

```bash
python CreateClientPolicy.py
python CreateProgramPolicy.py
```
Verwendet `data/OBT_Export_Create_ClientPolicies.xlsx` und `data/OBT_Export_Create_ProgrammPolicies.xlsx`

## API & Authentifizierung

Alle Skripte nutzen zentrale Authentifizierungsmethoden aus `auth/Authentification.py`, um einen Bearer Token über OAuth2 zu erhalten. Die Basis-URL und Credentials werden aus `ClientSecret.txt` gelesen.

## Hinweise

- Eingabedaten sind in `data/`, meist als `.json` oder `.xlsx`.
- Ergebnisse und mögliche Duplikate landen in `data/results/`.
- Skripte loggen ausführlich via `logging`.
