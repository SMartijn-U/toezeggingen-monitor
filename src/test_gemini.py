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

        if "flash" in naam.lower():
            geschikte_modellen.append(naam)

    print("\nBESCHIKBARE FLASH-MODELLEN:")

    if not geschikte_modellen:
        print("Geen Flash-modellen gevonden.")
        return

    for naam in geschikte_modellen:
        print(naam)


if __name__ == "__main__":
    main()
