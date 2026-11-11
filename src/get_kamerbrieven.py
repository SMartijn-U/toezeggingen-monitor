from datetime import datetime, timedelta, timezone

from document_text import get_document_text
from odata import get_met_retries


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v5"


RELEVANTE_DOCUMENTSOORTEN = {
    "Brief regering",
    "Memorie van toelichting",
}


def get_recente_documenten(aantal_dagen=7):
    url = f"{BASE_URL}/Document"

    nu = datetime.now(timezone.utc)
    vanaf = nu - timedelta(days=aantal_dagen)

    vanaf_datum = vanaf.strftime(
        "%Y-%m-%dT00:00:00Z"
    )

    print(
        f"Documenten ophalen vanaf: "
        f"{vanaf_datum}"
    )

    soort_filter = " or ".join(
        f"Soort eq '{soort}'"
        for soort in RELEVANTE_DOCUMENTSOORTEN
    )

    volledig_filter = (
        f"({soort_filter}) "
        f"and Datum ge {vanaf_datum} "
        "and Verwijderd eq false"
    )

    alle_documenten = []
    skip = 0
    batch_size = 100

    while True:
        params = {
            "$filter": volledig_filter,
            "$top": str(batch_size),
            "$skip": str(skip),
        }

        response = get_met_retries(
            url,
            params=params,
            timeout=60
        )

        data = response.json()
        batch = data.get("value", [])

        alle_documenten.extend(batch)

        print(
            f"Documenten opgehaald: "
            f"{len(batch)} "
            f"(totaal: {len(alle_documenten)})"
        )

        if len(batch) < batch_size:
            break

        skip += batch_size

    return alle_documenten


if __name__ == "__main__":
    documenten = get_recente_documenten(
        aantal_dagen=7
    )

    print(
        f"\nTotaal recente relevante documenten: "
        f"{len(documenten)}"
    )

    print("\nRECENTE RELEVANTE DOCUMENTEN:\n")

    for document in documenten:
        print(
            document.get("Datum"),
            "|",
            document.get("Soort"),
            "|",
            document.get("Nummer"),
            "|",
            document.get("Onderwerp"),
            "|",
            document.get("ContentType"),
            "| ID:",
            document.get("Id"),
        )
    
    print(
        "\nTEST VOLLEDIGE DOCUMENTTEKST:\n"
    )

    for document in documenten[:5]:
        try:
            tekst = get_document_text(document)

            print(
                document.get("Nummer"),
                "|",
                document.get("Soort"),
                "|",
                len(tekst),
                "tekens",
                "| OK"
            )

        except Exception as fout:
            print(
                document.get("Nummer"),
                "|",
                document.get("Soort"),
                "| FOUT:",
                fout
            )
