import json
from collections import Counter
from datetime import datetime
from pathlib import Path


INPUT_PATH = Path("data/candidates.json")
OUTPUT_PATH = Path("data/validation.json")


def datumdeel(waarde):
    """
    Zet bijvoorbeeld:
    2026-11-06T00:00:00+01:00

    om in:
    2026-11-06
    """

    if not waarde:
        return None

    if waarde.startswith("0001-01-01"):
        return None

    try:
        return datetime.fromisoformat(
            waarde.replace("Z", "+00:00")
        ).date().isoformat()

    except ValueError:
        return waarde[:10]


def laad_kandidaten():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Bestand niet gevonden: {INPUT_PATH}"
        )

    return json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )


def verzamel_datum_matches(data):
    matches = []

    for document in data.get("documenten", []):
        documentdatum = datumdeel(
            document.get("datum")
        )

        if not documentdatum:
            continue

        for kandidaat in document.get(
            "kandidaten",
            []
        ):
            if kandidaat.get("status") != "Afgedaan":
                continue

            nakomingsdatum = datumdeel(
                kandidaat.get("datum_nakoming")
            )

            if not nakomingsdatum:
                continue

            if nakomingsdatum != documentdatum:
                continue

            matches.append({
                "documentnummer": (
                    document.get("documentnummer")
                ),
                "documentsoort": (
                    document.get("documentsoort")
                ),
                "documentdatum": documentdatum,
                "onderwerp": (
                    document.get("onderwerp")
                ),
                "toezeggingnummer": (
                    kandidaat.get(
                        "toezeggingnummer"
                    )
                ),
                "positie": kandidaat.get("positie"),
                "score": kandidaat.get(
                    "totale_score"
                ),
                "toezeggingstekst": (
                    kandidaat.get(
                        "toezeggingstekst"
                    )
                ),
            })

    return matches


def bereken_statistieken(matches):
    unieke_toezeggingen = {
        match["toezeggingnummer"]
        for match in matches
    }

    beste_positie_per_toezegging = {}

    for match in matches:
        nummer = match["toezeggingnummer"]
        positie = match["positie"]

        vorige = beste_positie_per_toezegging.get(
            nummer
        )

        if vorige is None or positie < vorige:
            beste_positie_per_toezegging[
                nummer
            ] = positie

    posities = list(
        beste_positie_per_toezegging.values()
    )

    totaal = len(posities)

    top_1 = sum(
        positie <= 1
        for positie in posities
    )

    top_3 = sum(
        positie <= 3
        for positie in posities
    )

    top_5 = sum(
        positie <= 5
        for positie in posities
    )

    top_10 = sum(
        positie <= 10
        for positie in posities
    )

    top_15 = sum(
        positie <= 15
        for positie in posities
    )

    def percentage(aantal):
        if totaal == 0:
            return 0.0

        return round(
            100 * aantal / totaal,
            1
        )

    return {
        "aantal_datum_matches": len(matches),
        "unieke_toezeggingen": len(
            unieke_toezeggingen
        ),
        "top_1": {
            "aantal": top_1,
            "percentage": percentage(top_1),
        },
        "top_3": {
            "aantal": top_3,
            "percentage": percentage(top_3),
        },
        "top_5": {
            "aantal": top_5,
            "percentage": percentage(top_5),
        },
        "top_10": {
            "aantal": top_10,
            "percentage": percentage(top_10),
        },
        "top_15": {
            "aantal": top_15,
            "percentage": percentage(top_15),
        },
        "positie_verdeling": dict(
            sorted(
                Counter(posities).items()
            )
        ),
    }


def toon_bekende_luchtvaartmatches(
    matches
):
    te_controleren = {
        "TZ202610-188",
        "TZ202610-189",
        "TZ202610-183",
    }

    print(
        "\nBEKENDE LUCHTVAARTMATCHES:\n"
    )

    gevonden = False

    for match in matches:
        if (
            match["toezeggingnummer"]
            in te_controleren
        ):
            gevonden = True

            print(
                match["documentnummer"],
                "|",
                match["documentdatum"],
                "|",
                match["toezeggingnummer"],
                "| positie:",
                match["positie"],
                "| score:",
                match["score"],
                "|",
                match["onderwerp"],
            )

    if not gevonden:
        print("Geen gevonden.")


def schrijf_validatie(
    matches,
    statistieken
):
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output = {
        "methodologische_beperking": (
            "Een gelijke documentdatum en "
            "DatumNakoming is een aanwijzing, "
            "maar geen bewijs dat het document "
            "de betreffende toezegging afdoet."
        ),
        "statistieken": statistieken,
        "datum_matches": matches,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


if __name__ == "__main__":
    data = laad_kandidaten()

    matches = verzamel_datum_matches(
        data
    )

    statistieken = (
        bereken_statistieken(matches)
    )

    print("\nVALIDATIE KANDIDAATSELECTIE:\n")

    print(
        "Datum-matches:",
        statistieken[
            "aantal_datum_matches"
        ]
    )

    print(
        "Unieke recent afgedane "
        "toezeggingen:",
        statistieken[
            "unieke_toezeggingen"
        ]
    )

    for grens in [
        "top_1",
        "top_3",
        "top_5",
        "top_10",
        "top_15",
    ]:
        waarde = statistieken[grens]

        print(
            grens,
            ":",
            waarde["aantal"],
            "|",
            waarde["percentage"],
            "%"
        )

    print("\nPOSITIEVERDELING:")

    for positie, aantal in (
        statistieken[
            "positie_verdeling"
        ].items()
    ):
        print(
            f"Positie {positie}: {aantal}"
        )

    toon_bekende_luchtvaartmatches(
        matches
    )

    schrijf_validatie(
        matches,
        statistieken
    )

    print(
        f"\nValidatie opgeslagen in: "
        f"{OUTPUT_PATH}"
    )
