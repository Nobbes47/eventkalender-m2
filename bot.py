import os
import datetime
import requests
from bs4 import BeautifulSoup

URL = "https://gameforge.com"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    if not WEBHOOK_URL:
        print("FEHLER: DISCORD_WEBHOOK_URL nicht gesetzt.")
        return

    # 1. Heute-Datum in verschiedenen gängigen Foren-Formaten generieren
    heute = datetime.date.today()
    tag_ohne_null = heute.strftime("%d").lstrip("0")
    tag_mit_null =静态 = heute.strftime("%d")
    monat_mit_null = heute.strftime("%m")
    
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    monat_name = monate[heute.month - 1]
    
    # Suchmuster für die Datumszeile (z.B. "28. August" oder "28.08.")
    muster_1 = f"{tag_ohne_null}. {monat_name}"
    muster_2 = f"{tag_mit_null}.{monat_mit_null}."
    
    print(f"Suche im Forentext nach: '{muster_1}' oder '{muster_2}'")

    # 2. Forenseite abrufen
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler beim Abrufen der Forenseite: {e}")
        return

    # 3. HTML verarbeiten
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Fokus auf den Beitragscontainer (sucht gezielt nach Artikeln im Forum)
    posts = soup.find_all("article", class_="message")
    
    text_zeilen = []
    if posts:
        # Wir durchsuchen alle Posts auf der aktuellen Seite nach dem Datum
        for post in posts:
            content = post.find("div", class_="messageText")
            if content:
                text_zeilen.extend(content.get_text(separator="\n").split("\n"))
    else:
        # Fallback, falls sich Forenklassen geändert haben
        text_zeilen = soup.get_text(separator="\n").split("\n")

    # 4. Zeilen filtern und Events sammeln
    gefundene_events = []
    abschnitt_aktiv = False
    gefundenes_datum = ""

    for zeile in text_zeilen:
        clean_zeile = zeile.strip()
        if not clean_zeile:
            continue
        
        # Prüfen, ob eine Zeile dem heutigen Datum entspricht
        if (muster_1 in clean_zeile) or (muster_2 in clean_zeile):
            abschnitt_aktiv = True
            gefundenes_datum = clean_zeile
            gefundene_events.append(f"**📅 Events für {clean_zeile}:**")
            continue
            
        # Wenn der Abschnitt aktiv ist und ein NEUES Datum beginnt, stoppen wir das Einlesen
        if abschnitt_aktiv and any(m in clean_zeile for m in monate) and not any(m in clean_zeile for m in [muster_1, muster_2]):
            # Eine neue Datumsüberschrift beendet unseren heutigen Suchbereich
            if ":" not in clean_zeile and "server" not in clean_zeile.lower():
                abschnitt_aktiv = False

        # Wenn wir im heutigen Datumsblock sind und "Europe" vorkommt
        if abschnitt_aktiv and "europe" in clean_zeile.lower():
            gefundene_events.append(f"🔹 {clean_zeile}")

    # 5. Nachricht formatieren und absenden
    if len(gefundene_events) > 1:
        nachricht = "\n".join(gefundene_events)
    else:
        nachricht = f"📅 **Metin2 Europe-Events:** Für heute ({muster_1}) wurden keine expliziten Europe-Einträge im Kalender-Post gefunden."

    # Senden an Discord
    try:
        res = requests.post(WEBHOOK_URL, json={"content": nachricht}, timeout=10)
        print(f"An Discord übertragen. Status: {res.status_code}")
    except Exception as e:
        print(f"Fehler beim Senden des Discord-Webhooks: {e}")

if __name__ == "__main__":
    main()
