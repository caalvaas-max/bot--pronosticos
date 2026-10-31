import os
import httpx

api_key = os.getenv("BZZOIRO_API_KEY", "")
base_url = "https://sports.bzzoiro.com/api/v2"
headers = {"Authorization": f"Token {api_key}"}

endpoints = ["teams/", "matches/", "events/", "fixtures/", "predictions/"]

print("Probando API de Bzzoiro...\n")

for ep in endpoints:
    try:
        r = httpx.get(f"{base_url}/{ep}", headers=headers, timeout=10.0)
        print(f"Endpoint /{ep} -> Status: {r.status_code}")
        if r.status_code == 200:
            print(f"  ¡FUNCIONA! Datos: {str(r.json())[:150]}...")
    except Exception as e:
        print(f"Endpoint /{ep} -> Error: {e}")

print("\nPrueba terminada.")
