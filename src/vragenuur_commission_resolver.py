from collections import Counter
from copy import deepcopy


MINIMUM_WAARNEMINGEN = 10
MINIMUM_DOMINANT_AANDEEL = 0.80


def normaliseer_ministerie(
    ministerie
):
    waarde = (
        ministerie
        or ""
    ).strip().lower()

    voorvoegsels = (
        "ministerie van ",
        "ministerie voor ",
        "ministerie ",
    )

    for voorvoegsel in voorvoegsels:
        if waarde.startswith(
            voorvoegsel
        ):
            waarde = waarde[
                len(voorvoegsel):
            ]

            break

    return " ".join(
        waarde.split()
    )


def maak_vaste_commissie_index(
    vaste_commissies,
    maak_commissieslug
):
    index = {}

    for commissie in vaste_commissies:
        slug = maak_commissieslug(
            commissie
        )

        if not slug:
            continue

        index[slug] = {
            "commissie_id":
                commissie.get("Id"),

            "commissie_slug":
                slug,

            "commissie_afkorting":
                (
                    commissie.get("Afkorting")
                    or slug.upper()
                ).strip(),

            "commissie_naam":
                (
                    commissie.get("NaamNL")
                    or commissie.get("NaamWebNL")
                    or ""
                ).strip(),
        }

    return index


def bepaal_betrouwbare_commissies(
    toezegging,
    activiteit,
    vaste_commissie_index,
    maak_commissieslug
):
    soort = (
        activiteit.get("Soort")
        or ""
    ).strip()

    # Start alleen met reguliere
    # commissieactiviteiten. Daardoor wordt
    # de historische ministerie-index niet
    # vervuild met afgeleide koppelingen.
    if soort not in {
        "Commissiedebat",
        "Notaoverleg",
        "Wetgevingsoverleg",
    }:
        return []

    voortouw = (
        activiteit.get(
            "VoortouwCommissieAfkorting"
        )
        or activiteit.get(
            "Voortouwafkorting"
        )
        or activiteit.get(
            "VoortouwCommissieNaam"
        )
        or ""
    ).strip()

    if not voortouw:
        return []

    voortouw_slug = (
        maak_commissieslug({
            "Afkorting": voortouw
        })
    )

    if (
        voortouw_slug
        not in vaste_commissie_index
    ):
        # Soms bevat het voortouwveld de volledige
        # commissienaam in plaats van de afkorting.
        voortouw_lower = voortouw.lower()

        passende_slugs = [
            slug
            for slug, gegevens
            in vaste_commissie_index.items()
            if voortouw_lower
            in {
                (
                    gegevens.get(
                        "commissie_afkorting"
                    )
                    or ""
                ).lower(),
                (
                    gegevens.get(
                        "commissie_naam"
                    )
                    or ""
                ).lower(),
            }
        ]

        if len(passende_slugs) != 1:
            return []

        voortouw_slug = passende_slugs[0]

    return [
        voortouw_slug
    ]


def bouw_ministerie_commissie_index(
    toezeggingen,
    activiteiten,
    vaste_commissies,
    maak_commissieslug
):
    activiteiten_op_nummer = {
        activiteit.get("Nummer"):
            activiteit
        for activiteit in activiteiten
        if activiteit.get("Nummer")
    }

    vaste_commissie_index = (
        maak_vaste_commissie_index(
            vaste_commissies,
            maak_commissieslug
        )
    )

    tellingen = {}

    for toezegging in toezeggingen:
        ministerie = normaliseer_ministerie(
            toezegging.get("Ministerie")
        )

        if not ministerie:
            continue

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

        commissie_slugs = (
            bepaal_betrouwbare_commissies(
                toezegging,
                activiteit,
                vaste_commissie_index,
                maak_commissieslug
            )
        )

        if len(commissie_slugs) != 1:
            continue

        commissie_slug = (
            commissie_slugs[0]
        )

        tellingen.setdefault(
            ministerie,
            Counter()
        )[
            commissie_slug
        ] += 1

    ministerie_index = {}

    for ministerie, commissie_tellingen in (
        tellingen.items()
    ):
        totaal = sum(
            commissie_tellingen.values()
        )

        commissies = {}

        for (
            commissie_slug,
            aantal
        ) in commissie_tellingen.items():
            commissiegegevens = (
                vaste_commissie_index.get(
                    commissie_slug,
                    {}
                )
            )

            commissies[commissie_slug] = {
                **commissiegegevens,
                "aantal":
                    aantal,
                "aandeel":
                    round(
                        aantal / totaal,
                        6
                    ),
            }

        ministerie_index[ministerie] = {
            "ministerie":
                ministerie,

            "totaal":
                totaal,

            "commissies":
                commissies,
        }

    return (
        ministerie_index,
        vaste_commissie_index,
    )


def koppel_vragenuurtoezegging(
    toezegging,
    activiteit,
    ministerie_index,
    vaste_commissie_index
):
    if (
        activiteit.get("Soort")
        != "Vragenuur"
    ):
        return {
            "status":
                "niet_van_toepassing",

            "reden":
                "activiteit_is_geen_vragenuur",
        }

    ministerie_bronwaarde = (
        toezegging.get("Ministerie")
        or ""
    ).strip()

    ministerie = normaliseer_ministerie(
        ministerie_bronwaarde
    )

    if not ministerie:
        return {
            "status":
                "niet_gekoppeld",

            "reden":
                "ministerie_ontbreekt",
        }

    gegevens = ministerie_index.get(
        ministerie
    )

    if not gegevens:
        return {
            "status":
                "niet_gekoppeld",

            "reden":
                "ministerie_niet_in_index",

            "ministerie":
                ministerie_bronwaarde,
        }

    totaal = gegevens.get(
        "totaal",
        0
    )

    if totaal < MINIMUM_WAARNEMINGEN:
        return {
            "status":
                "onvoldoende_data",

            "reden":
                "te_weinig_waarnemingen",

            "ministerie":
                ministerie_bronwaarde,

            "waarnemingen":
                totaal,
        }

    gerangschikte_commissies = sorted(
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

    if not gerangschikte_commissies:
        return {
            "status":
                "niet_gekoppeld",

            "reden":
                "geen_commissies_in_index",

            "ministerie":
                ministerie_bronwaarde,
        }

    beste = gerangschikte_commissies[0]

    beste_aandeel = beste.get(
        "aandeel",
        0.0
    )

    if (
        beste_aandeel
        < MINIMUM_DOMINANT_AANDEEL
    ):
        return {
            "status":
                "ambigu",

            "reden":
                "geen_dominante_commissie",

            "ministerie":
                ministerie_bronwaarde,

            "waarnemingen":
                totaal,

            "kandidaten":
                deepcopy(
                    gerangschikte_commissies[
                        :3
                    ]
                ),
        }

    commissie_slug = beste.get(
        "commissie_slug"
    )

    commissiegegevens = (
        vaste_commissie_index.get(
            commissie_slug,
            beste
        )
    )

    commissie_afkorting = (
        commissiegegevens.get(
            "commissie_afkorting"
        )
        or commissie_slug.upper()
    )

    percentage = round(
        beste_aandeel * 100,
        1
    )

    return {
        "status":
            "gekoppeld",

        "reden":
            "dominante_ministeriecommissie",

        "commissie_id":
            commissiegegevens.get(
                "commissie_id"
            ),

        "commissie_slug":
            commissie_slug,

        "commissie_afkorting":
            commissie_afkorting,

        "commissie_naam":
            commissiegegevens.get(
                "commissie_naam"
            ),

        "score":
            beste_aandeel,

        "waarnemingen":
            totaal,

        "ministerie":
            ministerie_bronwaarde,

        "selectiereden": (
            "Vragenuur: ministerie "
            f"{ministerie_bronwaarde} "
            "historisch gekoppeld aan "
            f"{commissie_afkorting} "
            f"({percentage}%, "
            f"{totaal} waarnemingen)"
        ),

        "kandidaten":
            deepcopy(
                gerangschikte_commissies[
                    :3
                ]
            ),
    }
