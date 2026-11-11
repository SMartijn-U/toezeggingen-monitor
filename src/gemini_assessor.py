import os
import random
import time

from typing import Literal

from google import genai
from pydantic import BaseModel, Field


MODELLEN = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]


class Beoordeling(BaseModel):
    toezeggingnummer: str

    oordeel: Literal[
        "zeker_afgedaan",
        "zeer_waarschijnlijk_afgedaan",
        "waarschijnlijk_afgedaan",
        "mogelijk_deels_afgedaan",
        "waarschijnlijk_niet_afgedaan",
        "niet_afgedaan",
    ]

    expliciete_verwijzing: bool

    gedekte_onderdelen: list[str]

    ontbrekende_onderdelen: list[str]

    bewijsfragmenten: list[str]

    motivering: str


class Beoordelingen(BaseModel):
    beoordelingen: list[Beoordeling]


def maak_prompt(
    document,
    documenttekst,
    kandidaten
):
    kandidaattekst = []

    for kandidaat in kandidaten:
        kandidaattekst.append(
            "\n".join([
                (
                    "TOEZEGGINGNUMMER: "
                    f"{kandidaat['toezeggingnummer']}"
                ),
                (
                    "STATUS REGISTRATIE: "
                    f"{kandidaat['status']}"
                ),
                (
                    "TOEZEGGING: "
                    f"{kandidaat['toezeggingstekst']}"
                ),
                (
                    "ACTIVITEIT: "
                    f"{kandidaat.get('activiteitonderwerp')}"
                ),
                "---",
            ])
        )

    kandidaten_blok = "\n".join(
        kandidaattekst
    )

    return f"""
Je beoordeelt mogelijke afdoeningen van
toezeggingen aan de Tweede Kamer.

Je krijgt één openbaar parlementair document
en een lijst met kandidaat-toezeggingen.

Beoordeel IEDERE toezegging afzonderlijk.

BELANGRIJKE REGELS:

1. Zoek niet alleen naar het toezeggingnummer.
   Een toezegging kan tekstueel worden afgedaan
   zonder dat het nummer wordt genoemd.

2. Bepaal welke concrete informatie, handeling,
   rapportage, reactie of ander product is
   toegezegd.

3. Controleer ieder wezenlijk onderdeel van
   samengestelde toezeggingen afzonderlijk.

4. Een toezegging is alleen "zeker_afgedaan"
   wanneer alle wezenlijke onderdelen aantoonbaar
   in het document worden geleverd.

5. Wanneer een wezenlijk onderdeel ontbreekt,
   mag het oordeel niet "zeker_afgedaan" zijn.

6. Wanneer slechts een deel wordt behandeld,
   gebruik "mogelijk_deels_afgedaan".

7. Wanneer het document alleen aankondigt dat
   de informatie later komt, is de toezegging
   niet afgedaan.

8. Een algemene thematische overeenkomst is
   onvoldoende.

9. Baseer het oordeel uitsluitend op de tekst
   van het hieronder opgenomen document.

10. De huidige administratieve status van de
    toezegging is alleen achtergrondinformatie.
    Neem NIET aan dat een toezegging afgedaan is
    omdat de status "Afgedaan" luidt.

11. Geef maximaal drie bewijsfragmenten.

12. Ieder bewijsfragment moet een KORTE,
    LETTERLIJKE passage uit het document zijn.
    Verzin, parafraseer of corrigeer het
    bewijsfragment niet.

DOCUMENT

Nummer:
{document.get("documentnummer")}

Soort:
{document.get("documentsoort")}

Datum:
{document.get("datum")}

Onderwerp:
{document.get("onderwerp")}

VOLLEDIGE DOCUMENTTEKST

{documenttekst}

KANDIDAAT-TOEZEGGINGEN

{kandidaten_blok}
"""

def roep_gemini_aan(
    client,
    prompt,
    max_pogingen_per_model=2
):
    laatste_fout = None

    for model in MODELLEN:
        print(
            f"Gemini-model proberen: {model}"
        )

        for poging in range(
            1,
            max_pogingen_per_model + 1
        ):
            try:
                response = (
                    client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config={
                            "response_mime_type":
                                "application/json",
                            "response_schema":
                                Beoordelingen,
                        },
                    )
                )

                print(
                    f"Gemini geslaagd met: "
                    f"{model}"
                )

                return response, model

            except Exception as fout:
                laatste_fout = fout

                fouttekst = str(fout).lower()

                tijdelijk = (
                    "503" in fouttekst
                    or "unavailable" in fouttekst
                    or "high demand" in fouttekst
                    or "429" in fouttekst
                    or "resource_exhausted"
                    in fouttekst
                )

                if not tijdelijk:
                    raise

                print(
                    f"Tijdelijke Gemini-fout "
                    f"met {model}. "
                    f"Poging {poging} van "
                    f"{max_pogingen_per_model}."
                )

                if (
                    poging
                    < max_pogingen_per_model
                ):
                    wachttijd = (
                        5 * (2 ** (poging - 1))
                        + random.uniform(0, 2)
                    )

                    print(
                        f"{wachttijd:.1f} "
                        f"seconden wachten..."
                    )

                    time.sleep(
                        wachttijd
                    )

        print(
            f"{model} blijft onbeschikbaar. "
            f"Fallbackmodel proberen."
        )

    raise RuntimeError(
        "Alle Gemini-modellen zijn "
        "tijdelijk onbeschikbaar. "
        f"Laatste fout: {laatste_fout}"
    )

def beoordeel_document(
    document,
    documenttekst,
    kandidaten
):
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

    prompt = maak_prompt(
        document,
        documenttekst,
        kandidaten
    )

    response, gebruikt_model = (
        roep_gemini_aan(
            client,
            prompt
        )
    )

    resultaat = (
        Beoordelingen.model_validate_json(
            response.text
        )
    )

    print(
        f"Beoordeling uitgevoerd met: "
        f"{gebruikt_model}"
    )

    return resultaat
