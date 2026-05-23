import httpx

# TODO: replace with the actual API endpoint and params
API_URL = "https://api.example.com/flats"


async def fetch_listings(filters: dict) -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = client.get(API_URL, params=filters)
        response.raise_for_status()
        return response.json()
