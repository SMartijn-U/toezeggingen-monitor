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
    get_ienw_toezeggingen,
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
MAXIMUM_KANDIDATEN_PER_DOCUMENT = 15


def bouw_ienw_toezeggingen():
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

    activiteiten = (
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

    print("\nIenW-selectie maken...")

    ienw = get_ienw_toezeggingen(
        toezeggingen,
        activiteiten,
        volgcommissie_actoren,
        commissies
    )

    print(
        f"Te onderzoeken IenW-toezeggingen: "
        f"{len(ienw)}"
    )

    return ienw


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
    toezeggingen
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

            kandidaten = rangschik_kandidaten(
                document,
                tekst,
                toezeggingen,
                maximum=(
                    MAXIMUM_KANDIDATEN_PER_DOCUMENT
                )
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
                "kandidaten": kandidaat_records,
            })

            if kandidaat_records:
                beste = kandidaat_records[0]

                print(
                    "Beste kandidaat:",
                    beste["toezeggingnummer"],
                    "| score:",
                    beste["totale_score"]
                )

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
    toezeggingen = bouw_ienw_toezeggingen()

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
        toezeggingen
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

    print(
        f"Kandidaatparen opgeslagen: "
        f"{sum(len(item['kandidaten']) for item in resultaten)}"
    )
