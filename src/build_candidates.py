import json
from pathlib import Path

from get_toezeggingen import (
    get_open_toezeggingen,
    get_recent_afgedane_toezeggingen,
    combineer_toezeggingen,
    get_relevante_activiteiten,
    vul_ontbrekende_activiteiten_aan,
    get_volgcommissie_actoren,
    get_commissies,
    get_actuele_vaste_commissies,
    maak_commissieslug,
    get_toezeggingen_per_commissie,
)

from get_kamerbrieven import (
    get_recente_documenten,
)

from document_text import (
    get_document_text,
)

from match_candidates import (
    rangschik_kandidaten,
)


OUTPUT_PATH = Path(
    "data/candidates.json"
)

AANTAL_DAGEN_DOCUMENTEN = 7
AANTAL_DAGEN_AFGEDAAN = 14
MAXIMUM_KANDIDATEN_PER_DOCUMENT = 10
MINIMUM_KANDIDAATSCORE = 0.05

def bouw_toezeggingen_per_commissie():
    print(
        "\nActuele en recent afgedane "
        "toezeggingen ophalen..."
    )

    actuele_toezeggingen = (
        get_open_toezeggingen()
    )

    recent_afgedaan = (
        get_recent_afgedane_toezeggingen(
            aantal_dagen=AANTAL_DAGEN_AFGEDAAN
        )
    )

    toezeggingen = combineer_toezeggingen(
        actuele_toezeggingen,
        recent_afgedaan
    )

    print(
        f"Gecombineerde set toezeggingen: "
        f"{len(toezeggingen)}"
    )

    print("\nActiviteiten ophalen...")

    activiteiten = (
        get_relevante_activiteiten()
    )

    activiteiten, uitgesloten_activiteitnummers = (
        vul_ontbrekende_activiteiten_aan(
            toezeggingen,
            activiteiten
        )
    )

    print("\nVolgcommissies ophalen...")

    volgcommissie_actoren = (
        get_volgcommissie_actoren()
    )

    print("\nCommissies ophalen...")

    commissies = get_commissies()

    vaste_commissies = (
        get_actuele_vaste_commissies(
            commissies
        )
    )

    print(
        f"Actuele vaste commissies: "
        f"{len(vaste_commissies)}"
    )

    toezeggingen_per_commissie = {}

    for commissie in vaste_commissies:
        afkorting = (
            commissie.get("Afkorting")
            or ""
        ).strip()

        slug = maak_commissieslug(
            commissie
        )

        if not afkorting or not slug:
            print(
                "WAARSCHUWING: commissie zonder "
                "bruikbare afkorting of slug:",
                commissie.get("Id")
            )
            continue

        print(
            f"\nSelectie maken voor "
            f"{afkorting} | {slug}..."
        )

        selectie = (
            get_toezeggingen_per_commissie(
                toezeggingen,
                activiteiten,
                volgcommissie_actoren,
                commissies,
                commissie_afkorting=slug,
                uitgesloten_activiteitnummers=(
                    uitgesloten_activiteitnummers
                ),
            )
        )

        toezeggingen_per_commissie[slug] = {
            "commissie_id": (
                commissie.get("Id")
            ),
            "commissie_afkorting": (
                afkorting
            ),
            "commissie_naam": (
                commissie.get("NaamNL")
                or commissie.get("NaamWebNL")
                or ""
            ).strip(),
            "commissie_slug": slug,
            "toezeggingen": selectie,
        }

        print(
            f"{afkorting} | {slug} | "
            f"{len(selectie)} toezeggingen"
        )

    totaal_selecties = sum(
        len(gegevens["toezeggingen"])
        for gegevens
        in toezeggingen_per_commissie.values()
    )

    unieke_toezeggingen = {
        toezegging.get("Nummer")
        for gegevens
        in toezeggingen_per_commissie.values()
        for toezegging
        in gegevens["toezeggingen"]
        if toezegging.get("Nummer")
    }

    print(
        f"\nTotaal commissieselecties: "
        f"{totaal_selecties}"
    )

    print(
        f"Unieke toezeggingen: "
        f"{len(unieke_toezeggingen)}"
    )

    return toezeggingen_per_commissie

def maak_kandidaat_record(
    document,
    kandidaat,
    positie
):
    toezegging = kandidaat["toezegging"]
    activiteit = toezegging.get(
        "Activiteit",
        {}
    )

    return {
        "positie": positie,
        "commissie_afkorting": (
            toezegging.get(
                "CommissieAfkorting"
            )
        ),
        "commissie_slug": (
            toezegging.get(
                "CommissieSlug"
            )
        ),
        "selectiereden": (
            toezegging.get(
                "Selectiereden"
            )
        ),
        "toezeggingnummer": (
            toezegging.get("Nummer")
        ),
        "status": toezegging.get("Status"),
        "toezeggingstekst": (
            toezegging.get("Tekst")
        ),
        "bewindspersoon": (
            toezegging.get("Naam")
        ),
        "ministerie": (
            toezegging.get("Ministerie")
        ),
        "activiteitnummer": (
            toezegging.get("ActiviteitNummer")
        ),
        "activiteitsoort": (
            activiteit.get("Soort")
        ),
        "activiteitonderwerp": (
            activiteit.get("Onderwerp")
        ),
        "datum_nakoming": (
            toezegging.get("DatumNakoming")
        ),
        "kamerbrief_nakoming": (
            toezegging.get("KamerbriefNakoming")
        ),
        "tfidf_score": round(
            kandidaat["similarity"],
            6
        ),
        "volledige_documentscore": round(
            kandidaat.get(
                "volledige_documentscore",
                kandidaat["similarity"]
            ),
            6
        ),
        "lokale_score": round(
            kandidaat.get(
                "lokale_score",
                0.0
            ),
            6
        ),
        "beste_blokindex": (
            kandidaat.get(
                "beste_blokindex"
            )
        ),
        "expliciete_verwijzing_selectie": (
            kandidaat.get(
                "expliciete_verwijzing",
                False
            )
        ),
        "genormaliseerde_nummermatch": (
            kandidaat.get(
                "genormaliseerde_nummermatch",
                False
            )
        ),
        "bonusredenen": (
            kandidaat.get(
                "bonusredenen",
                []
            )
        ),
        "bonus": round(
            kandidaat["bonus"],
            6
        ),
        "totale_score": round(
            kandidaat["score"],
            6
        ),
    }

def verwerk_documenten(
    documenten,
    toezeggingen_per_commissie
):
    resultaten = []
    fouten = []

    totaal = len(documenten)

    for index, document in enumerate(
        documenten,
        start=1
    ):
        nummer = (
            document.get("Nummer")
            or document.get("Id")
        )

        print(
            f"\nDocument {index}/{totaal}: "
            f"{nummer} | "
            f"{document.get('Soort')} | "
            f"{document.get('Onderwerp')}"
        )

        try:
            tekst = get_document_text(
                document
            )

            commissieresultaten = []

            for slug, commissiegegevens in (
                toezeggingen_per_commissie.items()
            ):
                commissie_id = (
                    commissiegegevens.get(
                        "commissie_id"
                    )
                )

                zaak_commissie_ids = set(
                    document.get(
                        "ZaakCommissieIds",
                        []
                    )
                )

                if not zaak_commissie_ids:
                    print(
                        "COMMISSIEFILTER:",
                        nummer,
                        "| geen zaakcommissies; "
                        "document overgeslagen"
                    )
                    break

                if (
                    not commissie_id
                    or commissie_id
                    not in zaak_commissie_ids
                ):
                    continue

                commissie_toezeggingen = (
                    commissiegegevens[
                        "toezeggingen"
                    ]
                )

                if not commissie_toezeggingen:
                    continue

                print(
                    "COMMISSIEOVERLAP:",
                    nummer,
                    "|",
                    commissiegegevens[
                        "commissie_afkorting"
                    ],
                    "| commissie-ID:",
                    commissie_id,
                    "| zaakcommissies:",
                    [
                        (
                            item.get(
                                "commissie_afkorting"
                            ),
                            item.get(
                                "rol"
                            ),
                        )
                        for item in document.get(
                            "ZaakCommissies",
                            []
                        )
                    ]
                )

                debug_geval = (
                    nummer == "2026D59502"
                    and slug == "ienw"
                )

                kandidaten = rangschik_kandidaten(
                    document,
                    tekst,
                    commissie_toezeggingen,
                    maximum=(
                        1000
                        if debug_geval
                        else MAXIMUM_KANDIDATEN_PER_DOCUMENT
                    )
                )

                if debug_geval:
                    print(
                        "\nDEBUG ALLE SCORES "
                        "2026D59502 | I&W:"
                    )

                    for debug_positie, kandidaat in enumerate(
                        kandidaten,
                        start=1
                    ):
                        toezegging = kandidaat.get(
                            "toezegging",
                            {}
                        )

                        print(
                            "DEBUG SCORE:",
                            debug_positie,
                            "|",
                            toezegging.get("Nummer"),
                            "| tfidf:",
                            round(
                                kandidaat.get(
                                    "similarity",
                                    0.0
                                ),
                                6
                            ),
                            "| bonus:",
                            round(
                                kandidaat.get(
                                    "bonus",
                                    0.0
                                ),
                                6
                            ),
                            "| totaal:",
                            round(
                                kandidaat.get(
                                    "score",
                                    0.0
                                ),
                                6
                            ),
                            "| volledig:",
                            round(
                                kandidaat.get(
                                    "volledige_documentscore",
                                    0.0
                                ),
                                6
                            ),
                            "| lokaal:",
                            round(
                                kandidaat.get(
                                    "lokale_score",
                                    0.0
                                ),
                                6
                            ),
                            "| bonusredenen:",
                            kandidaat.get(
                                "bonusredenen",
                                []
                            ),
                            "| status:",
                            toezegging.get("Status"),
                            "| tekst:",
                            toezegging.get("Tekst"),
                        )

                kandidaten = kandidaten[
                    :MAXIMUM_KANDIDATEN_PER_DOCUMENT
                ]

                kandidaten = [
                    kandidaat
                    for kandidaat in kandidaten
                    if kandidaat.get(
                        "score",
                        0.0
                    ) >= MINIMUM_KANDIDAATSCORE
                ]

                print(
                    "Kandidaten boven minimumscore:",
                    commissiegegevens[
                        "commissie_afkorting"
                    ],
                    "|",
                    nummer,
                    "| minimum:",
                    MINIMUM_KANDIDAATSCORE,
                    "| aantal:",
                    len(kandidaten)
                )
                
                kandidaat_records = [
                    maak_kandidaat_record(
                        document,
                        kandidaat,
                        positie
                    )
                    for positie, kandidaat
                    in enumerate(
                        kandidaten,
                        start=1
                    )
                ]

                if not kandidaat_records:
                    continue

                commissieresultaten.append({
                    "commissie_id": (
                        commissiegegevens[
                            "commissie_id"
                        ]
                    ),
                    "commissie_afkorting": (
                        commissiegegevens[
                            "commissie_afkorting"
                        ]
                    ),
                    "commissie_naam": (
                        commissiegegevens[
                            "commissie_naam"
                        ]
                    ),
                    "commissie_slug": slug,
                    "aantal_kandidaten": (
                        len(kandidaat_records)
                    ),
                    "kandidaten": kandidaat_records,
                })

                beste = kandidaat_records[0]

                print(
                    "Beste kandidaat:",
                    commissiegegevens[
                        "commissie_afkorting"
                    ],
                    "|",
                    beste["toezeggingnummer"],
                    "| score:",
                    beste["totale_score"]
                )

            resultaten.append({
                "document_id": (
                    document.get("Id")
                ),
                "documentnummer": (
                    document.get("Nummer")
                ),
                "documentsoort": (
                    document.get("Soort")
                ),
                "datum": (
                    document.get("Datum")
                ),
                "onderwerp": (
                    document.get("Onderwerp")
                ),
                "content_type": (
                    document.get("ContentType")
                ),
                "aantal_tekens": len(tekst),
                "commissies": (
                    commissieresultaten
                ),
            })

        except Exception as fout:
            fout_record = {
                "document_id": (
                    document.get("Id")
                ),
                "documentnummer": (
                    document.get("Nummer")
                ),
                "documentsoort": (
                    document.get("Soort")
                ),
                "onderwerp": (
                    document.get("Onderwerp")
                ),
                "fout": str(fout),
            }

            fouten.append(fout_record)

            print(
                f"FOUT bij {nummer}: {fout}"
            )

    return resultaten, fouten
    
def schrijf_resultaten(
    documenten,
    resultaten,
    fouten
):
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output = {
        "samenvatting": {
            "aantal_documenten": len(documenten),
            "succesvol_verwerkt": len(resultaten),
            "aantal_fouten": len(fouten),
            "maximum_kandidaten_per_document": (
                MAXIMUM_KANDIDATEN_PER_DOCUMENT
            ),
            "minimum_kandidaatscore": (
                MINIMUM_KANDIDAATSCORE
            ),
            "opmerking": (
                "De scores meten tekstuele overeenkomst "
                "en zijn geen waarschijnlijkheden."
            ),
        },
        "documenten": resultaten,
        "fouten": fouten,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"\nResultaten opgeslagen in: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    toezeggingen_per_commissie = (
        bouw_toezeggingen_per_commissie()
    )

    print("\nRecente documenten ophalen...")

    documenten = get_recente_documenten(
        aantal_dagen=AANTAL_DAGEN_DOCUMENTEN
    )

    print(
        f"Recente documenten: "
        f"{len(documenten)}"
    )

    resultaten, fouten = verwerk_documenten(
        documenten,
        toezeggingen_per_commissie
    )

    schrijf_resultaten(
        documenten,
        resultaten,
        fouten
    )

    print("\nSAMENVATTING:")

    print(
        f"Documenten gevonden: "
        f"{len(documenten)}"
    )

    print(
        f"Documenten verwerkt: "
        f"{len(resultaten)}"
    )

    print(
        f"Documenten met fout: "
        f"{len(fouten)}"
    )

    aantal_kandidaatparen = sum(
        len(commissie["kandidaten"])
        for document in resultaten
        for commissie in document[
            "commissies"
        ]
    )

    print(
        f"Kandidaatparen opgeslagen: "
        f"{aantal_kandidaatparen}"
    )
