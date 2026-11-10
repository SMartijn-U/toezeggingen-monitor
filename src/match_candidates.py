import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


NEDERLANDSE_STOPWOORDEN = {
    "de", "het", "een", "en", "van", "voor", "in",
    "op", "met", "dat", "die", "dit", "te", "tot",
    "aan", "om", "over", "naar", "bij", "uit", "is",
    "wordt", "zal", "zegt", "toe", "minister",
    "staatssecretaris", "kamer", "tweede"
}


def normaliseer_tekst(tekst):
    if not tekst:
        return ""

    tekst = tekst.lower()

    tekst = re.sub(
        r"[^a-z0-9à-ÿ\- ]",
        " ",
        tekst
    )

    woorden = [
        woord
        for woord in tekst.split()
        if (
            len(woord) > 2
            and woord not in NEDERLANDSE_STOPWOORDEN
        )
    ]

    return " ".join(woorden)


def maak_documenttekst(document, volledige_tekst):
    onderdelen = [
        document.get("Soort") or "",
        document.get("Onderwerp") or "",
        document.get("Titel") or "",
        volledige_tekst or "",
    ]

    return normaliseer_tekst(
        " ".join(onderdelen)
    )


def maak_toezeggingtekst(toezegging):
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
        " ".join(onderdelen)
    )


def rangschik_kandidaten(
    document,
    volledige_tekst,
    toezeggingen,
    maximum=15
):
    documenttekst = maak_documenttekst(
        document,
        volledige_tekst
    )

    toezeggingsteksten = [
        maak_toezeggingtekst(toezegging)
        for toezegging in toezeggingen
    ]

    corpus = [
        documenttekst,
        *toezeggingsteksten
    ]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True
    )

    matrix = vectorizer.fit_transform(corpus)

    document_vector = matrix[0:1]
    toezegging_vectoren = matrix[1:]

    similarities = cosine_similarity(
        document_vector,
        toezegging_vectoren
    ).flatten()

    resultaten = []

    document_lower = volledige_tekst.lower()

    for index, similarity in enumerate(similarities):
        toezegging = toezeggingen[index]
        nummer = toezegging.get("Nummer") or ""

        bonus = 0.0

        # Zeer sterk signaal:
        # het toezeggingnummer staat letterlijk in de brief.
        if nummer and nummer.lower() in document_lower:
            bonus += 0.50

        score = min(
            1.0,
            float(similarity) + bonus
        )

        resultaten.append({
            "toezegging": toezegging,
            "similarity": float(similarity),
            "bonus": bonus,
            "score": score,
        })

    resultaten.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return resultaten[:maximum]
