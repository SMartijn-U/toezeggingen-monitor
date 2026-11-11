import json
from pathlib import Path

from document_text import get_document_text
from gemini_assessor import beoordeel_document

from evidence_validator import (
    valideer_beoordeling
)

CANDIDATES_PATH = Path(
    "data/candidates.json"
)

TEST_DOCUMENTNUMMER = "2026D56295"


def main():
    data = json.loads(
        CANDIDATES_PATH.read_text(
            encoding="utf-8"
        )
    )

    document = None

    for item in data["documenten"]:
        if (
            item.get("documentnummer")
            == TEST_DOCUMENTNUMMER
        ):
            document = item
            break

    if not document:
        raise RuntimeError(
            f"{TEST_DOCUMENTNUMMER} "
            "niet gevonden."
        )

    documenten_metadata = {
        "Id": document["document_id"],
        "Nummer": document[
            "documentnummer"
        ],
        "Soort": document[
            "documentsoort"
        ],
        "Datum": document["datum"],
        "Onderwerp": document[
            "onderwerp"
        ],
        "ContentType": document[
            "content_type"
        ],
    }

    print(
        "Testdocument:",
        document["documentnummer"],
        "|",
        document["onderwerp"]
    )

    documenttekst = get_document_text(
        documenten_metadata
    )

    kandidaten = document[
        "kandidaten"
    ][:10]

    print(
        f"Aantal kandidaten voor Gemini: "
        f"{len(kandidaten)}"
    )

    resultaat = beoordeel_document(
        document,
        documenttekst,
        kandidaten
    )

    print(
        "\nGEMINI-BEOORDELINGEN:\n"
    )

    for beoordeling in (
        resultaat.beoordelingen
    ):
        print(
            beoordeling.toezeggingnummer,
            "|",
            beoordeling.oordeel,
            "| expliciet:",
            beoordeling.expliciete_verwijzing
        )

        print(
            "Gedekt:",
            beoordeling.gedekte_onderdelen
        )

        print(
            "Ontbreekt:",
            beoordeling.ontbrekende_onderdelen
        )

        print(
            "Bewijs:",
            beoordeling.bewijsfragmenten
        )

        print(
            "Motivering:",
            beoordeling.motivering
        )

        # Controleer of de bewijsfragmenten
        # letterlijk in de brief voorkomen.
        validatie = valideer_beoordeling(
            beoordeling,
            documenttekst
        )

        print(
            "Bewijsvalidatie:",
            validatie["aantal_geldig"],
            "/",
            validatie["aantal_fragmenten"],
            "fragmenten letterlijk gevonden"
        )

        for fragment_resultaat in (
            validatie["fragmenten"]
        ):
            status = (
                "GELDIG"
                if fragment_resultaat["geldig"]
                else "NIET GEVONDEN"
            )

            print(
                "   ",
                status,
                "|",
                fragment_resultaat["fragment"],
            )

        # HARDE VEILIGHEIDSREGEL:
        # een positief oordeel mag alleen worden
        # gepubliceerd als alle bewijsfragmenten
        # daadwerkelijk in het document staan.
        positieve_oordelen = {
            "zeker_afgedaan",
            "zeer_waarschijnlijk_afgedaan",
            "waarschijnlijk_afgedaan",
            "mogelijk_deels_afgedaan",
        }

        publiceerbaar = True

        if (
            beoordeling.oordeel in positieve_oordelen
            and not validatie["alle_geldig"]
        ):
            publiceerbaar = False

        print(
            "Publiceerbaar:",
            publiceerbaar
        )

        print()
        

if __name__ == "__main__":
    main()
