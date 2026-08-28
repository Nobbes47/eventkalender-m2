import os
import datetime
import requests
from bs4 import BeautifulSoup

# URL zum Metin2 Forenpost
URL = "https://board.de.metin2.gameforge.com/index.php?thread/90381-eventkalender/"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    # 1. Deutsche Monate für die Datumssuche definieren
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    heute = datetime.date.today()
    tag = heute.strftime("%d").lstrip("0") # Entfernt führende Null (z.B. "05" -> "5")
    monat_name = monate[heute.month - 1]
    
    such_datum = f"{tag}. {monat_name}" # Ergibt z.B. "28. August"
    
    # 2. Forenseite abrufen
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(URL, headers=headers)
    if response.status_code != 200:
        print(f"Fehler beim Laden der Seite: {response.status_code}")
        return

    # 3. HTML parsen
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Spezifischen Postinhalt anhand der Post-ID aus der URL finden
    post_content = soup.find("div", id="postRow-3360374") 
    if not post_content:
        # Fallback: Suche im gesamten Text, falls die ID sich geändert hat
        post_content = soup.find("div", class_="messageText")

    if not post_content:
        print("Forenbeitrag konnte nicht isoliert werden.")
        return

    # Textzeilen extrahieren
    text_lines = post_content.get_text(separator="\n").split("\n")
    
    # 4. Events filtern
    gefundene_events = []
    aktuelles_datum_aktiv = False

    for line in text_lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        # Prüfen, ob eine neue Datumszeile beginnt
        if any(m in line_clean for m in monate):
            if such_datum in line_clean:
                aktuelles_datum_aktiv = True
                gefundene_events.append(f"**📅 Events für {line_clean}:**")
            else:
                aktuelles_datum_aktiv = False # Ein anderes Datum hat begonnen
        
        # Wenn wir im heutigen Datum sind, nach Europe filtern
        if aktuelles_datum_aktiv and "europe" in line_clean.lower():
            gefundene_events.append(f"🔹 {line_clean}")

    # 5. Ergebnis an Discord senden
    if len(gefundene_events) > 1: # Mehr als nur die Überschrift
        nachricht = "\n".join(gefundene_events)
    else:
        nachricht = f"📅 **Metin2 Europe-Events ({such_datum}):** Heute wurden keine spezifischen Europe-Events im Forenpost gefunden."

    # Webhook absenden
    payload = {"content": nachricht}
    requests.post(WEBHOOK_URL, json=payload)
    print("Nachricht erfolgreich an Discord gesendet.")

if __name__ == "__main__":
    main()
