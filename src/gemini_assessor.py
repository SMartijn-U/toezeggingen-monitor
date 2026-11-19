import os
import random
import time

from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

MODELLEN = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
]

MAX_POGINGEN_PER_MODEL = {
    "gemini-3.5-flash-lite": 2,
    "gemini-3.8-flash": 1,
    "gemini-3.6-flash": 1,
}

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

Je mag uitsluitend de hieronder opgenomen
kandidaat-toezeggingen beoordelen.

Geef voor iedere aangeleverde kandidaat exact
één beoordeling terug.

Voeg nooit zelf een toezegging toe, ook niet
wanneer in het document een andere toezegging
expliciet wordt genoemd.

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
    Gebruik alleen bewijsfragmenten die
    daadwerkelijk nodig zijn om het oordeel
    te onderbouwen.

12. Ieder bewijsfragment moet een EXACTE,
    LETTERLIJKE en AANEENGESLOTEN passage
    uit het document zijn.

    Neem de passage exact over zoals deze
    in het document staat.

    VERBODEN:
    - een passage inkorten met "..." of "…";
    - woorden of zinnen uit een passage
      weglaten;
    - meerdere losse passages samenvoegen;
    - tekst parafraseren;
    - spelling, interpunctie of formulering
      corrigeren;
    - zelf woorden aan het bewijsfragment
      toevoegen.

    Als een relevante passage te lang is,
    kies dan een kortere aaneengesloten
    passage die op zichzelf voldoende bewijs
    levert.

    Als geen geschikt letterlijk
    bewijsfragment aanwezig is, geef dan
    geen bewijsfragment voor dat onderdeel.


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
    prompt
):
    laatste_fout = None

    for model in MODELLEN:
        max_pogingen = (
            MAX_POGINGEN_PER_MODEL.get(
                model,
                1
            )
        )

        print(
            f"Gemini-model proberen: {model}"
        )

        for poging in range(
            1,
            max_pogingen + 1
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
                    or "resource_exhausted" in fouttekst
                    or "timeout" in fouttekst
                    or "timed out" in fouttekst
                )

                if not tijdelijk:
                    raise

                print(
                    f"Tijdelijke Gemini-fout "
                    f"met {model}. "
                    f"Poging {poging} van "
                    f"{max_pogingen}."
                )

                if poging < max_pogingen:
                    wachttijd = (
                        15
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
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=90_000
        ),
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
