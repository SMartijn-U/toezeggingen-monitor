from get_toezeggingen import (
    get_open_toezeggingen,
    get_relevante_activiteiten,
    vul_ontbrekende_activiteiten_aan,
    get_volgcommissie_actoren,
    get_commissies,
    get_ienw_toezeggingen,
)

from document_text import get_document_text

from match_candidates import (
    rangschik_kandidaten
)


TEST_DOCUMENT = {
    "Id": "7f493f98-10f7-4a2a-bc6e-05d885fba0d9",
    "Soort": "Brief regering",
    "Nummer": "2026D56295",
    "Titel": None,
    "Onderwerp": "Aanpak verduurzaming luchtvaart",
    "ContentType": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
}


if __name__ == "__main__":
    print("IenW-toezeggingen ophalen...")

    toezeggingen = get_open_toezeggingen()

    activiteiten = get_relevante_activiteiten()

    activiteiten = (
        vul_ontbrekende_activiteiten_aan(
            toezeggingen,
            activiteiten
        )
    )

    volgcommissie_actoren = (
        get_volgcommissie_actoren()
    )

    commissies = get_commissies()

    ienw = get_ienw_toezeggingen(
        toezeggingen,
        activiteiten,
        volgcommissie_actoren,
        commissies
    )

    print(
        f"\nAantal IenW-toezeggingen: "
        f"{len(ienw)}"
    )

    print("\nTestbrief uitlezen...")

    brieftekst = get_document_text(
        TEST_DOCUMENT
    )

    print(
        f"Brieftekst: "
        f"{len(brieftekst)} tekens"
    )

    kandidaten = rangschik_kandidaten(
        TEST_DOCUMENT,
        brieftekst,
        ienw,
        maximum=20
    )

    print("\nTOP 20 KANDIDATEN:\n")

    for positie, kandidaat in enumerate(
        kandidaten,
        start=1
    ):
        toezegging = kandidaat["toezegging"]

        print(
            positie,
            "|",
            toezegging.get("Nummer"),
            "| score:",
            round(
                kandidaat["score"],
                4
            ),
            "| tfidf:",
            round(
                kandidaat["similarity"],
                4
            ),
            "| bonus:",
            kandidaat["bonus"],
        )

        print(
            "   ",
            toezegging.get("Tekst")
        )

        print()
