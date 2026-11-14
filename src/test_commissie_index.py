import json
from pathlib import Path


from commissie_index import (
    bouw_commissie_index,
)

from get_toezeggingen import (
    get_open_toezeggingen,
    get_recent_afgedane_toezeggingen,
    combineer_toezeggingen,
    get_relevante_activiteiten,
    vul_ontbrekende_activiteiten_aan,
    get_volgcommissie_actoren,
    get_commissies,
)


OUTPUT_PATH = Path(
    "data/commissie_index_test.json"
)


def main():
    print("Toezeggingen ophalen...")

    actuele_toezeggingen = (
        get_open_toezeggingen()
    )

    recent_afgedaan = (
        get_recent_afgedane_toezeggingen(
            aantal_dagen=14
        )
    )

    toezeggingen = combineer_toezeggingen(
        actuele_toezeggingen,
        recent_afgedaan
    )

    print(
        "Gecombineerde set toezeggingen:",
        len(toezeggingen)
    )

    print("\nActiviteiten ophalen...")

    activiteiten = (
        get_relevante_activiteiten()
    )

    (
        activiteiten,
        uitgesloten_activiteitnummers,
    ) = vul_ontbrekende_activiteiten_aan(
        toezeggingen,
        activiteiten
    )

    print("\nVolgcommissies ophalen...")

    volgcommissie_actoren = (
        get_volgcommissie_actoren()
    )

    print("\nCommissies ophalen...")

    commissies = get_commissies()

    print(
        "\nGezamenlijke commissie-index "
        "bouwen..."
    )

    commissie_index = (
        bouw_commissie_index(
            toezeggingen,
            activiteiten,
            volgcommissie_actoren,
            commissies,
            uitgesloten_activiteitnummers=(
                uitgesloten_activiteitnummers
            ),
        )
    )

    samenvatting = (
        commissie_index["samenvatting"]
    )

    print(
        "\n"
        "========================================"
    )

    print(
        "SAMENVATTING COMMISSIE-INDEX"
    )

    print(
        "========================================"
    )

    print(
        "Actuele vaste commissies:",
        samenvatting[
            "aantal_actuele_commissies"
        ]
    )

    print(
        "Totaal commissieselecties:",
        samenvatting[
            "totaal_commissieselecties"
        ]
    )

    print(
        "Unieke toezeggingen:",
        samenvatting[
            "unieke_toezeggingen"
        ]
    )

    print(
        "Toezeggingen bij meerdere "
        "commissies:",
        samenvatting[
            "toezeggingen_bij_meerdere_commissies"
        ]
    )

    print(
        "Verdeling aantal commissies:",
        samenvatting[
            "verdeling_aantal_commissies"
        ]
    )

    print(
        "\nSELECTIES PER COMMISSIE:\n"
    )

    for slug, gegeven in sorted(
        commissie_index[
            "commissies"
        ].items()
    ):
        print(
            slug,
            "|",
            gegeven["afkorting"],
            "|",
            gegeven[
                "aantal_toezeggingen"
            ],
            "|",
            gegeven["naam"],
        )

    meervoudige_toezeggingen = [
        toezegging
        for toezegging
        in commissie_index[
            "toezeggingen"
        ]
        if len(
            toezegging.get(
                "Commissies",
                []
            )
        ) > 1
    ]

    meervoudige_toezeggingen.sort(
        key=lambda toezegging: (
            -len(
                toezegging.get(
                    "Commissies",
                    []
                )
            ),
            toezegging.get("Nummer") or "",
        )
    )

    print(
        "\nVOORBEELDEN MEERDERE "
        "COMMISSIES:\n"
    )

    for toezegging in (
        meervoudige_toezeggingen[:20]
    ):
        print(
            toezegging.get("Nummer"),
            "| commissies:",
            ", ".join(
                toezegging.get(
                    "CommissieSlugs",
                    []
                )
            ),
            "|",
            toezegging.get("Tekst"),
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            commissie_index,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"\nTestindex opgeslagen in: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
