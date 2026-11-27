from collections import Counter
from copy import deepcopy

from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)
from sklearn.metrics.pairwise import (
    cosine_similarity,
)


MINIMUM_WAARNEMINGEN = 10
MINIMUM_DOMINANT_AANDEEL = 0.80

MINIMUM_MINISTERIE_AANDEEL_VOOR_INHOUD = 0.05
MAXIMUM_INHOUDELIJKE_KANDIDATEN = 5

MAXIMUM_VRAGENUURCOMMISSIES = 3

AANTAL_BESTE_PROFIELMATCHES = 3


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

def normaliseer_profieltekst(
    tekst
):
    waarde = (
        tekst
        or ""
    ).lower()

    waarde = " ".join(
        waarde.split()
    )

    return waarde

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

def bouw_commissieprofielen(
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

    commissieprofielen = {
        commissie_slug: []
        for commissie_slug
        in vaste_commissie_index
    }

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

        commissie_slugs = (
            bepaal_betrouwbare_commissies(
                toezegging,
                activiteit,
                vaste_commissie_index,
                maak_commissieslug
            )
        )

        # Alleen ondubbelzinnig gekoppelde
        # reguliere toezeggingen gebruiken.
        if len(commissie_slugs) != 1:
            continue

        commissie_slug = (
            commissie_slugs[0]
        )

        onderdelen = [
            toezegging.get("Tekst") or "",
            activiteit.get("Onderwerp") or "",
        ]

        profieltekst = (
            normaliseer_profieltekst(
                " ".join(
                    onderdelen
                )
            )
        )

        if not profieltekst:
            continue

        commissieprofielen.setdefault(
            commissie_slug,
            []
        ).append(
            profieltekst
        )

    return commissieprofielen

def rangschik_commissies_op_inhoud(
    toezegging,
    activiteit,
    kandidaatcommissies,
    commissieprofielen
):
    vraagtekst = normaliseer_profieltekst(
        " ".join([
            toezegging.get("Tekst") or "",
            activiteit.get("Onderwerp") or "",
        ])
    )

    if not vraagtekst:
        return []

    profielteksten = []
    profiel_slugs = []

    for commissie in kandidaatcommissies:
        commissie_slug = (
            commissie.get(
                "commissie_slug"
            )
        )

        if not commissie_slug:
            continue

        teksten = commissieprofielen.get(
            commissie_slug,
            []
        )

        for tekst in teksten:
            if not tekst:
                continue

            profielteksten.append(
                tekst
            )

            profiel_slugs.append(
                commissie_slug
            )

    if not profielteksten:
        return []

    corpus = [
        vraagtekst,
        *profielteksten,
    ]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True
    )

    matrix = vectorizer.fit_transform(
        corpus
    )

    scores = cosine_similarity(
        matrix[0:1],
        matrix[1:]
    ).flatten()

    scores_per_commissie = {}

    for commissie_slug, score in zip(
        profiel_slugs,
        scores
    ):
        scores_per_commissie.setdefault(
            commissie_slug,
            []
        ).append(
            float(score)
        )

    resultaat = []

    kandidaten_op_slug = {
        commissie.get(
            "commissie_slug"
        ): commissie
        for commissie in kandidaatcommissies
        if commissie.get(
            "commissie_slug"
        )
    }

    for (
        commissie_slug,
        commissie_scores
    ) in scores_per_commissie.items():
        commissie_scores.sort(
            reverse=True
        )

        beste_scores = commissie_scores[
            :AANTAL_BESTE_PROFIELMATCHES
        ]

        inhoudelijke_score = (
            sum(beste_scores)
            / len(beste_scores)
        )

        commissiegegevens = (
            kandidaten_op_slug.get(
                commissie_slug,
                {}
            )
        )

        resultaat.append({
            **commissiegegevens,

            "inhoudelijke_score":
                round(
                    inhoudelijke_score,
                    6
                ),

            "beste_profielscores": [
                round(
                    score,
                    6
                )
                for score
                in beste_scores
            ],

            "aantal_profielteksten":
                len(
                    commissie_scores
                ),
        })

    resultaat.sort(
        key=lambda item:
            item.get(
                "inhoudelijke_score",
                0.0
            ),
        reverse=True
    )

    return resultaat

def maak_commissiekoppeling(
    commissie,
    positie,
    vaste_commissie_index,
    koppelbron
):
    commissie_slug = (
        commissie.get(
            "commissie_slug"
        )
    )

    commissiegegevens = (
        vaste_commissie_index.get(
            commissie_slug,
            commissie
        )
    )

    ministerie_aandeel = (
        commissie.get(
            "aandeel",
            0.0
        )
    )

    inhoudelijke_score = (
        commissie.get(
            "inhoudelijke_score"
        )
    )

    return {
        "commissie_id":
            commissiegegevens.get(
                "commissie_id"
            ),

        "commissie_slug":
            commissie_slug,

        "commissie_afkorting":
            (
                commissiegegevens.get(
                    "commissie_afkorting"
                )
                or commissie_slug.upper()
            ),

        "commissie_naam":
            commissiegegevens.get(
                "commissie_naam"
            ),

        "positie":
            positie,

        "koppelbron":
            koppelbron,

        "ministerie_aandeel":
            ministerie_aandeel,

        "inhoudelijke_score":
            inhoudelijke_score,

        "aantal_ministeriewaarnemingen":
            commissie.get(
                "aantal",
                0
            ),

        "beste_profielscores":
            commissie.get(
                "beste_profielscores",
                []
            ),

        "aantal_profielteksten":
            commissie.get(
                "aantal_profielteksten",
                0
            ),
    }


def koppel_vragenuurtoezegging(
    toezegging,
    activiteit,
    ministerie_index,
    vaste_commissie_index,
    commissieprofielen
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

            "commissies":
                [],
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

            "commissies":
                [],
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

            "commissies":
                [],
        }

    totaal = gegevens.get(
        "totaal",
        0
    )

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

            "waarnemingen":
                totaal,

            "commissies":
                [],
        }

    beste = gerangschikte_commissies[0]

    beste_aandeel = beste.get(
        "aandeel",
        0.0
    )

    # Een dominante ministerie-relatie levert
    # één commissie op.
    if (
        totaal >= MINIMUM_WAARNEMINGEN
        and beste_aandeel
        >= MINIMUM_DOMINANT_AANDEEL
    ):
        commissiekoppeling = (
            maak_commissiekoppeling(
                beste,
                positie=1,
                vaste_commissie_index=(
                    vaste_commissie_index
                ),
                koppelbron=(
                    "dominante_ministeriecommissie"
                )
            )
        )

        percentage = round(
            beste_aandeel * 100,
            1
        )

        commissie_afkorting = (
            commissiekoppeling[
                "commissie_afkorting"
            ]
        )

        return {
            "status":
                "gekoppeld",

            "reden":
                "dominante_ministeriecommissie",

            "ministerie":
                ministerie_bronwaarde,

            "waarnemingen":
                totaal,

            "selectiereden": (
                "Vragenuur: ministerie "
                f"{ministerie_bronwaarde} "
                "historisch gekoppeld aan "
                f"{commissie_afkorting} "
                f"({percentage}%, "
                f"{totaal} waarnemingen)"
            ),

            "commissies": [
                commissiekoppeling
            ],

            "ministerie_rangschikking":
                deepcopy(
                    gerangschikte_commissies
                ),
        }

    # Bij een niet-dominant ministerie worden
    # alle enigszins plausibele commissies eerst
    # inhoudelijk gerangschikt.
    ministerie_kandidaten = [
        commissie
        for commissie
        in gerangschikte_commissies
        if commissie.get(
            "aandeel",
            0.0
        )
        >= (
            MINIMUM_MINISTERIE_AANDEEL_VOOR_INHOUD
        )
    ][
        :MAXIMUM_INHOUDELIJKE_KANDIDATEN
    ]

    if not ministerie_kandidaten:
        # Wanneer geen commissie de grens van
        # vijf procent haalt, gebruiken we toch
        # de historische top drie.
        ministerie_kandidaten = (
            gerangschikte_commissies[
                :MAXIMUM_VRAGENUURCOMMISSIES
            ]
        )

    inhoudelijke_rangschikking = (
        rangschik_commissies_op_inhoud(
            toezegging,
            activiteit,
            ministerie_kandidaten,
            commissieprofielen
        )
    )

    # Als er onvoldoende profielinformatie is,
    # blijft de historische volgorde behouden.
    if inhoudelijke_rangschikking:
        uiteindelijke_rangschikking = (
            inhoudelijke_rangschikking
        )
        koppelbron = (
            "ministerie_en_inhoudelijke_rangschikking"
        )
    else:
        uiteindelijke_rangschikking = (
            ministerie_kandidaten
        )
        koppelbron = (
            "ministerie_rangschikking"
        )

    geselecteerde_commissies = []

    for positie, commissie in enumerate(
        uiteindelijke_rangschikking[
            :MAXIMUM_VRAGENUURCOMMISSIES
        ],
        start=1
    ):
        koppeling = maak_commissiekoppeling(
            commissie,
            positie=positie,
            vaste_commissie_index=(
                vaste_commissie_index
            ),
            koppelbron=koppelbron
        )

        geselecteerde_commissies.append(
            koppeling
        )

    if not geselecteerde_commissies:
        return {
            "status":
                "niet_gekoppeld",

            "reden":
                "geen_bruikbare_commissies",

            "ministerie":
                ministerie_bronwaarde,

            "waarnemingen":
                totaal,

            "commissies":
                [],
        }

    afkortingen = [
        commissie.get(
            "commissie_afkorting"
        )
        for commissie
        in geselecteerde_commissies
        if commissie.get(
            "commissie_afkorting"
        )
    ]

    return {
        "status":
            "gekoppeld_meervoudig",

        "reden":
            koppelbron,

        "ministerie":
            ministerie_bronwaarde,

        "waarnemingen":
            totaal,

        "selectiereden": (
            "Vragenuur: top "
            f"{len(geselecteerde_commissies)} "
            "plausibele commissies op basis "
            "van ministerie en inhoud: "
            + ", ".join(
                afkortingen
            )
        ),

        "commissies":
            geselecteerde_commissies,

        "ministerie_rangschikking":
            deepcopy(
                gerangschikte_commissies
            ),

        "inhoudelijke_rangschikking":
            deepcopy(
                inhoudelijke_rangschikking
            ),
    }
