import os
import datetime
import re
import html
import requests
from bs4 import BeautifulSoup

# Wir nutzen den offiziellen RSS-Feed des Threads, um die Gameforge-Sperre zu umgehen
URL = "https://gameforge.com"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    if not WEBHOOK_URL:
        print("FEHLER: DISCORD_WEBHOOK_URL fehlt.")
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

    print(f"Lese RSS-Feed aus. Suche nach: '{tag}. {monat_name}'")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
    }

    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        requests.post(WEBHOOK_URL, json={"content": f"❌ Fehler beim Laden des RSS-Feeds: {e}"})
        return

    # 2. XML/RSS-Inhalt parsen
    soup = BeautifulSoup(response.content, "xml")
    
    # Wir nehmen den Inhalt des neuesten Beitrags (WoltLab speichert Forentext im <content:encoded> Tag)
    entries = soup.find_all("entry")
    if not entries:
        # Älteres RSS-Format Fallback (<item> statt <entry>)
        entries = soup.find_all("item")

    text_zeilen = []
    
    # Wir durchsuchen die neuesten Beiträge im Feed nach unserem Kalendertext
    for entry in entries:
        content_tag = entry.find("content:encoded") or entry.find("description")
        if content_tag:
            # HTML-Inhalt aus dem Feed in reinen Text umwandeln
            html_inhalt = content_tag.text
            clean_text = BeautifulSoup(html_inhalt, "html.parser").get_text(separator="\n")
            text_zeilen = clean_text.split("\n")
            
            # Wenn der Text dieses Beitrags den aktuellen Monat enthält, haben wir den Kalenderpost!
            if monat_name.lower() in clean_text.lower():
                print("Erfolgreich: Den aktuellen Kalender-Post im RSS-Feed gefunden.")
                break

    # 3. Textblock des heutigen Tages extrahieren
    event_block = []
    im_heutigen_abschnitt = False

    for zeile in text_zeilen:
        clean_zeile = html.unescape(zeile.strip())
        if not clean_zeile:
            continue
        
        # Startpunkt: Der heutige Tag matcht am Anfang der Zeile
        if reg_heute.match(clean_zeile):
            im_heutigen_abschnitt = True
            continue
            
        # Endpunkt: Der darauffolgende Tag beginnt -> Schleife abbrechen
        if im_heutigen_abschnitt and reg_irgendein_tag.match(clean_zeile):
            im_heutigen_abschnitt = False
            break
            
        if im_heutigen_abschnitt:
            event_block.append(clean_zeile)

    # 4. Events filtern (Unerwünschte Fremdserver-Events ausblenden)
    finale_events = []
    aktuelles_event = []
    
    def verarbeite_event(ev_lines):
        if not ev_lines:
            return
        event_text = " ".join(ev_lines).lower()
        if "nur germania und teutonia" in event_text:
            return
        
        # Text-Formatierung für Discord bauen
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

    # 5. Nachricht via Webhook an Discord übermitteln
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
