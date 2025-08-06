# User Provisioning mittels Abacus REST-API

Ein Python-basiertes Toolkit zur Automatisierung der Benutzer-, Passwort-
und Policy-Verwaltung über die Abacus REST-API. Alle Skripte
authentifizieren sich über OAuth2 und teilen sich zentrale Hilfsfunktionen.

## Projektstruktur

```
creation.py                 # führt alle Erstellungs- und Änderungs-Module sequenziell aus
deletion.py                 # führt die Lösch-Module sequenziell aus
utils/
    auth/                   # OAuth2-Authentifizierung und Tokenverwaltung
    Creation/               # Module zum Erstellen von Kategorien, (Service-)Benutzern und Policies
    Modification/           # Module zum Ändern von Benutzern und Passwörtern
    Delete/                 # Module zum Löschen von Benutzern, Policies und Kategorien
requirements.txt            # Python-Abhängigkeiten
```

Eingabedateien werden im Verzeichnis `_data/` erwartet. Ergebnisse und
Duplikate landen in `_data/results/`.

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

   Im Ordner `utils/auth/` muss die Datei `ClientSecret.txt` mit folgendem
   Aufbau vorhanden sein:

   ```
   <client_id>
   <client_secret>
   <base_url>  # z.B. http://localhost:40000
   ```

   > Diese Datei darf nicht in ein öffentliches Repository gelangen!

## Nutzung

1. **AbaReports exportieren und in `_data/` ablegen.**

2. **Erstellungs- und Änderungs-Workflow ausführen:**

   ```bash
   python creation.py
   ```

   Das Skript führt nacheinander folgende Module aus:

   - `utils.Creation.CreateCategory`
   - `utils.Creation.CreateServiceUsers`
   - `utils.Creation.CreateUsers`
   - `utils.Modification.ModifyPassword`
   - `utils.Modification.ModifyUsers`
   - `utils.Creation.CreateProgramPolicy`
   - `utils.Creation.CreateClientPolicy`

   Die Erstellung und Aktualisierung von Benutzern erfolgt asynchron und
   begrenzt parallele Requests für einen effizienteren Ablauf.

3. **Lösch-Workflow ausführen:**

   ```bash
   python deletion.py
   ```

   Führt die Module `DeleteUsers`, `DeleteProgrammPolicies`,
   `DeleteClientPolicies` und `DeleteCategories` aus.

4. **Einzelne Module starten:**

   ```bash
   python -m utils.Creation.CreateUsers
   ```

   Dies ist für jedes Modul in `utils/` möglich.

## API & Authentifizierung

Alle Module verwenden die Funktionen aus `utils/auth/Authentification.py`,
um einen OAuth2-Bearer-Token zu erhalten. Die Basis-URL und Credentials
werden aus `ClientSecret.txt` gelesen.

## Hinweise

- Eingabedaten liegen in `_data/` (JSON oder XLSX).
- Ergebnisse und Duplikatslisten werden in `_data/results/` gespeichert.
- Skripte loggen ausführlich über das Python-`logging`-Modul.

