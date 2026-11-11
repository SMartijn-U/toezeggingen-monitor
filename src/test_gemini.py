import os

from google import genai
from pydantic import BaseModel


MODEL = "gemini-3.6-flash"


class TestBeoordeling(BaseModel):
    oordeel: str
    score: int
    motivering: str


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
        f"Structured output testen met: "
        f"{MODEL}"
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=(
            "Geef als oordeel exact 'test'. "
            "Geef als score exact 42. "
            "Leg in één korte zin uit dat "
            "dit een technische test is."
        ),
        config={
            "response_mime_type":
                "application/json",
            "response_schema":
                TestBeoordeling,
        },
    )

    resultaat = (
        TestBeoordeling.model_validate_json(
            response.text
        )
    )

    print(
        "Structured output geslaagd."
    )

    print(
        "Oordeel:",
        resultaat.oordeel
    )

    print(
        "Score:",
        resultaat.score
    )

    print(
        "Motivering:",
        resultaat.motivering
    )


if __name__ == "__main__":
    main()
