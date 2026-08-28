import os
import requests
from bs4 import BeautifulSoup

URL = "https://gameforge.com"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    if not WEBHOOK_URL:
        print("FEHLER: DISCORD_WEBHOOK_URL fehlt.")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = requests.get(URL, headers=headers, timeout=15)
        print(f"Webseite geladen. Status-Code: {response.status_code}")
    except Exception as e:
        requests.post(WEBHOOK_URL, json={"content": f"❌ Netzwerkfehler beim Laden des Forums: {e}"})
        return

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Wir holen uns einfach den puren Text der gesamten Seite (ohne HTML)
    gesamter_text = soup.get_text(separator="\n")
    
    # Bereite eine Test-Nachricht für Discord vor
    linien = [line.strip() for line in gesamter_text.split("\n") if line.strip()]
    text_auszug = "\n".join(linien[:15]) # Die ersten 15 Zeilen Text
    
    # Prüfen ob wichtige Schlüsselwörter überhaupt im Text existieren
    status_check = f"**🔍 DIAGNOSE-BERICHT:**\n"
    status_check += f"• Status-Code der Seite: {response.status_code}\n"
    status_check += f"• Wort 'August' gefunden? {'JA' if 'august' in gesamter_text.lower() else 'NEIN'}\n"
    status_check += f"• Wort 'Europe' gefunden? {'JA' if 'europe' in gesamter_text.lower() else 'NEIN'}\n"
    status_check += f"• Wort 'Cloudflare' gefunden? {'JA' if 'cloudflare' in gesamter_text.lower() else 'NEIN'}\n\n"
    status_check += f"**📄 Text-Anfang der Seite (erste Zeilen):**\n```text\n{text_auszug[:800]}\n```"

    # Diagnose an Discord senden
    requests.post(WEBHOOK_URL, json={"content": status_check})
    print("Diagnose-Nachricht an Discord gesendet.")

if __name__ == "__main__":
    main()
