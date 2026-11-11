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

    response = client.models.generate_content(
        model="gemini-3.8-flash",
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
