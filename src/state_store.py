import json
import os
from pathlib import Path


HISTORY_PATH = Path(
    "data/assessment_history.json"
)

PUBLISHED_PATH = Path(
    "data/published_results.json"
)


def laad_json(path, standaard):
    if not path.exists():
        return standaard

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        json.JSONDecodeError,
        OSError
    ) as fout:
        print(
            f"WAARSCHUWING: {path} kon "
            f"niet worden gelezen: {fout}"
        )

        return standaard


def schrijf_json_atomair(
    path,
    gegevens
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    tijdelijk_pad = path.with_suffix(
        path.suffix + ".tmp"
    )

    tijdelijk_pad.write_text(
        json.dumps(
            gegevens,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    os.replace(
        tijdelijk_pad,
        path
    )

def migreer_oude_historie(
    historie
):
    verwerkt = historie.get(
        "verwerkt",
        {}
    )

    gemigreerd = {}
    aantal_gemigreerd = 0

    for sleutel, gegevens in (
        verwerkt.items()
    ):
        # Nieuwe sleutels bevatten al een
        # commissie_slug, bijvoorbeeld:
        # ienw|2026D56295
        if "|" in sleutel:
            gemigreerd[sleutel] = gegevens
            continue

        # De bestaande historie is opgebouwd
        # toen alleen IenW werd beoordeeld.
        nieuwe_sleutel = (
            f"ienw|{sleutel}"
        )

        nieuwe_gegevens = dict(
            gegevens
        )

        nieuwe_gegevens.setdefault(
            "commissie_slug",
            "ienw"
        )

        nieuwe_gegevens.setdefault(
            "commissie_afkorting",
            "I&W"
        )

        gemigreerd[
            nieuwe_sleutel
        ] = nieuwe_gegevens

        aantal_gemigreerd += 1

    historie["verwerkt"] = gemigreerd

    if aantal_gemigreerd:
        print(
            f"Oude historievermeldingen "
            f"gemigreerd naar IenW: "
            f"{aantal_gemigreerd}"
        )

    return historie

def laad_historie():
    gegevens = laad_json(
        HISTORY_PATH,
        {
            "verwerkt": {},
            "wacht_op_herhaling": {},
            "round_robin": {
                "laatste_commissie_slug": None,
            },
        }
    )

    gegevens.setdefault(
        "verwerkt",
        {}
    )

    gegevens.setdefault(
        "wacht_op_herhaling",
        {}
    )

    gegevens.setdefault(
        "round_robin",
        {
            "laatste_commissie_slug": None,
        }
    )

    gegevens["round_robin"].setdefault(
        "laatste_commissie_slug",
        None
    )

    gegevens = migreer_oude_historie(
        gegevens
    )

    return gegevens
def schrijf_historie(historie):
    schrijf_json_atomair(
        HISTORY_PATH,
        historie
    )

def migreer_oude_gepubliceerde_resultaten(
    gegevens
):
    resultaten = gegevens.get(
        "resultaten",
        {}
    )

    gemigreerd = {}
    aantal_gemigreerd = 0

    for sleutel, resultaat in (
        resultaten.items()
    ):
        onderdelen = sleutel.split("|")

        # Nieuwe sleutel:
        # commissie_slug|toezeggingnummer|
        # documentnummer
        if len(onderdelen) == 3:
            gemigreerd[sleutel] = resultaat
            continue

        # Oude sleutel:
        # toezeggingnummer|documentnummer
        if len(onderdelen) != 2:
            print(
                "WAARSCHUWING: onbekende "
                "publicatiesleutel:",
                sleutel
            )

            gemigreerd[sleutel] = resultaat
            continue

        toezeggingnummer = onderdelen[0]
        documentnummer = onderdelen[1]

        nieuwe_sleutel = (
            f"ienw|"
            f"{toezeggingnummer}|"
            f"{documentnummer}"
        )

        nieuw_resultaat = dict(
            resultaat
        )

        nieuw_resultaat[
            "sleutel"
        ] = nieuwe_sleutel

        nieuw_resultaat.setdefault(
            "commissie_slug",
            "ienw"
        )

        nieuw_resultaat.setdefault(
            "commissie_afkorting",
            "I&W"
        )

        gemigreerd[
            nieuwe_sleutel
        ] = nieuw_resultaat

        aantal_gemigreerd += 1

    gegevens["resultaten"] = gemigreerd

    if aantal_gemigreerd:
        print(
            "Oude gepubliceerde resultaten "
            f"gemigreerd naar IenW: "
            f"{aantal_gemigreerd}"
        )

    return gegevens

def laad_gepubliceerde_resultaten():
    gegevens = laad_json(
        PUBLISHED_PATH,
        {
            "resultaten": {}
        }
    )

    gegevens.setdefault(
        "resultaten",
        {}
    )

    gegevens = (
        migreer_oude_gepubliceerde_resultaten(
            gegevens
        )
    )

    return gegevens


def schrijf_gepubliceerde_resultaten(
    gegevens
):
    schrijf_json_atomair(
        PUBLISHED_PATH,
        gegevens
    )
