import os
import datetime
import re
import requests
from bs4 import BeautifulSoup

# Wir rufen direkt den exakten Post über seine ID ab, um Foren-Weiterleitungen zu umgehen
URL = "https://gameforge.com"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    if not WEBHOOK_URL:
        print("FEHLER: DISCORD_WEBHOOK_URL ist nicht gesetzt.")
        return

    # 1. Heutiges Datum bestimmen
    heute = datetime.date.today()
    tag = heute.strftime("%d").lstrip("0")
    
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    monat_name = monate[heute.month - 1]
    
    # Flexible Regex-Muster für den Zeilenabgleich
    reg_heute = re.compile(f"^{tag}\\.\\s*{monat_name}", re.IGNORECASE)
    reg_irgendein_tag = re.compile(r"^\d+\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)", re.IGNORECASE)

    print(f"Starte Scraper. Suche nach Kalender-Einträgen für den {tag}. {monat_name}...")

    # 2. Forenseite abrufen
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler beim Abrufen der Webseite: {e}")
        return

    # 3. HTML verarbeiten
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Gezielte Suche nach dem von Ihnen angegebenen Post (ID: 3360374)
    target_post = soup.find("article", id="post3360374")
    if not target_post:
        # Fallback auf den Beitragscontainer der WoltLab-Forensoftware
        target_post = soup.find("div", id="postRow-3360374")

    text_zeilen = []
    if target_post:
        content = target_post.find("div", class_="messageText")
        if content:
            text_zeilen = content.get_text(separator="\n").split("\n")
            print("Erfolgreich: Den spezifischen Kalender-Post (ID 3360374) isoliert.")
            
    # Letzter Rettungsanker: Falls IDs geblockt werden, den gesamten Text durchsuchen
    if not text_zeilen:
        print("Hinweis: Post-ID wurde nicht gefunden. Scanne gesamten Seitentext...")
        text_zeilen = soup.get_text(separator="\n").split("\n")

    # 4. Textblock des heutigen Tages extrahieren
    event_block = []
    im_heutigen_abschnitt = False

    for zeile in text_zeilen:
        clean_zeile = zeile.strip()
        if not clean_zeile:
            continue
        
        # Startpunkt: Der heutige Tag matcht am Anfang der Zeile
        if reg_heute.match(clean_zeile):
            im_heutigen_abschnitt = True
            print(f"-> Heute-Block im Forentext gefunden bei Zeile: '{clean_zeile}'")
            continue
            
        # Endpunkt: Der darauffolgende Tag beginnt -> Schleife abbrechen
        if im_heutigen_abschnitt and reg_irgendein_tag.match(clean_zeile):
            im_heutigen_abschnitt = False
            break
            
        if im_heutigen_abschnitt:
            event_block.append(clean_zeile)

    # 5. Events filtern (Unerwünschte Fremdserver-Events wie Germania/Teutonia löschen)
    finale_events = []
    aktuelles_event = []
    
    def verarbeite_event(ev_lines):
        if not ev_lines:
            return
        event_text = " ".join(ev_lines).lower()
        if "nur germania und teutonia" in event_text:
            return
        
        # Schöne Text-Aufbereitung für Discord
        formatted = f"🔹 **{ev_lines[0]}**\n"
        for sub_line in ev_lines[1:]:
            formatted += f"   {sub_line}\n"
        finale_events.append(formatted)

    for line in event_block:
        if line.lower().startswith("event "):
            verarbeite_event(aktuelles_event)
            aktuelles_event = [line]
        elif line.lower() == "nichts":
            finale_events.append("🔹 Heute finden laut Kalender keine geplanten Events statt.")
        else:
            if aktuelles_event:
                aktuelles_event.append(line)
                
    verarbeite_event(aktuelles_event)

    # 6. Nachricht via Webhook an Discord übermitteln
    if finale_events:
        nachricht = f"📅 **Metin2 Europe-Events für heute ({tag}. {monat_name}):**\n\n" + "\n".join(finale_events)
    else:
        nachricht = f"📅 **Metin2 Europe-Events ({tag}. {monat_name}):** Heute finden keine Europe-Events statt oder der Kalender wurde im Forum noch nicht eingetragen."

    try:
        res = requests.post(WEBHOOK_URL, json={"content": nachricht}, timeout=10)
        print(f"Discord-Webhook gesendet. Status-Code: {res.status_code}")
    except Exception as e:
        print(f"Fehler beim Senden des Discord-Webhooks: {e}")

if __name__ == "__main__":
    main()
