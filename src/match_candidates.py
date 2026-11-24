import re

from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)
from sklearn.metrics.pairwise import (
    cosine_similarity,
)


NEDERLANDSE_STOPWOORDEN = {
    "de", "het", "een", "en", "van", "voor", "in",
    "op", "met", "dat", "die", "dit", "te", "tot",
    "aan", "om", "over", "naar", "bij", "uit", "is",
    "wordt", "zal", "zegt", "toe", "minister",
    "staatssecretaris", "kamer", "tweede",
}

BONUS_EXACT_NUMMER = 0.50

MAXIMUM_BLOKGROOTTE = 1800
BLOKOVERLAP = 300


def normaliseer_tekst(tekst):
    if not tekst:
        return ""

    tekst = tekst.lower()

    # Verschillende liggende streepjes gelijk maken.
    tekst = (
        tekst
        .replace("–", "-")
        .replace("—", "-")
        .replace("‑", "-")
    )

    # Samengestelde woorden met een koppelteken
    # ook als losse woorden herkenbaar maken.
    tekst = tekst.replace(
        "-",
        " "
    )

    tekst = re.sub(
        r"[^a-z0-9à-ÿ ]",
        " ",
        tekst
    )

    tekst = re.sub(
        r"\s+",
        " ",
        tekst
    ).strip()

    woorden = [
        woord
        for woord in tekst.split()
        if (
            len(woord) > 2
            and woord not in NEDERLANDSE_STOPWOORDEN
        )
    ]

    return " ".join(
        woorden
    )


def normaliseer_toezeggingnummer(
    nummer
):
    if not nummer:
        return None

    match = re.fullmatch(
        r"\s*"
        r"(?:tz\s*)?"
        r"(\d{6})"
        r"\s*-\s*"
        r"(\d{1,3})"
        r"\s*",
        str(nummer),
        flags=re.IGNORECASE
    )

    if not match:
        return None

    periode = match.group(1)

    volgnummer = (
        match.group(2)
        .zfill(3)
    )

    return (
        f"{periode}"
        f"{volgnummer}"
    )


def vind_toezeggingnummers_in_tekst(
    tekst
):
    gevonden = set()

    if not tekst:
        return gevonden

    patroon = re.compile(
        r"(?<!\d)"
        r"(?:tz\s*)?"
        r"(\d{6})"
        r"\s*-\s*"
        r"(\d{1,3})"
        r"(?!\d)",
        flags=re.IGNORECASE
    )

    for match in patroon.finditer(
        tekst
    ):
        periode = match.group(1)

        volgnummer = (
            match.group(2)
            .zfill(3)
        )

        gevonden.add(
            f"{periode}"
            f"{volgnummer}"
        )

    return gevonden


def maak_documenttekst(
    document,
    volledige_tekst
):
    onderdelen = [
        document.get("Soort") or "",
        document.get("Onderwerp") or "",
        document.get("Titel") or "",
        volledige_tekst or "",
    ]

    return normaliseer_tekst(
        " ".join(
            onderdelen
        )
    )


def maak_toezeggingtekst(
    toezegging
):
    activiteit = toezegging.get(
        "Activiteit",
        {}
    )

    onderdelen = [
        toezegging.get("Nummer") or "",
        toezegging.get("Tekst") or "",
        toezegging.get("Naam") or "",
        toezegging.get("Ministerie") or "",
        activiteit.get("Onderwerp") or "",
        activiteit.get("Soort") or "",
    ]

    return normaliseer_tekst(
        " ".join(
            onderdelen
        )
    )


def maak_tekstblokken(
    volledige_tekst
):
    if not volledige_tekst:
        return []

    tekst = (
        volledige_tekst
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    # Eerst zoveel mogelijk gebruikmaken van
    # alinea-einden uit het brondocument.
    alineaen = [
        re.sub(
            r"\s+",
            " ",
            alinea
        ).strip()
        for alinea in re.split(
            r"\n\s*\n|\n",
            tekst
        )
        if alinea.strip()
    ]

    blokken = []
    huidig_blok = ""

    for alinea in alineaen:
        if not huidig_blok:
            huidig_blok = alinea
            continue

        gecombineerd = (
            f"{huidig_blok} "
            f"{alinea}"
        )

        if (
            len(gecombineerd)
            <= MAXIMUM_BLOKGROOTTE
        ):
            huidig_blok = gecombineerd
            continue

        blokken.append(
            huidig_blok
        )

        # Overlap voorkomt dat relevante passages
        # precies op een blokgrens verloren gaan.
        overlap = huidig_blok[
            -BLOKOVERLAP:
        ]

        huidig_blok = (
            f"{overlap} "
            f"{alinea}"
        )

    if huidig_blok:
        blokken.append(
            huidig_blok
        )

    # Fallback voor documenten waarin nauwelijks
    # alinea-einden zijn overgebleven.
    if len(blokken) <= 1:
        blokken = []

        stapgrootte = (
            MAXIMUM_BLOKGROOTTE
            - BLOKOVERLAP
        )

        for begin in range(
            0,
            len(tekst),
            stapgrootte
        ):
            einde = (
                begin
                + MAXIMUM_BLOKGROOTTE
            )

            blok = tekst[
                begin:einde
            ].strip()

            if blok:
                blokken.append(
                    blok
                )

    return blokken


def rangschik_kandidaten(
    document,
    volledige_tekst,
    toezeggingen,
    maximum=15
):
    if not toezeggingen:
        return []

    documenttekst = maak_documenttekst(
        document,
        volledige_tekst
    )

    ruwe_tekstblokken = (
        maak_tekstblokken(
            volledige_tekst
        )
    )

    genormaliseerde_blokken = [
        normaliseer_tekst(
            tekstblok
        )
        for tekstblok
        in ruwe_tekstblokken
    ]

    geldige_blokken = [
        (
            ruw_blok,
            genormaliseerd_blok,
        )
        for (
            ruw_blok,
            genormaliseerd_blok,
        )
        in zip(
            ruwe_tekstblokken,
            genormaliseerde_blokken
        )
        if genormaliseerd_blok
    ]

    ruwe_tekstblokken = [
        item[0]
        for item
        in geldige_blokken
    ]

    genormaliseerde_blokken = [
        item[1]
        for item
        in geldige_blokken
    ]

    toezeggingsteksten = [
        maak_toezeggingtekst(
            toezegging
        )
        for toezegging
        in toezeggingen
    ]

    documentdelen = [
        documenttekst,
        *genormaliseerde_blokken,
    ]

    corpus = [
        *documentdelen,
        *toezeggingsteksten,
    ]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True
    )

    matrix = vectorizer.fit_transform(
        corpus
    )

    aantal_documentdelen = len(
        documentdelen
    )

    documentvectoren = matrix[
        :aantal_documentdelen
    ]

    toezeggingvectoren = matrix[
        aantal_documentdelen:
    ]

    similarity_matrix = cosine_similarity(
        documentvectoren,
        toezeggingvectoren
    )

    document_toezeggingnummers = (
        vind_toezeggingnummers_in_tekst(
            volledige_tekst
        )
    )

    resultaten = []

    for index, toezegging in enumerate(
        toezeggingen
    ):
        nummer = (
            toezegging.get("Nummer")
            or ""
        )

        volledige_documentscore = float(
            similarity_matrix[
                0,
                index
            ]
        )

        lokale_scores = (
            similarity_matrix[
                1:,
                index
            ]
            if len(documentdelen) > 1
            else []
        )

        if len(lokale_scores) > 0:
            beste_blokindex = int(
                lokale_scores.argmax()
            )

            beste_lokale_score = float(
                lokale_scores[
                    beste_blokindex
                ]
            )
        else:
            beste_blokindex = None
            beste_lokale_score = 0.0

        similarity = max(
            volledige_documentscore,
            beste_lokale_score
        )

        bonus = 0.0
        bonusredenen = []

        genormaliseerd_nummer = (
            normaliseer_toezeggingnummer(
                nummer
            )
        )

        nummermatch = (
            genormaliseerd_nummer
            and genormaliseerd_nummer
            in document_toezeggingnummers
        )

        if nummermatch:
            bonus += (
                BONUS_EXACT_NUMMER
            )

            bonusredenen.append(
                "genormaliseerde_nummermatch"
            )

        score = min(
            1.0,
            similarity + bonus
        )

        resultaten.append({
            "toezegging":
                toezegging,

            "similarity":
                similarity,

            "volledige_documentscore":
                volledige_documentscore,

            "lokale_score":
                beste_lokale_score,

            "beste_blokindex":
                beste_blokindex,

            "genormaliseerde_nummermatch":
                bool(nummermatch),

            "bonusredenen":
                bonusredenen,

            "bonus":
                bonus,

            "score":
                score,
        })

    resultaten.sort(
        key=lambda item: (
            item["score"],
            item["similarity"],
        ),
        reverse=True
    )

    return resultaten[
        :maximum
    ]
