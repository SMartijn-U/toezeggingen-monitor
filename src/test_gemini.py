import os

from google import genai


MODEL = "gemini-3.6-flash"


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

    print(
        f"Gemini-model testen: {MODEL}"
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=(
            "Antwoord uitsluitend met "
            "het woord: werkt"
        ),
    )

    print(
        "Gemini-verbinding geslaagd."
    )

    print(
        "Antwoord:",
        response.text
    )


if __name__ == "__main__":
    main()
