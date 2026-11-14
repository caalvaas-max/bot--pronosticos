import os, httpx, asyncio
from dotenv import load_dotenv
load_dotenv()

async def test():
    print("--- Probando FootballSoccerAPI ---")
    key = os.getenv("FOOTBALLSOCCER_API_KEY")
    if key:
        async with httpx.AsyncClient() as c:
            try:
                r = await c.get("https://api.footballsoccerapi.com/v1/matches?limit=1", headers={"X-API-Key": key})
                print(f"Status: {r.status_code}")
                print(f"Respuesta: {r.text[:100]}...\n")
            except Exception as e:
                print(f"Error: {e}\n")

    print("--- Probando 5DollarFootballAPI ---")
    key2 = os.getenv("FIVEDOLLAR_API_KEY")
    if key2:
        async with httpx.AsyncClient() as c:
            try:
                r = await c.get("https://api.5dollarfootballapi.com/v1/leagues", headers={"Authorization": f"Bearer {key2}"})
                print(f"Status: {r.status_code}")
                print(f"Respuesta: {r.text[:100]}...\n")
            except Exception as e:
                print(f"Error: {e}\n")

asyncio.run(test())
