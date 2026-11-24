import os
import random
import time

from typing import Literal

from google import genai
from google.genai import types
from groq import Groq
from pydantic import BaseModel, Field

MAX_POGINGEN_PER_MODEL = {
    "gemini-3.5-flash-lite": 2,
    "gemini-3.1-flash-lite": 2,
    "openai/gpt-oss-20b": 2,
    "qwen/qwen3.8-27b": 1,
    "gemini-3.8-flash": 1,
    "gemini-3.6-flash": 1,
}

MODELROUTE = [
    ("gemini", "gemini-3.5-flash-lite"),
    ("gemini", "gemini-3.1-flash-lite"),
    ("groq", "openai/gpt-oss-20b"),
    ("groq", "qwen/qwen3.8-27b"),
    ("gemini", "gemini-3.8-flash"),
    ("gemini", "gemini-3.6-flash"),
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

class GestructureerdAntwoord:
    def __init__(
        self,
        parsed
    ):
        self.parsed = parsed
        self.text = parsed.model_dump_json(
            ensure_ascii=False
        )

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

def roep_groq_model_aan(
    client,
    model,
    prompt
):
    schema = (
        Beoordelingen.model_json_schema()
    )

    completion = (
        client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Voer de beoordeling exact "
                        "volgens de instructies uit. "
                        "Geef uitsluitend JSON terug "
                        "dat aan het opgegeven schema "
                        "voldoet."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name":
                        "toezeggingenbeoordelingen",
                    "strict": False,
                    "schema": schema,
                },
            },
        )
    )

    inhoud = (
        completion
        .choices[0]
        .message
        .content
    )

    if not inhoud:
        raise ValueError(
            "Groq gaf geen antwoordtekst terug."
        )

    parsed = (
        Beoordelingen.model_validate_json(
            inhoud
        )
    )

    return GestructureerdAntwoord(
        parsed
    )

def roep_gemini_aan(
    gemini_client,
    groq_client,
    prompt
):
    laatste_fout = None

    for aanbieder, model in MODELROUTE:
        max_pogingen = (
            MAX_POGINGEN_PER_MODEL.get(
                model,
                1
            )
        )

        for poging in range(
            1,
            max_pogingen + 1
        ):
            try:
                print(
                    f"Model proberen: "
                    f"{aanbieder} | {model}"
                )

                if aanbieder == "gemini":
                    response = (
                        gemini_client
                        .models
                        .generate_content(
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

                elif aanbieder == "groq":
                    if groq_client is None:
                        print(
                            "Groq overslaan: "
                            "GROQ_API_KEY ontbreekt."
                        )
                        break

                    response = (
                        roep_groq_model_aan(
                            groq_client,
                            model,
                            prompt
                        )
                    )

                else:
                    raise ValueError(
                        f"Onbekende aanbieder: "
                        f"{aanbieder}"
                    )

                print(
                    f"Model geslaagd: "
                    f"{aanbieder} | {model}"
                )

                return (
                    response,
                    f"{aanbieder}:{model}"
                )

            except Exception as fout:
                laatste_fout = fout
                fouttekst = str(
                    fout
                ).lower()

                tijdelijk = (
                    "429" in fouttekst
                    or "503" in fouttekst
                    or "504" in fouttekst
                    or "404" in fouttekst
                    or "rate limit" in fouttekst
                    or "resource_exhausted"
                        in fouttekst
                    or "unavailable" in fouttekst
                    or "high demand" in fouttekst
                    or "deadline_exceeded"
                        in fouttekst
                    or "deadline exceeded"
                        in fouttekst
                    or "deadline expired"
                        in fouttekst
                    or "timeout" in fouttekst
                    or "timed out" in fouttekst
                    or "connection" in fouttekst
                    or "model not found"
                        in fouttekst
                    or "model_not_found"
                        in fouttekst
                    or "decommissioned"
                        in fouttekst
                )

                # Ongeldige JSON of een tijdelijke
                # schema-afwijking mag bij Groq ook
                # opnieuw worden geprobeerd.
                groq_outputfout = (
                    aanbieder == "groq"
                    and (
                        "validation error"
                            in fouttekst
                        or "json" in fouttekst
                        or "response_format"
                            in fouttekst
                    )
                )

                if (
                    not tijdelijk
                    and not groq_outputfout
                ):
                    raise

                print(
                    f"Tijdelijke modelfout met "
                    f"{aanbieder} | {model}. "
                    f"Poging {poging} van "
                    f"{max_pogingen}. "
                    f"Fout: {fout}"
                )

                if poging < max_pogingen:
                    wachttijd = (
                        15
                        + random.uniform(
                            0,
                            2
                        )
                    )

                    print(
                        f"{wachttijd:.1f} "
                        f"seconden wachten..."
                    )

                    time.sleep(
                        wachttijd
                    )

        print(
            f"{aanbieder} | {model} "
            f"blijft onbeschikbaar. "
            f"Volgend model proberen."
        )

    raise RuntimeError(
        "Alle Gemini- en Groq-modellen "
        "zijn tijdelijk onbeschikbaar. "
        f"Laatste fout: {laatste_fout}"
    )

def beoordeel_document(
    document,
    documenttekst,
    kandidaten
):
    gemini_api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY ontbreekt."
        )

    gemini_client = genai.Client(
        api_key=gemini_api_key,
        http_options=types.HttpOptions(
            timeout=90_000
        ),
    )

    groq_api_key = os.environ.get(
        "GROQ_API_KEY"
    )

    groq_client = (
        Groq(
            api_key=groq_api_key,
            timeout=90.0,
            max_retries=0,
        )
        if groq_api_key
        else None
    )


    prompt = maak_prompt(
        document,
        documenttekst,
        kandidaten
    )

    response, gebruikt_model = (
        roep_gemini_aan(
            gemini_client,
            groq_client,
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
