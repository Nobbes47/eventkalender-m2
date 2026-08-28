import os
import datetime
import requests
from bs4 import BeautifulSoup

URL = "https://gameforge.com"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    if not WEBHOOK_URL:
        print("FEHLER: DISCORD_WEBHOOK_URL ist nicht gesetzt.")
        return

    # 1. Heutiges und morgiges Datum berechnen (für die Block-Eingrenzung)
    heute = datetime.date.today()
    morgen = heute + datetime.timedelta(days=1)
    
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    
    such_heute = f"{heute.strftime('%d').lstrip('0')}. {monate[heute.month - 1]}"
    such_morgen = f"{morgen.strftime('%d').lstrip('0')}. {monate[morgen.month - 1]}"
    
    print(f"Suche nach Block ab: '{such_heute}' bis: '{such_morgen}'")

    # 2. Forenseite abrufen
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler beim Abrufen der Webseite: {e}")
        return

    # 3. HTML Textzeilen extrahieren
    soup = BeautifulSoup(response.text, "html.parser")
    posts = soup.find_all("article", class_="message")
    
    text_zeilen = []
    if posts:
        for post in posts:
            content = post.find("div", class_="messageText")
            if content:
                text_zeilen.extend(content.get_text(separator="\n").split("\n"))
    if not text_zeilen:
        text_zeilen = soup.get_text(separator="\n").split("\n")

    # 4. Block-basiertes Auslesen
    event_block = []
    im_heutigen_abschnitt = False

    for zeile in text_zeilen:
        clean_zeile = zeile.strip()
        if not clean_zeile:
            continue
        
        # Startpunkt: Der heutige Tag wurde gefunden
        if clean_zeile.startswith(such_heute):
            im_heutigen_abschnitt = True
            continue
            
        # Endpunkt: Der morgige Tag beginnt -> Schleife abbrechen
        if im_heutigen_abschnitt and clean_zeile.startswith(such_morgen):
            im_heutigen_abschnitt = False
            break
            
        # Wenn wir uns im heutigen Block befinden, Zeilen sammeln
        if im_heutigen_abschnitt:
            event_block.append(clean_zeile)

    # 5. Events filtern (Ausschließen, was NUR für Germania/Teutonia ist)
    finale_events = []
    aktuelles_event = []
    
    # Hilfsfunktion, um ein gesammeltes Event zu prüfen und hinzuzufügen
    def verarbeite_event(ev_lines):
        if not ev_lines:
            return
        # Verbinde die Zeilen des Events zu einem Textblock für die Filterprüfung
        event_text = " ".join(ev_lines).lower()
        # Falls es explizit NUR für die anderen Server ist, ignorieren wir es
        if "nur germania und teutonia" in event_text:
            return
        
        # Formatiere das Event hübsch für Discord
        formatted = f"🔹 **{ev_lines[0]}**\n"
        for sub_line in ev_lines[1:]:
            formatted += f"   {sub_line}\n"
        finale_events.append(formatted)

    for line in event_block:
        # Sobald eine Zeile mit "Event " beginnt, startet ein neuer Eintrag
        if line.lower().startswith("event "):
            verarbeite_event(aktuelles_event)
            aktuelles_event = [line]
        elif line.lower() == "nichts":
            finale_events.append("🔹 Heute finden keine geplanten Events statt.")
        else:
            if aktuelles_event:
                aktuelles_event.append(line)
                
    # Das letzte Event der Schleife verarbeiten
    verarbeite_event(aktuelles_event)

    # 6. Discord-Nachricht zusammenbauen
    if finale_events:
        nachricht = f"📅 **Metin2 Europe-Events für heute ({such_heute}):**\n\n" + "\n".join(finale_events)
    else:
        nachricht = f"📅 **Metin2 Europe-Events ({such_heute}):** Für heute wurden keine passenden Einträge im Kalender gefunden."

    # Webhook absenden
    try:
        res = requests.post(WEBHOOK_URL, json={"content": nachricht}, timeout=10)
        print(f"An Discord übertragen. Status: {res.status_code}")
    except Exception as e:
        print(f"Fehler beim Senden des Discord-Webhooks: {e}")

if __name__ == "__main__":
    main()
