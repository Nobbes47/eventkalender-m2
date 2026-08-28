import os
import datetime
import re
import requests
from bs4 import BeautifulSoup

# Wir nutzen die offizielle JSON-API-Schnittstelle des Forums für diesen Post
API_URL = "https://gameforge.com"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    if not WEBHOOK_URL:
        print("FEHLER: DISCORD_WEBHOOK_URL fehlt in den GitHub Secrets!")
        return

    # 1. Heutiges Datum bestimmen (z.B. "28. August")
    heute = datetime.date.today()
    tag = heute.strftime("%d").lstrip("0")
    
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    monat_name = monate[heute.month - 1]
    
    reg_heute = re.compile(f"^{tag}\\.\\s*{monat_name}", re.IGNORECASE)
    reg_irgendein_tag = re.compile(r"^\d+\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)", re.IGNORECASE)

    print(f"Rufe Foren-API auf. Suche nach Events für den: {tag}. {monat_name}")

    # 2. Daten direkt von der WoltLab-API abrufen
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Fehler beim Abruf der Foren-API: {e}")
        return

    # Die API liefert den Foren-Post direkt in einem sauberen Text-Feld aus
    html_content = data.get("data", {}).get("message", "")
    if not html_content:
        print("Konnte keinen Textinhalt aus der Foren-API lesen.")
        return

    # 3. HTML in saubere Textzeilen zerlegen
    soup = BeautifulSoup(html_content, "html.parser")
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
            continue
            
        # Endpunkt: Der nächste Kalendertag beginnt -> Suche beenden
        if im_heutigen_abschnitt and reg_irgendein_tag.match(clean_zeile):
            im_heutigen_abschnitt = False
            break
            
        if im_heutigen_abschnitt:
            event_block.append(clean_zeile)

    # 5. Events filtern (Ausschließen, was NUR für andere Server gilt)
    finale_events = []
    aktuelles_event = []
    
    def verarbeite_event(ev_lines):
        if not ev_lines:
            return
        event_text = " ".join(ev_lines).lower()
        if "nur germania und teutonia" in event_text:
            return
        
        # Übersichtliche Formatierung für Discord aufbauen
        title = ev_lines[0]
        details = ev_lines[1:]
        
        formatted = f"🔹 **{title}**\n" + "\n".join([f"   {d}" for d in details])
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

    # 6. Nachricht via Webhook an Discord senden
    if finale_events:
        nachricht = f"📅 **Metin2 Europe-Events für heute ({tag}. {monat_name}):**\n\n" + "\n\n".join(finale_events)
    else:
        nachricht = f"📅 **Metin2 Europe-Events ({tag}. {monat_name}):** Heute finden keine Europe-Events statt oder der Kalender wurde im Forum noch nicht eingetragen."

    try:
        res = requests.post(WEBHOOK_URL, json={"content": nachricht}, timeout=10)
        print(f"Discord-Webhook gesendet. Status-Code: {res.status_code}")
    except Exception as e:
        print(f"Fehler beim Senden des Discord-Webhooks: {e}")

if __name__ == "__main__":
    main()
