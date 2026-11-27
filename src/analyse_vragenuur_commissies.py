import json

from collections import Counter
from pathlib import Path

from get_toezeggingen import (
    get_open_toezeggingen,
    get_recent_afgedane_toezeggingen,
    combineer_toezeggingen,
    get_relevante_activiteiten,
    vul_ontbrekende_activiteiten_aan,
    get_commissies,
    get_actuele_vaste_commissies,
    maak_commissieslug,
)

from vragenuur_commission_resolver import (
    MINIMUM_WAARNEMINGEN,
    MINIMUM_DOMINANT_AANDEEL,
    MINIMUM_INHOUDELIJKE_SCORE,
    MINIMUM_INHOUDELIJKE_MARGE,
    bouw_ministerie_commissie_index,
    bouw_commissieprofielen,
    koppel_vragenuurtoezegging,
)


OUTPUT_PATH = Path(
    "data/"
    "vragenuur_commission_diagnostics.json"
)

AANTAL_DAGEN_AFGEDAAN = 14


def main():
    print(
        "Openstaande en deels afgedane "
        "toezeggingen ophalen..."
    )

    actuele_toezeggingen = (
        get_open_toezeggingen()
    )

    print(
        "Recent afgedane toezeggingen ophalen..."
    )

    recent_afgedaan = (
        get_recent_afgedane_toezeggingen(
            aantal_dagen=(
                AANTAL_DAGEN_AFGEDAAN
            )
        )
    )

    toezeggingen = combineer_toezeggingen(
        actuele_toezeggingen,
        recent_afgedaan
    )

    print(
        "Relevante activiteiten ophalen..."
    )

    activiteiten = (
        get_relevante_activiteiten()
    )

    activiteiten, _ = (
        vul_ontbrekende_activiteiten_aan(
            toezeggingen,
            activiteiten
        )
    )

    activiteiten_op_nummer = {
        activiteit.get("Nummer"):
            activiteit
        for activiteit in activiteiten
        if activiteit.get("Nummer")
    }

    print(
        "Commissies ophalen..."
    )

    commissies = get_commissies()

    vaste_commissies = (
        get_actuele_vaste_commissies(
            commissies
        )
    )

    (
        ministerie_index,
        vaste_commissie_index,
    ) = bouw_ministerie_commissie_index(
        toezeggingen,
        activiteiten,
        vaste_commissies,
        maak_commissieslug
    )

    commissieprofielen = (
        bouw_commissieprofielen(
            toezeggingen,
            activiteiten,
            vaste_commissies,
            maak_commissieslug
        )
    )

    print(
        "Commissieprofielen opgebouwd:",
        len(
            commissieprofielen
        )
    )
    
    vragenuur_resultaten = []

    for toezegging in toezeggingen:
        activiteitnummer = (
            toezegging.get(
                "ActiviteitNummer"
            )
        )

        activiteit = (
            activiteiten_op_nummer.get(
                activiteitnummer
            )
        )

        if not activiteit:
            continue

        if (
            activiteit.get("Soort")
            != "Vragenuur"
        ):
            continue

        resolver_resultaat = (
            koppel_vragenuurtoezegging(
                toezegging,
                activiteit,
                ministerie_index,
                vaste_commissie_index,
                commissieprofielen
            )
        )

        vragenuur_resultaten.append({
            "toezeggingnummer":
                toezegging.get("Nummer"),

            "status":
                toezegging.get("Status"),

            "toezeggingtekst":
                toezegging.get("Tekst"),

            "bewindspersoon":
                toezegging.get("Naam"),

            "functie":
                toezegging.get("Functie"),

            "ministerie":
                toezegging.get("Ministerie"),

            "activiteitnummer":
                activiteitnummer,

            "activiteitdatum":
                activiteit.get("Datum"),

            "activiteitonderwerp":
                activiteit.get("Onderwerp"),

            "resolver":
                resolver_resultaat,
        })

    status_tellingen = Counter(
        resultaat[
            "resolver"
        ].get(
            "status",
            "onbekend"
        )
        for resultaat
        in vragenuur_resultaten
    )

    ministerie_overzicht = {}

    for ministerie, gegevens in (
        ministerie_index.items()
    ):
        commissies_gesorteerd = sorted(
            gegevens.get(
                "commissies",
                {}
            ).values(),
            key=lambda item:
                item.get(
                    "aandeel",
                    0.0
                ),
            reverse=True
        )

        ministerie_overzicht[
            ministerie
        ] = {
            "totaal":
                gegevens.get("totaal"),

            "commissies":
                commissies_gesorteerd,
        }

    output = {
        "samenvatting": {
            "aantal_toezeggingen":
                len(toezeggingen),

            "aantal_vragenuurtoezeggingen":
                len(vragenuur_resultaten),

            "resolverstatussen":
                dict(status_tellingen),

            "minimum_waarnemingen":
                MINIMUM_WAARNEMINGEN,

            "minimum_dominant_aandeel":
                MINIMUM_DOMINANT_AANDEEL,

            "productie_actief":
                False,

            "minimum_inhoudelijke_score":
                MINIMUM_INHOUDELIJKE_SCORE,

            "minimum_inhoudelijke_marge":
                MINIMUM_INHOUDELIJKE_MARGE,
        },

        "ministerie_commissie_index":
            ministerie_overzicht,

        "vragenuurtoezeggingen":
            vragenuur_resultaten,

        "commissieprofielen": {
            commissie_slug: {
                "aantal_profielteksten":
                    len(teksten)
            }
            for commissie_slug, teksten
            in commissieprofielen.items()
        },
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        "\nVRAGENUURANALYSE:"
    )

    print(
        "Vragenuurtoezeggingen:",
        len(vragenuur_resultaten)
    )

    for status, aantal in (
        status_tellingen.most_common()
    ):
        print(
            status,
            ":",
            aantal
        )

    print(
        "\nDiagnostiek opgeslagen in:",
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()
