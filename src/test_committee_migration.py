from collections import Counter

from build_assessments import (
    laad_kandidaten,
    selecteer_beoordelingseenheden,
)

from state_store import (
    laad_historie,
    laad_gepubliceerde_resultaten,
)


def main():
    print(
        "\n=== DROGE MIGRATIECONTROLE ==="
    )

    historie = laad_historie()

    gepubliceerd = (
        laad_gepubliceerde_resultaten()
    )

    data = laad_kandidaten()

    verwerkt = historie.get(
        "verwerkt",
        {}
    )

    wachtrij = historie.get(
        "wacht_op_herhaling",
        {}
    )

    resultaten = gepubliceerd.get(
        "resultaten",
        {}
    )

    print(
        "\nHISTORIE NA MIGRATIE IN GEHEUGEN"
    )

    print(
        "Verwerkt:",
        len(verwerkt)
    )

    print(
        "Wachtrij:",
        len(wachtrij)
    )

    oude_historie_sleutels = [
        sleutel
        for sleutel in verwerkt
        if "|" not in sleutel
    ]

    print(
        "Oude historiesleutels over:",
        len(oude_historie_sleutels)
    )

    print(
        "\nPUBLICATIES NA MIGRATIE "
        "IN GEHEUGEN"
    )

    print(
        "Gepubliceerde resultaten:",
        len(resultaten)
    )

    oude_publicatiesleutels = [
        sleutel
        for sleutel in resultaten
        if len(
            sleutel.split("|")
        ) != 3
    ]

    print(
        "Oude publicatiesleutels over:",
        len(oude_publicatiesleutels)
    )

    historie_per_commissie = Counter(
        sleutel.split("|")[0]
        for sleutel in verwerkt
        if "|" in sleutel
    )

    publicaties_per_commissie = Counter(
        sleutel.split("|")[0]
        for sleutel in resultaten
        if len(
            sleutel.split("|")
        ) == 3
    )

    print(
        "\nHISTORIE PER COMMISSIE"
    )

    for slug, aantal in sorted(
        historie_per_commissie.items()
    ):
        print(
            slug,
            ":",
            aantal
        )

    print(
        "\nPUBLICATIES PER COMMISSIE"
    )

    for slug, aantal in sorted(
        publicaties_per_commissie.items()
    ):
        print(
            slug,
            ":",
            aantal
        )

    print(
        "\nEERSTE 5 HISTORIESLEUTELS"
    )

    for sleutel in list(
        verwerkt
    )[:5]:
        print(
            sleutel
        )

    print(
        "\nEERSTE 5 PUBLICATIESLEUTELS"
    )

    for sleutel in list(
        resultaten
    )[:5]:
        print(
            sleutel
        )

    beoordelingseenheden = (
        selecteer_beoordelingseenheden(
            data,
            historie
        )
    )

    print(
        "\nBEOORDELINGSEENHEDEN "
        "VOOR VOLGENDE RUN:",
        len(beoordelingseenheden)
    )

    for index, eenheid in enumerate(
        beoordelingseenheden,
        start=1
    ):
        document = eenheid[
            "document"
        ]

        commissie = eenheid[
            "commissie"
        ]

        print(
            index,
            "|",
            eenheid["sleutel"],
            "|",
            commissie.get(
                "commissie_afkorting"
            ),
            "|",
            document.get(
                "documentnummer"
            ),
            "|",
            len(
                commissie.get(
                    "kandidaten",
                    []
                )
            ),
            "kandidaten",
        )

    print(
        "\nCONTROLE VOLTOOID"
    )

    print(
        "Er zijn door dit script geen "
        "JSON-bestanden geschreven."
    )


if __name__ == "__main__":
    main()
