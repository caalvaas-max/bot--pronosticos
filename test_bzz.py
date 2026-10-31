import os
import httpx
import json

api_key = os.getenv("BZZOIRO_API_KEY", "")
if not api_key:
    print("❌ ERROR: La variable BZZOIRO_API_KEY está vacía. Haz el 'export' de nuevo.")
    exit()

url = "https://sports.bzzoiro.com/api/v2/predictions/"
headers = {
    "Authorization": f"Token {api_key}",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

print("Consultando a Bzzoiro...")
r = httpx.get(url, headers=headers)

print(f"Status Code: {r.status_code}")

if r.status_code == 200:
    try:
        data = r.json()
        results = data.get("results", [])
        print(f"✅ ¡Éxito! Partidos encontrados: {len(results)}")
        for p in results[:3]:
            ev = p.get("event", {})
            h = ev.get('home_team', ev.get('home', 'Local'))
            a = ev.get('away_team', ev.get('away', 'Visita'))
            print(f" - {h} vs {a}")
    except Exception as e:
        print("❌ Error parseando JSON:", e)
else:
    print("❌ Respuesta del servidor:")
    print(r.text[:300]) # Mostrar los primeros 300 caracteres del error
