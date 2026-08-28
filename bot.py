import os
import datetime
import re
import requests
from bs4 import BeautifulSoup

# Verwende die direkte URL zum Thread
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
    
    # Suchmuster: Findet "28. August", "28.August", "28.  August" etc.
    reg_heute = re.compile(f"^{tag}\\.\\s*{monat_name}", re.IGNORECASE)
    # Suchmuster für irgendeinen anderen Tag (um das Ende des Blocks zu erkennen)
    reg_irgendein_tag = re.compile(r"^\d+\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)", re.IGNORECASE)

    print(f"Suche im Forum nach Block für Tag: '{tag}. {monat_name}'")

    # 2. Forenseite mit Browser-Einstellungen und Sprach-Cookie abrufen
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    # Der Cookie sorgt dafür, dass das WoltLab-Forum uns die deutsche Ansicht liefert
    cookies = {
        "wcf_languageID": "1" 
    }

    try:
        response = requests.get(URL, headers=headers, cookies=cookies, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler beim Abrufen der Webseite: {e}")
        return

    # 3. HTML parsen und Zeilen isolieren
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Suche gezielt nach Forenbeiträgen (WoltLab nutzt <article class="message">)
    posts = soup.find_all("article", class_="message")
    
    text_zeilen = []
    if posts:
        # Wir nehmen den allerletzten Post auf der Seite (das ist meist der neueste Kalender)
        letzter_post = posts[-1]
        content = letzter_post.find("div", class_="messageText")
        if content:
            text_zeilen = content.get_text(separator="\n").split("\n")
            print("Erfolgreich den Inhalt des letzten Forenbeitrags isoliert.")
            
    # Fallback, falls die Beitragsstruktur nicht greift
    if not text_zeilen:
        print("Fallback: Nutze gesamten Seitentext.")
        text_zeilen = soup.get_text(separator="\n").split("\n")

    # 4. Textblock des heutigen Tages ausschneiden
    event_block = []
    im_heutigen_abschnitt = False

    for zeile in text_zeilen:
        clean_zeile = zeile.strip()
        if not clean_zeile:
            continue
        
        # Wenn die Zeile mit unserem heutigen Tag matcht
        if reg_heute.match(clean_zeile):
            im_heutigen_abschnitt = True
            print(f"Startpunkt im Forum gefunden: {clean_zeile}")
            continue
            
        # Wenn der Abschnitt aktiv ist und ein NEUER Tag beginnt -> Abbrechen
        if im_heutigen_abschnitt and reg_irgendein_tag.match(clean_zeile):
            print(f"Endpunkt erreicht (Nächster Tag beginnt): {clean_zeile}")
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
        
        # Hübsche Formatierung bauen
        formatted = f"🔹 **{ev_lines[0]}**\n"
        for sub_line in ev_lines[1:]:
            formatted += f"   {sub_line}\n"
        finale_events.append(formatted)

    for line in event_block:
        if line.lower().startswith("event "):
            verarbeite_event(aktuelles_event)
            aktuelles_event = [line]
        elif line.lower() == "nichts":
            finale_events.append("🔹 Heute finden keine geplanten Events statt.")
        else:
            if aktuelles_event:
                aktuelles_event.append(line)
                
    verarbeite_event(aktuelles_event)

    # 6. Discord-Nachricht absenden
    if finale_events:
        nachricht = f"📅 **Metin2 Europe-Events für heute ({tag}. {monat_name}):**\n\n" + "\n".join(finale_events)
    else:
        nachricht = f"📅 **Metin2 Europe-Events ({tag}. {monat_name}):** Heute finden keine Europe-Events statt oder der Kalender wurde im Forum noch nicht eingetragen."

    try:
        res = requests.post(WEBHOOK_URL, json={"content": nachricht}, timeout=10)
        print(f"An Discord übertragen. Status-Code: {res.status_code}")
    except Exception as e:
        print(f"Fehler beim Senden an Discord: {e}")

if __name__ == "__main__":
    main()
