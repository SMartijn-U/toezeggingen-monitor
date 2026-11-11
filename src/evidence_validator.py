import re
import unicodedata


def normaliseer_tekst(tekst):
    if not tekst:
        return ""

    # Unicode normaliseren
    tekst = unicodedata.normalize(
        "NFKC",
        tekst
    )

    # Verschillende soorten aanhalingstekens
    # gelijk behandelen
    tekst = tekst.replace("“", '"')
    tekst = tekst.replace("”", '"')
    tekst = tekst.replace("‘", "'")
    tekst = tekst.replace("’", "'")

    # Afbrekingen en witruimte normaliseren
    tekst = tekst.replace("\u00ad", "")
    tekst = re.sub(
        r"\s+",
        " ",
        tekst
    )

    return tekst.strip().lower()


def valideer_fragment(
    fragment,
    documenttekst
):
    fragment_norm = normaliseer_tekst(
        fragment
    )

    document_norm = normaliseer_tekst(
        documenttekst
    )

    if not fragment_norm:
        return False

    return fragment_norm in document_norm


def valideer_beoordeling(
    beoordeling,
    documenttekst
):
    resultaten = []

    for fragment in (
        beoordeling.bewijsfragmenten
    ):
        geldig = valideer_fragment(
            fragment,
            documenttekst
        )

        resultaten.append({
            "fragment": fragment,
            "geldig": geldig,
        })

    aantal = len(resultaten)

    geldig_aantal = sum(
        item["geldig"]
        for item in resultaten
    )

    alle_geldig = (
        aantal > 0
        and geldig_aantal == aantal
    )

    return {
        "aantal_fragmenten": aantal,
        "aantal_geldig": geldig_aantal,
        "alle_geldig": alle_geldig,
        "fragmenten": resultaten,
    }
