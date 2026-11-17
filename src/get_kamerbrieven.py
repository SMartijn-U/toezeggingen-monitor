from datetime import datetime, timedelta, timezone

from document_text import get_document_text
from odata import get_met_retries


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v5"


RELEVANTE_DOCUMENTSOORTEN = {
    "Brief regering",
    "Memorie van toelichting",
}

def verrijk_document_met_zaakcommissies(
    document
):
    zaak_ids = []
    zaak_commissies = []
    zaak_commissie_ids = set()

    for zaak in document.get(
        "Zaak",
        []
    ):
        zaak_id = zaak.get("Id")

        if zaak_id:
            zaak_ids.append(
                zaak_id
            )

        for actor in zaak.get(
            "ZaakActor",
            []
        ):
            relatie = actor.get(
                "Relatie"
            )

            if relatie not in {
                "Voortouwcommissie",
                "Volgcommissie",
            }:
                continue

            commissie_id = actor.get(
                "Commissie_Id"
            )

            commissie = actor.get(
                "Commissie"
            ) or {}

            if not commissie_id:
                commissie_id = commissie.get(
                    "Id"
                )

            if not commissie_id:
                continue

            sleutel = (
                zaak_id,
                commissie_id,
                relatie,
            )

            bestaand = {
                (
                    item.get("zaak_id"),
                    item.get("commissie_id"),
                    item.get("rol"),
                )
                for item in zaak_commissies
            }

            if sleutel in bestaand:
                continue

            zaak_commissie_ids.add(
                commissie_id
            )

            zaak_commissies.append({
                "zaak_id":
                    zaak_id,

                "commissie_id":
                    commissie_id,

                "commissie_afkorting": (
                    actor.get(
                        "ActorAfkorting"
                    )
                    or commissie.get(
                        "Afkorting"
                    )
                    or ""
                ),

                "commissie_naam": (
                    actor.get(
                        "ActorNaam"
                    )
                    or commissie.get(
                        "NaamNL"
                    )
                    or commissie.get(
                        "NaamWebNL"
                    )
                    or ""
                ),

                "rol":
                    relatie,
            })

    document[
        "ZaakIds"
    ] = zaak_ids

    document[
        "ZaakCommissieIds"
    ] = sorted(
        zaak_commissie_ids
    )

    document[
        "ZaakCommissies"
    ] = zaak_commissies

    return document

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
            "$expand": (
                "Zaak("
                "$expand=ZaakActor("
                "$expand=Commissie"
                ")"
                ")"
            ),
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

        batch = [
            verrijk_document_met_zaakcommissies(
                document
            )
            for document in batch
        ]

        alle_documenten.extend(batch)data = response.json()
        
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
            "| zaken:",
            document.get(
                "ZaakIds",
                []
            ),
            "| zaakcommissies:",
            [
                (
                    commissie.get(
                        "commissie_afkorting"
                    ),
                    commissie.get(
                        "rol"
                    ),
                )
                for commissie
                in document.get(
                    "ZaakCommissies",
                    []
                )
            ],
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
