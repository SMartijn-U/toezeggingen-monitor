import json
import time
from pathlib import Path


from document_text import get_document_text
from evidence_validator import valideer_beoordeling
from gemini_assessor import beoordeel_document

from datetime import datetime, timezone

from state_store import (
    laad_historie,
    schrijf_historie,
    laad_gepubliceerde_resultaten,
    schrijf_gepubliceerde_resultaten,
)


INPUT_PATH = Path(
    "data/candidates.json"
)

OUTPUT_PATH = Path(
    "data/assessments.json"
)


MAX_DOCUMENTEN = 10
MAX_KANDIDATEN_PER_DOCUMENT = 10

BEKEND_TESTDOCUMENT = "2026D56295"


POSITIEVE_OORDELEN = {
    "zeker_afgedaan",
    "zeer_waarschijnlijk_afgedaan",
    "waarschijnlijk_afgedaan",
    "mogelijk_deels_afgedaan",
}


RAPPORTAGECATEGORIEEN = {
    "zeker_afgedaan":
        "Hoge zekerheid: mogelijke afdoening",

    "zeer_waarschijnlijk_afgedaan":
        "Hoge zekerheid: mogelijke afdoening",

    "waarschijnlijk_afgedaan":
        "Mogelijke afdoening",

    "mogelijk_deels_afgedaan":
        "Mogelijk gedeeltelijk afgedaan",

    "waarschijnlijk_niet_afgedaan":
        "Niet rapporteren",

    "niet_afgedaan":
        "Niet rapporteren",
}


def nu_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()

def laad_kandidaten():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Bestand ontbreekt: {INPUT_PATH}"
        )

    return json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )


def selecteer_pilotdocumenten(
    data,
    historie
):
    documenten = data.get(
        "documenten",
        []
    )

    per_nummer = {
        document.get(
            "documentnummer"
        ): document
        for document in documenten
        if document.get(
            "documentnummer"
        )
    }

    geselecteerd = []

    # 1. Eerst documenten die eerder
    # door bijvoorbeeld een Gemini-503
    # niet verwerkt konden worden.
    for nummer in historie[
        "wacht_op_herhaling"
    ]:
        document = per_nummer.get(
            nummer
        )

        if not document:
            continue

        if nummer in historie[
            "verwerkt"
        ]:
            continue

        geselecteerd.append(
            document
        )

        if (
            len(geselecteerd)
            >= MAX_DOCUMENTEN
        ):
            return geselecteerd

    # 2. Daarna nieuwe documenten.
    for document in documenten:
        if (
            len(geselecteerd)
            >= MAX_DOCUMENTEN
        ):
            break

        nummer = document.get(
            "documentnummer"
        )

        if not nummer:
            continue

        if nummer in historie[
            "verwerkt"
        ]:
            continue

        reeds_geselecteerd = any(
            bestaand.get(
                "documentnummer"
            )
            == nummer
            for bestaand in geselecteerd
        )

        if not reeds_geselecteerd:
            geselecteerd.append(
                document
            )

    return geselecteerd

def maak_documentmetadata(document):
    return {
        "Id": document.get(
            "document_id"
        ),
        "Nummer": document.get(
            "documentnummer"
        ),
        "Soort": document.get(
            "documentsoort"
        ),
        "Datum": document.get(
            "datum"
        ),
        "Onderwerp": document.get(
            "onderwerp"
        ),
        "ContentType": document.get(
            "content_type"
        ),
    }


def maak_beoordelingsrecord(
    beoordeling,
    kandidaat,
    documenttekst
):
    validatie = valideer_beoordeling(
        beoordeling,
        documenttekst
    )

    status_registratie = kandidaat.get(
        "status"
    )

    status_nog_actief = (
        status_registratie
        in {
            "Openstaand",
            "Deels Afgedaan",
        }
    )

    positief = (
        beoordeling.oordeel
        in POSITIEVE_OORDELEN
    )

    publiceerbaar = (
        positief
        and validatie["alle_geldig"]
        and status_nog_actief
    )

    categorie = (
        RAPPORTAGECATEGORIEEN.get(
            beoordeling.oordeel,
            "Niet rapporteren"
        )
    )

    if positief and not publiceerbaar:
        categorie = (
            "Niet publiceren: "
            "bewijs niet gevalideerd"
        )

    return {
        "toezeggingnummer":
            beoordeling.toezeggingnummer,

        "status_registratie":
            kandidaat.get("status"),

        "positie_kandidaat":
            kandidaat.get("positie"),

        "tfidf_score":
            kandidaat.get("tfidf_score"),

        "oordeel":
            beoordeling.oordeel,

        "rapportagecategorie":
            categorie,

        "expliciete_verwijzing":
            beoordeling.expliciete_verwijzing,

        "gedekte_onderdelen":
            beoordeling.gedekte_onderdelen,

        "ontbrekende_onderdelen":
            beoordeling.ontbrekende_onderdelen,

        "bewijsfragmenten":
            beoordeling.bewijsfragmenten,

        "motivering":
            beoordeling.motivering,

        "bewijsvalidatie":
            validatie,

        "publiceerbaar":
            publiceerbaar,
    }


def verwerk_document(document):
    nummer = document.get(
        "documentnummer"
    )

    print(
        f"\nDocument beoordelen: "
        f"{nummer} | "
        f"{document.get('onderwerp')}"
    )

    metadata = maak_documentmetadata(
        document
    )

    documenttekst = get_document_text(
        metadata
    )

    kandidaten = document.get(
        "kandidaten",
        []
    )[:MAX_KANDIDATEN_PER_DOCUMENT]

    print(
        f"Aantal kandidaten: "
        f"{len(kandidaten)}"
    )

    resultaat = beoordeel_document(
        document,
        documenttekst,
        kandidaten
    )

    kandidaten_op_nummer = {
        kandidaat.get(
            "toezeggingnummer"
        ): kandidaat
        for kandidaat in kandidaten
    }

    beoordelingen = []

    ontvangen_nummers = set()

    for beoordeling in (
        resultaat.beoordelingen
    ):
        nummer_toezegging = (
            beoordeling.toezeggingnummer
        )

        ontvangen_nummers.add(
            nummer_toezegging
        )

        kandidaat = (
            kandidaten_op_nummer.get(
                nummer_toezegging
            )
        )

        if not kandidaat:
            print(
                "WAARSCHUWING: Gemini gaf "
                "een onbekend toezeggingnummer:",
                nummer_toezegging
            )
            continue

        record = maak_beoordelingsrecord(
            beoordeling,
            kandidaat,
            documenttekst
        )

        beoordelingen.append(
            record
        )

        print(
            nummer_toezegging,
            "|",
            record["oordeel"],
            "| bewijs:",
            record["bewijsvalidatie"][
                "aantal_geldig"
            ],
            "/",
            record["bewijsvalidatie"][
                "aantal_fragmenten"
            ],
            "| publiceerbaar:",
            record["publiceerbaar"],
        )

    verwachte_nummers = set(
        kandidaten_op_nummer
    )

    ontbrekende_beoordelingen = sorted(
        verwachte_nummers
        - ontvangen_nummers
    )

    if ontbrekende_beoordelingen:
        print(
            "WAARSCHUWING: geen beoordeling "
            "ontvangen voor:",
            ", ".join(
                ontbrekende_beoordelingen
            )
        )

    return {
        "document_id":
            document.get("document_id"),

        "documentnummer":
            nummer,

        "documentsoort":
            document.get("documentsoort"),

        "datum":
            document.get("datum"),

        "onderwerp":
            document.get("onderwerp"),

        "aantal_tekens":
            len(documenttekst),

        "aantal_kandidaten":
            len(kandidaten),

        "aantal_beoordelingen":
            len(beoordelingen),

        "ontbrekende_beoordelingen":
            ontbrekende_beoordelingen,

        "beoordelingen":
            beoordelingen,
    }


def bewaar_publiceerbare_resultaten(
    document_resultaat,
    gepubliceerde_resultaten
):
    resultaten = gepubliceerde_resultaten[
        "resultaten"
    ]

    documentnummer = (
        document_resultaat.get(
            "documentnummer"
        )
    )

    for beoordeling in (
        document_resultaat.get(
            "beoordelingen",
            []
        )
    ):
        if not beoordeling.get(
            "publiceerbaar"
        ):
            continue

        toezeggingnummer = (
            beoordeling.get(
                "toezeggingnummer"
            )
        )

        sleutel = (
            f"{toezeggingnummer}|"
            f"{documentnummer}"
        )

        if sleutel in resultaten:
            continue

        resultaten[sleutel] = {
            "sleutel":
                sleutel,

            "eerste_signalering":
                nu_iso(),

            "toezeggingnummer":
                toezeggingnummer,

            "status_registratie":
                beoordeling.get(
                    "status_registratie"
                ),

            "documentnummer":
                documentnummer,

            "documentsoort":
                document_resultaat.get(
                    "documentsoort"
                ),

            "documentdatum":
                document_resultaat.get(
                    "datum"
                ),

            "documentonderwerp":
                document_resultaat.get(
                    "onderwerp"
                ),

            "oordeel":
                beoordeling.get(
                    "oordeel"
                ),

            "rapportagecategorie":
                beoordeling.get(
                    "rapportagecategorie"
                ),

            "expliciete_verwijzing":
                beoordeling.get(
                    "expliciete_verwijzing"
                ),

            "gedekte_onderdelen":
                beoordeling.get(
                    "gedekte_onderdelen"
                ),

            "ontbrekende_onderdelen":
                beoordeling.get(
                    "ontbrekende_onderdelen"
                ),

            "bewijsfragmenten":
                beoordeling.get(
                    "bewijsfragmenten"
                ),

            "motivering":
                beoordeling.get(
                    "motivering"
                ),

            "bewijsvalidatie":
                beoordeling.get(
                    "bewijsvalidatie"
                ),
        }

        print(
            "Nieuwe RSS-kandidaat bewaard:",
            sleutel
        )

def schrijf_output(
    resultaten,
    fouten
):
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    publiceerbare_resultaten = []

    for document in resultaten:
        for beoordeling in document.get(
            "beoordelingen",
            []
        ):
            if beoordeling.get(
                "publiceerbaar"
            ):
                publiceerbare_resultaten.append({
                    "documentnummer":
                        document.get(
                            "documentnummer"
                        ),

                    "documentsoort":
                        document.get(
                            "documentsoort"
                        ),

                    "documentdatum":
                        document.get(
                            "datum"
                        ),

                    "documentonderwerp":
                        document.get(
                            "onderwerp"
                        ),

                    **beoordeling,
                })

    output = {
        "samenvatting": {
            "maximum_documenten":
                MAX_DOCUMENTEN,

            "maximum_kandidaten_per_document":
                MAX_KANDIDATEN_PER_DOCUMENT,

            "documenten_verwerkt":
                len(resultaten),

            "documenten_met_fout":
                len(fouten),

            "publiceerbare_resultaten":
                len(
                    publiceerbare_resultaten
                ),

            "waarschuwing": (
                "Publiceerbaar betekent alleen "
                "dat Gemini een positief oordeel "
                "gaf en alle bewijsfragmenten "
                "letterlijk zijn teruggevonden. "
                "Menselijke controle blijft nodig."
            ),
        },

        "documenten": resultaten,

        "publiceerbare_resultaten":
            publiceerbare_resultaten,

        "fouten": fouten,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"\nResultaten opgeslagen in: "
        f"{OUTPUT_PATH}"
    )


def main():
    data = laad_kandidaten()

    historie = laad_historie()

    gepubliceerde_resultaten = (
        laad_gepubliceerde_resultaten()
    )

    documenten = (
        selecteer_pilotdocumenten(
            data,
            historie
        )
    )

    print(
        f"Pilotdocumenten geselecteerd: "
        f"{len(documenten)}"
    )

    for document in documenten:
        print(
            "-",
            document.get(
                "documentnummer"
            ),
            "|",
            document.get(
                "documentsoort"
            ),
            "|",
            document.get(
                "onderwerp"
            ),
        )

    resultaten = []
    fouten = []

    for index, document in enumerate(
        documenten,
        start=1
    ):
        print(
            f"\nPilotdocument "
            f"{index}/{len(documenten)}"
        )

        try:
            resultaat = verwerk_document(
                document
            )

            resultaten.append(
                resultaat
            )
            nummer = document.get(
                "documentnummer"
            )

            historie[
                "verwerkt"
            ][nummer] = {
                "datum_verwerkt":
                    nu_iso(),

                "documentdatum":
                    document.get(
                        "datum"
                    ),

                "onderwerp":
                    document.get(
                        "onderwerp"
                    ),
            }

            historie[
                "wacht_op_herhaling"
            ].pop(
                nummer,
                None
            )

            bewaar_publiceerbare_resultaten(
                resultaat,
                gepubliceerde_resultaten
            )            

        except Exception as fout:
            nummer = document.get(
                "documentnummer"
            )

            fout_record = {
                "documentnummer":
                    nummer,

                "onderwerp":
                    document.get(
                        "onderwerp"
                    ),

                "fout":
                    str(fout),
            }

            fouten.append(
                fout_record
            )

            print(
                "FOUT:",
                fout_record
            )

            # Kijk of dit document al eerder
            # in de wachtrij stond.
            eerder = historie[
                "wacht_op_herhaling"
            ].get(
                nummer,
                {}
            )

            # Tel deze mislukte poging erbij op.
            pogingen = (
                eerder.get(
                    "pogingen",
                    0
                )
                + 1
            )

            # Bewaar het document in de wachtrij
            # voor een volgende GitHub-run.
            historie[
                "wacht_op_herhaling"
            ][nummer] = {
                "pogingen":
                    pogingen,

                "laatste_poging":
                    nu_iso(),

                "documentdatum":
                    document.get(
                        "datum"
                    ),

                "onderwerp":
                    document.get(
                        "onderwerp"
                    ),

                "laatste_fout":
                    str(fout),
            }

            print(
                "Document in wachtrij geplaatst:",
                nummer,
                "| pogingen:",
                pogingen
            )

        # Gratis Gemini-tier ontlasten.
        if index < len(documenten):
            wachttijd = 30
            
            print(
                f"{wachttijd} seconden wachten "
                f"voor het volgende document..."
            )

            time.sleep(wachttijd)

        # Tussenresultaten na ieder document
        # veiligstellen.
        schrijf_output(
            resultaten,
            fouten
        )
        schrijf_historie(
            historie
        )

        schrijf_gepubliceerde_resultaten(
            gepubliceerde_resultaten
        )

    print("\nPILOT SAMENVATTING:")

    print(
        "Documenten verwerkt:",
        len(resultaten)
    )

    print(
        "Documenten met fout:",
        len(fouten)
    )

    totaal_publiceerbaar = sum(
        1
        for document in resultaten
        for beoordeling in document[
            "beoordelingen"
        ]
        if beoordeling[
            "publiceerbaar"
        ]
    )

    print(
        "Publiceerbare beoordelingen:",
        totaal_publiceerbaar
    )


if __name__ == "__main__":
    main()
