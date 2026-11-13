from get_toezeggingen import (
    get_open_toezeggingen,
    get_recent_afgedane_toezeggingen,
    combineer_toezeggingen,
    get_relevante_activiteiten,
    vul_ontbrekende_activiteiten_aan,
    get_volgcommissie_actoren,
    get_commissies,
    get_toezeggingen_per_commissie,
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

    recent_afgedaan = (
        get_recent_afgedane_toezeggingen(
            aantal_dagen=14
        )
    )

    print(
        f"Actueel open/deels afgedaan: "
        f"{len(toezeggingen)}"
    )

    print(
        f"Recent afgedaan: "
        f"{len(recent_afgedaan)}"
    )

    toezeggingen = combineer_toezeggingen(
        toezeggingen,
        recent_afgedaan
    )

    print(
        f"Gecombineerde set: "
        f"{len(toezeggingen)}"
    )

    activiteiten = get_relevante_activiteiten()

    activiteiten, uitgesloten_activiteitnummers = (
        vul_ontbrekende_activiteiten_aan(
            toezeggingen,
            activiteiten
        )
    )

    volgcommissie_actoren = (
        get_volgcommissie_actoren()
    )

    commissies = get_commissies()

    ienw = get_toezeggingen_per_commissie(
        toezeggingen,
        activiteiten,
        volgcommissie_actoren,
        commissies,
        commissie_afkorting="ienw",
        uitgesloten_activiteitnummers=(
            uitgesloten_activiteitnummers
        ),
    )

    print(
        f"\nAantal IenW-toezeggingen: "
        f"{len(ienw)}"
    )

    print("\nCONTROLE BEKENDE LUCHTVAARTTOEZEGGINGEN:\n")

    controle_nummers = {
        "TZ202610-188",
        "TZ202610-189",
        "TZ202610-191",
        "TZ202605-005",
    }

    gevonden_nummers = set()

    for toezegging in ienw:
        nummer = toezegging.get("Nummer")

        if nummer in controle_nummers:
            gevonden_nummers.add(nummer)

            print(
                nummer,
                "| status:",
                toezegging.get("Status"),
                "| DatumNakoming:",
                toezegging.get("DatumNakoming"),
                "| KamerbriefNakoming:",
                toezegging.get("KamerbriefNakoming"),
            )

    ontbrekend = (
        controle_nummers
        - gevonden_nummers
    )

    if ontbrekend:
        print(
            "\nNiet aanwezig in IenW-selectie:",
            ", ".join(sorted(ontbrekend))
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
            "| status:",
            toezegging.get("Status"),
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
