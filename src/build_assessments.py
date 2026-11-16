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


MAX_BEOORDELINGSEENHEDEN = 10
MAX_KANDIDATEN_PER_COMMISSIE = 10

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

def maak_eenheidsleutel(
    documentnummer,
    commissie_slug
):
    return (
        f"{commissie_slug}|"
        f"{documentnummer}"
    )

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


def selecteer_beoordelingseenheden(
    data,
    historie
):
    documenten = data.get(
        "documenten",
        []
    )

    beschikbare_eenheden = {}
    eenheden_per_commissie = {}

    for document in documenten:
        documentnummer = document.get(
            "documentnummer"
        )

        if not documentnummer:
            continue

        for commissie in document.get(
            "commissies",
            []
        ):
            commissie_slug = commissie.get(
                "commissie_slug"
            )

            kandidaten = commissie.get(
                "kandidaten",
                []
            )

            if (
                not commissie_slug
                or not kandidaten
            ):
                continue

            sleutel = maak_eenheidsleutel(
                documentnummer,
                commissie_slug
            )

            eenheid = {
                "sleutel": sleutel,
                "document": document,
                "commissie": commissie,
            }

            beschikbare_eenheden[
                sleutel
            ] = eenheid

            eenheden_per_commissie.setdefault(
                commissie_slug,
                []
            ).append(
                eenheid
            )

    geselecteerd = []
    geselecteerde_sleutels = set()

    # 1. Mislukte beoordelingseenheden
    # krijgen altijd voorrang.
    for sleutel in historie[
        "wacht_op_herhaling"
    ]:
        eenheid = beschikbare_eenheden.get(
            sleutel
        )

        if not eenheid:
            continue

        if sleutel in historie[
            "verwerkt"
        ]:
            continue

        if sleutel in geselecteerde_sleutels:
            continue

        geselecteerd.append(
            eenheid
        )

        geselecteerde_sleutels.add(
            sleutel
        )

        if (
            len(geselecteerd)
            >= MAX_BEOORDELINGSEENHEDEN
        ):
            return geselecteerd

    # 2. Nieuwe beoordelingseenheden:
    # round-robin over commissies.
    #
    # Per ronde wordt maximaal één nieuwe
    # beoordelingseenheid per commissie
    # toegevoegd.
    commissie_slugs = list(
        eenheden_per_commissie.keys()
    )

    laatste_commissie_slug = (
        historie.get(
            "round_robin",
            {}
        ).get(
            "laatste_commissie_slug"
        )
    )

    if (
        laatste_commissie_slug
        and laatste_commissie_slug
        in commissie_slugs
    ):
        laatste_index = (
            commissie_slugs.index(
                laatste_commissie_slug
            )
        )

        commissie_slugs = (
            commissie_slugs[
                laatste_index + 1:
            ]
            + commissie_slugs[
                :laatste_index + 1
            ]
        )

    positie_per_commissie = {
        commissie_slug: 0
        for commissie_slug in commissie_slugs
    }

    laatst_geselecteerde_commissie_slug = None

    while (
        len(geselecteerd)
        < MAX_BEOORDELINGSEENHEDEN
    ):
        iets_toegevoegd = False
        commissie_met_onverwerkte_eenheden = False

        for commissie_slug in commissie_slugs:
            if (
                len(geselecteerd)
                >= MAX_BEOORDELINGSEENHEDEN
            ):
                break

            eenheden = eenheden_per_commissie[
                commissie_slug
            ]

            positie = positie_per_commissie[
                commissie_slug
            ]

            while positie < len(eenheden):
                eenheid = eenheden[positie]
                sleutel = eenheid["sleutel"]

                positie += 1

                if sleutel in historie[
                    "verwerkt"
                ]:
                    continue

                if sleutel in geselecteerde_sleutels:
                    continue

                commissie_met_onverwerkte_eenheden = True

                geselecteerd.append(
                    eenheid
                )

                geselecteerde_sleutels.add(
                    sleutel
                )

                laatst_geselecteerde_commissie_slug = (
                    commissie_slug
                )
                
                iets_toegevoegd = True
                break

            positie_per_commissie[
                commissie_slug
            ] = positie

        if not iets_toegevoegd:
            break

        if not commissie_met_onverwerkte_eenheden:
            break

    if laatst_geselecteerde_commissie_slug:
        historie.setdefault(
            "round_robin",
            {}
        )[
            "laatste_commissie_slug"
        ] = (
            laatst_geselecteerde_commissie_slug
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
    documenttekst,
    commissie
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
        "commissie_id":
            commissie.get(
                "commissie_id"
            ),

        "commissie_afkorting":
            commissie.get(
                "commissie_afkorting"
            ),

        "commissie_naam":
            commissie.get(
                "commissie_naam"
            ),

        "commissie_slug":
            commissie.get(
                "commissie_slug"
            ),

        "selectiereden":
            kandidaat.get(
                "selectiereden"
            ),

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


def verwerk_beoordelingseenheid(
    document,
    commissie
):
    documentnummer = document.get(
        "documentnummer"
    )

    commissie_afkorting = commissie.get(
        "commissie_afkorting"
    )

    commissie_slug = commissie.get(
        "commissie_slug"
    )

    print(
        f"\nBeoordelingseenheid: "
        f"{commissie_afkorting} | "
        f"{documentnummer} | "
        f"{document.get('onderwerp')}"
    )

    metadata = maak_documentmetadata(
        document
    )

    documenttekst = get_document_text(
        metadata
    )

    kandidaten = commissie.get(
        "kandidaten",
        []
    )[:MAX_KANDIDATEN_PER_COMMISSIE]

    print(
        f"Aantal kandidaten voor "
        f"{commissie_afkorting}: "
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
        if kandidaat.get(
            "toezeggingnummer"
        )
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
            documenttekst,
            commissie
        )

        beoordelingen.append(
            record
        )

        print(
            commissie_afkorting,
            "|",
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
        "verwerkingssleutel":
            maak_eenheidsleutel(
                documentnummer,
                commissie_slug
            ),

        "commissie_id":
            commissie.get(
                "commissie_id"
            ),

        "commissie_afkorting":
            commissie_afkorting,

        "commissie_naam":
            commissie.get(
                "commissie_naam"
            ),

        "commissie_slug":
            commissie_slug,

        "document_id":
            document.get("document_id"),

        "documentnummer":
            documentnummer,

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

    commissie_slug = (
        document_resultaat.get(
            "commissie_slug"
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
            f"{commissie_slug}|"
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

            "commissie_id":
                document_resultaat.get(
                    "commissie_id"
                ),

            "commissie_afkorting":
                document_resultaat.get(
                    "commissie_afkorting"
                ),

            "commissie_naam":
                document_resultaat.get(
                    "commissie_naam"
                ),

            "commissie_slug":
                commissie_slug,

            "selectiereden":
                beoordeling.get(
                    "selectiereden"
                ),
            
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
                    "commissie_id":
                        document.get(
                            "commissie_id"
                        ),

                    "commissie_afkorting":
                        document.get(
                            "commissie_afkorting"
                        ),

                    "commissie_naam":
                        document.get(
                            "commissie_naam"
                        ),

                    "commissie_slug":
                        document.get(
                            "commissie_slug"
                        ),

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
            "maximum_beoordelingseenheden":
                MAX_BEOORDELINGSEENHEDEN,

            "maximum_kandidaten_per_commissie":
                MAX_KANDIDATEN_PER_COMMISSIE,

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

    beoordelingseenheden = (
        selecteer_beoordelingseenheden(
            data,
            historie
        )
    )

    print(
        f"Beoordelingseenheden geselecteerd: "
        f"{len(beoordelingseenheden)}"
    )

    for eenheid in beoordelingseenheden:
        document = eenheid["document"]
        commissie = eenheid["commissie"]

        print(
            "-",
            eenheid["sleutel"],
            "|",
            commissie.get(
                "commissie_afkorting"
            ),
            "|",
            document.get(
                "documentnummer"
            ),
            "|",
            document.get(
                "onderwerp"
            ),
        )

    resultaten = []
    fouten = []

    for index, eenheid in enumerate(
        beoordelingseenheden,
        start=1
    ):
        document = eenheid["document"]
        commissie = eenheid["commissie"]
        sleutel = eenheid["sleutel"]
 
        print(
            f"\nBeoordelingseenheid "
            f"{index}/"
            f"{len(beoordelingseenheden)}"
        )


        try:
            resultaat = (
                verwerk_beoordelingseenheid(
                    document,
                    commissie
                )
            )

            resultaten.append(
                resultaat
            )
            nummer = document.get(
                "documentnummer"
            )

            historie[
                "verwerkt"
            ][sleutel] = {
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

                "commissie_slug":
                    commissie.get(
                        "commissie_slug"
                    ),

                "commissie_afkorting":
                    commissie.get(
                        "commissie_afkorting"
                    ),
            }

            historie[
                "wacht_op_herhaling"
            ].pop(
                sleutel,
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
                "sleutel":
                    sleutel,

                "documentnummer":
                    nummer,

                "commissie_slug":
                    commissie.get(
                        "commissie_slug"
                    ),

                "commissie_afkorting":
                    commissie.get(
                        "commissie_afkorting"
                    ),

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
                sleutel,
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
            ][sleutel] = {
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

                "commissie_slug":
                    commissie.get(
                        "commissie_slug"
                    ),

                "commissie_afkorting":
                    commissie.get(
                        "commissie_afkorting"
                    ),
                
                "laatste_fout":
                    str(fout),
            }

            print(
                "Beoordelingseenheid in "
                "wachtrij geplaatst:",
                sleutel,
                "| pogingen:",
                pogingen
            )

        # Gratis Gemini-tier ontlasten.
        if index < len(
            beoordelingseenheden
        ):
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

    print("\nBEOORDELINGSSAMENVATTING:")

    print(
        "Beoordelingseenheden verwerkt:",
        len(resultaten)
    )

    print(
        "Beoordelingseenheden met fout:",
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
