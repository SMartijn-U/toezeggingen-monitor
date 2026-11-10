import requests
from datetime import datetime, timezone
from collections import Counter


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"


def get_odata_paginated(
    entity,
    odata_filter=None,
    batch_size=250
):
    url = f"{BASE_URL}/{entity}"

    resultaten = []
    skip = 0

    while True:
        params = {
            "$top": str(batch_size),
            "$skip": str(skip),
        }

        if odata_filter:
            params["$filter"] = odata_filter

        response = requests.get(
            url,
            params=params,
            timeout=60
        )
        response.raise_for_status()

        data = response.json()
        batch = data.get("value", [])
        resultaten.extend(batch)

        print(
            f"{entity}: {len(batch)} opgehaald "
            f"(totaal: {len(resultaten)})"
        )

        if len(batch) < batch_size:
            break

        skip += batch_size

    return resultaten

def get_volgcommissie_actoren():
    return get_odata_paginated(
        entity="ActiviteitActor",
        odata_filter=(
            "Relatie eq 'Volgcommissie' "
            "and Verwijderd eq false"
        )
    )

def get_commissies():
    return get_odata_paginated(
        entity="Commissie",
        odata_filter="Verwijderd eq false"
    )

def get_open_toezeggingen():
    url = f"{BASE_URL}/Toezegging"

    alle_toezeggingen = []
    skip = 0
    batch_size = 250

    while True:
        params = {
            "$filter": (
                "(Status eq 'Openstaand' or Status eq 'Deels Voldaan') "
                "and Verwijderd eq false"
            ),
            "$top": str(batch_size),
            "$skip": str(skip)
        }

        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()
        batch = data.get("value", [])

        alle_toezeggingen.extend(batch)

        print(
            f"Pagina opgehaald: {len(batch)} toezeggingen "
            f"(totaal: {len(alle_toezeggingen)})"
        )

        if len(batch) < batch_size:
            break

        skip += batch_size

    return alle_toezeggingen

from datetime import datetime, timezone


from datetime import datetime, timezone


def get_relevante_activiteiten():
    url = f"{BASE_URL}/Activiteit"

    relevante_soorten = [
        "Commissiedebat",
        "Notaoverleg",
        "Wetgevingsoverleg",
        "Plenair debat (debat)",
        "Plenair debat (dertigledendebat)",
        "Plenair debat (initiatiefwetgeving)",
        "Plenair debat (interpellatiedebat)",
        "Plenair debat (overig)",
        "Plenair debat (tweeminutendebat)",
        "Plenair debat (wetgeving)",
    ]

    vandaag = datetime.now(timezone.utc)

    try:
        vijf_jaar_geleden = vandaag.replace(
            year=vandaag.year - 5
        )
    except ValueError:
        vijf_jaar_geleden = vandaag.replace(
            year=vandaag.year - 5,
            day=28
        )

    vanaf_datum = vijf_jaar_geleden.strftime(
        "%Y-%m-%dT00:00:00Z"
    )

    soort_filter = " or ".join(
        f"Soort eq '{soort}'"
        for soort in relevante_soorten
    )

    volledig_filter = (
        f"({soort_filter}) "
        f"and Datum ge {vanaf_datum} "
        "and Verwijderd eq false"
    )

    alle_activiteiten = []
    skip = 0
    batch_size = 250

    print(f"Activiteiten ophalen vanaf: {vanaf_datum}")

    while True:
        params = {
            "$filter": volledig_filter,
            "$top": str(batch_size),
            "$skip": str(skip),
        }

        response = requests.get(
            url,
            params=params,
            timeout=60
        )
        response.raise_for_status()

        data = response.json()
        batch = data.get("value", [])
        alle_activiteiten.extend(batch)

        print(
            f"Relevante activiteiten opgehaald: "
            f"{len(batch)} "
            f"(totaal: {len(alle_activiteiten)})"
        )

        if len(batch) < batch_size:
            break

        skip += batch_size

    return alle_activiteiten

def get_ienw_toezeggingen(
    toezeggingen,
    activiteiten,
    volgcommissie_actoren,
    commissies
):
    ienw = []

    zonder_activiteit = 0
    activiteit_niet_gevonden = 0
    plenair_zonder_ienw_volgcommissie = 0
    niet_gevonden_records = []

    activiteiten_op_nummer = {
        activiteit.get("Nummer"): activiteit
        for activiteit in activiteiten
        if activiteit.get("Nummer")
    }

    commissies_op_id = {
        commissie.get("Id"): commissie
        for commissie in commissies
        if commissie.get("Id")
    }

    # Maak per activiteit een verzameling van volgcommissies.
    volgcommissies_per_activiteit = {}

    # Alleen actorrecords bewaren die horen bij de
    # relevante activiteiten van de afgelopen vijf jaar.
    relevante_activiteit_ids = {
        activiteit.get("Id")
        for activiteit in activiteiten
        if activiteit.get("Id")
    }

    for actor in volgcommissie_actoren:
        activiteit_id = actor.get("Activiteit_Id")
        commissie_id = actor.get("Commissie_Id")

        if activiteit_id not in relevante_activiteit_ids:
            continue

        commissie = commissies_op_id.get(commissie_id)

        if not commissie:
            continue

        commissie_afkorting = (
            commissie.get("Afkorting") or ""
        ).strip().lower()

        commissie_naam = (
            commissie.get("NaamNL") or ""
        ).strip().lower()

        activiteit_commissies = (
            volgcommissies_per_activiteit.setdefault(
                activiteit_id,
                set()
            )
        )

        activiteit_commissies.add(
            commissie_afkorting
        )
        activiteit_commissies.add(
            commissie_naam
        )

    for toezegging in toezeggingen:
        activiteit_nummer = toezegging.get(
            "ActiviteitNummer"
        )

        if not activiteit_nummer:
            zonder_activiteit += 1
            continue

        activiteit = activiteiten_op_nummer.get(
            activiteit_nummer
        )

        if not activiteit:
            activiteit_niet_gevonden += 1

            niet_gevonden_records.append({
                "Nummer": toezegging.get("Nummer"),
                "Status": toezegging.get("Status"),
                "ActiviteitNummer": activiteit_nummer,
                "Tekst": toezegging.get("Tekst"),
            })

            continue

        soort = activiteit.get("Soort", "")
        voortouw = (
            activiteit.get("Voortouwnaam") or ""
        ).strip().lower()

        is_ienw = False
        selectiereden = None

        # Route 1: commissieactiviteiten.
        if soort in {
            "Commissiedebat",
            "Notaoverleg",
            "Wetgevingsoverleg",
        }:
            if (
                voortouw
                == "vaste commissie voor infrastructuur en waterstaat"
            ):
                is_ienw = True
                selectiereden = "IenW is voortouwcommissie"

        # Route 2: plenaire debatten.
        elif soort.startswith("Plenair debat"):
            activiteit_id = activiteit.get("Id")

            volgcommissies = (
                volgcommissies_per_activiteit.get(
                    activiteit_id,
                    set()
                )
            )

            if (
                "ienw" in volgcommissies
                or (
                    "vaste commissie voor infrastructuur "
                    "en waterstaat"
                ) in volgcommissies
            ):
                is_ienw = True
                selectiereden = "IenW is volgcommissie"
            else:
                plenair_zonder_ienw_volgcommissie += 1

        if is_ienw:
            toezegging["Activiteit"] = activiteit
            toezegging["Selectiereden"] = selectiereden
            ienw.append(toezegging)

    print(
        f"Activiteiten in index: "
        f"{len(activiteiten_op_nummer)}"
    )
    print(
        f"Activiteiten met volgcommissie: "
        f"{len(volgcommissies_per_activiteit)}"
    )
    print(
        f"Zonder ActiviteitNummer: "
        f"{zonder_activiteit}"
    )
    print(
        f"Activiteit niet gevonden: "
        f"{activiteit_niet_gevonden}"
    )
    print(
        f"Plenaire activiteiten zonder IenW "
        f"als volgcommissie: "
        f"{plenair_zonder_ienw_volgcommissie}"
    )

    print("\nNIET-GEVONDEN ACTIVITEITEN:")

    if niet_gevonden_records:
        for record in niet_gevonden_records:
            print(
                record.get("Nummer"),
                "|",
                record.get("Status"),
                "|",
                record.get("ActiviteitNummer"),
                "|",
                record.get("Tekst"),
            )
    else:
        print("Geen.")
    
    return ienw

if __name__ == "__main__":
    print("Openstaande toezeggingen ophalen...")

    toezeggingen = get_open_toezeggingen()

    print(
        f"Alle open/deels voldane toezeggingen: "
        f"{len(toezeggingen)}"
    )
    alle_statussen = Counter(
        toezegging.get("Status", "Onbekend")
        for toezegging in toezeggingen
    )

    print("\nSTATUS ALLE OPGEHAALDE TOEZEGGINGEN:")

    for status, aantal in alle_statussen.most_common():
        print(f"{status}: {aantal}")

    print("\nRelevante activiteiten ophalen...")

    activiteiten = get_relevante_activiteiten()

    print(
        f"Totaal relevante activiteiten: "
        f"{len(activiteiten)}"
    )

    print("\nVolgcommissies ophalen...")

    volgcommissie_actoren = (
        get_volgcommissie_actoren()
    )

    print(
        f"Volgcommissie-actoren: "
        f"{len(volgcommissie_actoren)}"
    )

    print("\nCommissies ophalen...")

    commissies = get_commissies()

    print(
        f"Commissies: {len(commissies)}"
    )

    print("\nIenW-selectie maken...")

    ienw = get_ienw_toezeggingen(
        toezeggingen,
        activiteiten,
        volgcommissie_actoren,
        commissies
    )

    print(f"IenW-toezeggingen: {len(ienw)}")
    redenen = Counter(
        toezegging.get("Selectiereden", "Onbekend")
        for toezegging in ienw
    )

    print("\nSELECTIE PER REDEN:")

    for reden, aantal in redenen.most_common():
        print(f"{reden}: {aantal}")
    soorten = Counter(
        toezegging["Activiteit"].get(
            "Soort",
            "Onbekend"
        )
        for toezegging in ienw
    )

    print("\nSELECTIE PER ACTIVITEITSOORT:")

    for soort, aantal in soorten.most_common():
        print(f"{soort}: {aantal}")
    statussen = Counter(
        toezegging.get("Status", "Onbekend")
        for toezegging in ienw
    )

    print("\nSELECTIE PER STATUS:")

    for status, aantal in statussen.most_common():
        print(f"{status}: {aantal}")
    nummers = [
        toezegging.get("Nummer")
        for toezegging in ienw
        if toezegging.get("Nummer")
    ]

    nummer_tellingen = Counter(nummers)

    dubbele_nummers = [
        nummer
        for nummer, aantal in nummer_tellingen.items()
        if aantal > 1
    ]

    print(
        f"\nDubbele toezeggingnummers: "
        f"{len(dubbele_nummers)}"
    )

    if dubbele_nummers:
        for nummer in dubbele_nummers:
            print("Dubbel:", nummer)

    print("\nEERSTE 20 IENW-TOEZEGGINGEN:\n")

    for toezegging in ienw[:20]:
        activiteit = toezegging["Activiteit"]

        print(
            toezegging.get("Nummer"),
            "|",
            toezegging.get("Status"),
            "|",
            activiteit.get("Nummer"),
            "|",
            activiteit.get("Soort"),
            "|",
            activiteit.get("Onderwerp"),
            "|",
            toezegging.get("Selectiereden"),
        )
