import os
import datetime
import re
import requests
from bs4 import BeautifulSoup

# Die echte Foren-URL zu Ihrem Eventkalender
FORUM_URL = "https://gameforge.com"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
API_KEY = os.getenv("SCRAPERAPI_KEY")

def main():
    if not WEBHOOK_URL or not API_KEY:
        print("FEHLER: DISCORD_WEBHOOK_URL oder SCRAPERAPI_KEY fehlt in den Secrets!")
        return

    # 1. Heutiges Datum bestimmen (z.B. "28. August")
    heute = datetime.date.today()
    tag = heute.strftime("%d").lstrip("0")
    
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    monat_name = monate[heute.month - 1]
    
    reg_heute = re.compile(f"^{tag}\\.\\s*{monat_name}", re.IGNORECASE)
    reg_irgendein_tag = re.compile(r"^\d+\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)", re.IGNORECASE)

    print(f"Rufe Forenseite über ScraperAPI ab. Suche nach: '{tag}. {monat_name}'")

    # 2. Anfrage über den ScraperAPI-Proxy tunneln
    proxy_url = f"http://scraperapi.com?api_key={API_KEY}&url={FORUM_URL}"
    
    try:
        response = requests.get(proxy_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler beim Abruf über ScraperAPI: {e}")
        return

    # 3. HTML verarbeiten
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Gezielte Suche nach dem von Ihnen angegebenen Post (ID: 3360374)
    target_post = soup.find("article", id="post3360374") or soup.find("div", id="postRow-3360374")

    text_zeilen = []
    if target_post:
        content = target_post.find("div", class_="messageText")
        if content:
            text_zeilen = content.get_text(separator="\n").split("\n")
            print("Erfolgreich: Den spezifischen Kalender-Post isoliert.")
            
    if not text_zeilen:
        print("Fallback: Scanne gesamten Seitentext, da Post-ID im HTML fehlt.")
        text_zeilen = soup.get_text(separator="\n").split("\n")

    # 4. Textblock des heutigen Tages extrahieren
    event_block = []
    im_heutigen_abschnitt = False

    for zeile in text_zeilen:
        clean_zeile = zeile.strip()
        if not clean_zeile:
            continue
        
        if reg_heute.match(clean_zeile):
            im_heutigen_abschnitt = True
            continue
            
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
        
        # Schöne Formatierung für Discord aufbauen
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
        requests.post(WEBHOOK_URL, json={"content": nachricht}, timeout=10)
        print("Discord-Webhook erfolgreich gesendet.")
    except Exception as e:
        print(f"Fehler beim Senden des Discord-Webhooks: {e}")

if __name__ == "__main__":
    main()
