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
        document.get("Onderwerp
