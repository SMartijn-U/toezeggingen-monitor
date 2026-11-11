import os

from google import genai


def main():
    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY ontbreekt."
        )

    client = genai.Client(
        api_key=api_key
    )

    print("Beschikbare modellen opvragen...")

    geschikte_modellen = []

    for model in client.models.list():
        naam = model.name or ""

        if "flash" not in naam.lower():
            continue

        geschikte_modellen.append(naam)

    print("\nBESCHIKBARE FLASH-MODELLEN:")

    for naam in geschikte_modellen:
        print(naam)

    if not geschikte_modellen:
        raise RuntimeError(
            "Geen Flash-model beschikbaar."
        )
