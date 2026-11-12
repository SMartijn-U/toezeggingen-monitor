import requests
import time

import re

from datetime import datetime, timedelta, timezone
from collections import Counter


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v5"

RELEVANTE_ACTIVITEITSOORTEN = {
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
}

def get_met_retries(
    url,
    params=None,
    timeout=60,
    max_pogingen=5
):
    for poging in range(
        1,
        max_pogingen + 1
    ):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=timeout
            )

            if response.status_code < 500:
                response.raise_for_status()
                return response

            print(
                f"Tijdelijke serverfout "
                f"{response.status_code}. "
                f"Poging {poging} van "
                f"{max_pogingen}."
            )

        except (
            requests.ConnectionError,
            requests.Timeout
        ) as fout:
            print(
                f"Tijdelijke netwerkfout: "
                f"{fout}. "
                f"Poging {poging} van "
                f"{max_pogingen}."
            )

        if poging < max_pogingen:
            wachttijd = 2 ** poging

            print(
                f"{wachttijd} seconden wachten "
                f"voor nieuwe poging..."
            )

            time.sleep(wachttijd)

    raise RuntimeError(
        f"OData-verzoek mislukt na "
        f"{max_pogingen} pogingen: {url}"
    )

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

        response = get_met_retries(
            url,
            params=params,
            timeout=60
        )

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
            "Rol eq 'Volgcommissie' "
            "and Verwijderd eq false"
        )
    )

def get_commissies():
    return get_odata_paginated(
        entity="Commissie",
        odata_filter="Verwijderd eq false"
    )

def maak_commissieslug(commissie):
    afkorting = (
        commissie.get("Afkorting")
        or commissie.get("Id")
        or ""
    )

    slug = afkorting.lower()

    slug = slug.replace(
        "&",
        "en"
    )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        slug
    )

    return slug.strip("-")

def get_actuele_vaste_commissies(
    commissies
):
    vandaag = datetime.now(
        timezone.utc
    ).date()

    actuele_commissies = []

    for commissie in commissies:
        # In OData v5 heet het voormalige
        # veld Inhoudsopgave nu Soort.
        soort = (
            commissie.get("Soort")
            or ""
        ).strip()

        if soort != "Vaste commissies":
            continue

        if commissie.get("Verwijderd") is True:
            continue

        datum_actief = commissie.get(
            "DatumActief"
        )

        datum_inactief = commissie.get(
            "DatumInactief"
        )

        # Een toekomstige commissie is nog
        # niet actief.
        if (
            datum_actief
            and not datum_actief.startswith(
                "0001-01-01"
            )
        ):
            try:
                actief_vanaf = (
                    datetime.fromisoformat(
                        datum_actief.replace(
                            "Z",
                            "+00:00"
                        )
                    ).date()
                )

                if actief_vanaf > vandaag:
                    continue

            except ValueError:
                print(
                    "WAARSCHUWING: ongeldige "
                    "DatumActief:",
                    commissie.get("Afkorting"),
                    datum_actief
                )

        # Geen DatumInactief of een nuldatum
        # betekent dat de commissie nog actief is.
        is_inactief = False

        if (
            datum_inactief
            and not datum_inactief.startswith(
                "0001-01-01"
            )
        ):
            try:
                inactief_vanaf = (
                    datetime.fromisoformat(
                        datum_inactief.replace(
                            "Z",
                            "+00:00"
                        )
                    ).date()
                )

                if inactief_vanaf <= vandaag:
                    is_inactief = True

            except ValueError:
                print(
                    "WAARSCHUWING: ongeldige "
                    "DatumInactief:",
                    commissie.get("Afkorting"),
                    datum_inactief
                )

        if is_inactief:
            continue

        actuele_commissies.append(
            commissie
        )

    actuele_commissies.sort(
        key=lambda commissie: (
            commissie.get("NaamNL")
            or commissie.get("NaamWebNL")
            or commissie.get("Afkorting")
            or ""
        )
    )

    return actuele_commissies

def maak_commissie_index(
    vaste_commissies
):
    index = {}

    for commissie in vaste_commissies:
        commissie_id = commissie.get(
            "Id"
        )

        if not commissie_id:
            continue

        index[commissie_id] = {
            "id": commissie_id,
            "afkorting": commissie.get(
                "Afkorting"
            ),
            "naam": (
                commissie.get("NaamNL")
                or commissie.get("NaamWebNL")
                or ""
            ).strip(),
            "slug": maak_commissieslug(
                commissie
            ),
        }

    return index

def get_open_toezeggingen():
    url = f"{BASE_URL}/Toezegging"

    alle_toezeggingen = []
    skip = 0
    batch_size = 250

    while True:
        params = {
            "$filter": (
                "(Status eq 'Openstaand' or Status eq 'Deels Afgedaan') "
                "and Verwijderd eq false"
            ),
            "$top": str(batch_size),
            "$skip": str(skip)
        }

        response = get_met_retries(
            url,
            params=params,
            timeout=60
        )

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

def get_recent_afgedane_toezeggingen(
    aantal_dagen=14
):
    url = f"{BASE_URL}/Toezegging"

    nu = datetime.now(timezone.utc)
    vanaf = nu - timedelta(days=aantal_dagen)

    vanaf_datum = vanaf.strftime(
        "%Y-%m-%dT00:00:00Z"
    )

    alle_toezeggingen = []
    skip = 0
    batch_size = 250

    print(
        f"Recent afgedane toezeggingen "
        f"ophalen vanaf: {vanaf_datum}"
    )

    while True:
        params = {
            "$filter": (
                "Status eq 'Afgedaan' "
                f"and GewijzigdOp ge {vanaf_datum} "
                "and Verwijderd eq false"
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

        alle_toezeggingen.extend(batch)

        print(
            f"Recent afgedaan opgehaald: "
            f"{len(batch)} "
            f"(totaal: {len(alle_toezeggingen)})"
        )

        if len(batch) < batch_size:
            break

        skip += batch_size

    return alle_toezeggingen

def combineer_toezeggingen(
    actuele_toezeggingen,
    recent_afgedane_toezeggingen
):
    per_nummer = {}

    for toezegging in (
        actuele_toezeggingen
        + recent_afgedane_toezeggingen
    ):
        nummer = toezegging.get("Nummer")

        if nummer:
            per_nummer[nummer] = toezegging

    return list(per_nummer.values())

def get_relevante_activiteiten():
    url = f"{BASE_URL}/Activiteit"

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
        for soort in RELEVANTE_ACTIVITEITSOORTEN
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

        response = get_met_retries(
            url,
            params=params,
            timeout=60
        )

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

def get_activiteit_op_nummer(activiteit_nummer):
    url = f"{BASE_URL}/Activiteit"

    params = {
        "$filter": (
            f"Nummer eq '{activiteit_nummer}' "
            "and Verwijderd eq false"
        ),
        "$top": "1",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()
        resultaten = data.get("value", [])

        if not resultaten:
            return None

        return resultaten[0]

    except requests.RequestException as fout:
        print(
            f"FOUT bij ophalen activiteit "
            f"{activiteit_nummer}: {fout}"
        )

        return None

def bepaal_ontbrekende_activiteitnummers(
    toezeggingen,
    activiteiten
):
    bekende_nummers = {
        activiteit.get("Nummer")
        for activiteit in activiteiten
        if activiteit.get("Nummer")
    }

    ontbrekende_nummers = {
        toezegging.get("ActiviteitNummer")
        for toezegging in toezeggingen
        if (
            toezegging.get("ActiviteitNummer")
            and toezegging.get("ActiviteitNummer")
            not in bekende_nummers
        )
    }

    return sorted(ontbrekende_nummers)

def vul_ontbrekende_activiteiten_aan(
    toezeggingen,
    activiteiten
):
    ontbrekende_nummers = (
        bepaal_ontbrekende_activiteitnummers(
            toezeggingen,
            activiteiten
        )
    )

    print(
        f"\nOntbrekende unieke activiteitnummers "
        f"voor fallback: {len(ontbrekende_nummers)}"
    )

    aanvullende_activiteiten = []
    uitgesloten_soorten = Counter()
    werkelijk_niet_gevonden = []

    for activiteit_nummer in ontbrekende_nummers:
        activiteit = get_activiteit_op_nummer(
            activiteit_nummer
        )

        if not activiteit:
            werkelijk_niet_gevonden.append(
                activiteit_nummer
            )
            continue

        soort = activiteit.get("Soort", "Onbekend")

        if soort not in RELEVANTE_ACTIVITEITSOORTEN:
            uitgesloten_soorten[soort] += 1

            print(
                f"Fallback uitgesloten: "
                f"{activiteit_nummer} | {soort}"
            )

            continue

        aanvullende_activiteiten.append(
            activiteit
        )

        print(
            f"Fallback toegevoegd: "
            f"{activiteit_nummer} | "
            f"{soort} | "
            f"{activiteit.get('Onderwerp')}"
        )

    bestaande_ids = {
        activiteit.get("Id")
        for activiteit in activiteiten
        if activiteit.get("Id")
    }

    for activiteit in aanvullende_activiteiten:
        if activiteit.get("Id") not in bestaande_ids:
            activiteiten.append(activiteit)

    print(
        f"\nRelevante activiteiten toegevoegd "
        f"via fallback: "
        f"{len(aanvullende_activiteiten)}"
    )

    print("\nUITGESLOTEN FALLBACK-ACTIVITEITEN:")

    if uitgesloten_soorten:
        for soort, aantal in (
            uitgesloten_soorten.most_common()
        ):
            print(f"{soort}: {aantal}")
    else:
        print("Geen.")

    print("\nWERKELIJK NIET GEVONDEN ACTIVITEITEN:")

    if werkelijk_niet_gevonden:
        for activiteit_nummer in (
            werkelijk_niet_gevonden
        ):
            print(activiteit_nummer)
    else:
        print("Geen.")

    return activiteiten

def get_toezeggingen_per_commissie(
    toezeggingen,
    activiteiten,
    volgcommissie_actoren,
    commissies,
    commissie_afkorting
):
    geselecteerd = []

    zonder_activiteit = 0
    activiteit_niet_gevonden = 0
    plenair_zonder_volgcommissie = 0
    niet_gevonden_records = []

    gezochte_afkorting = (
        commissie_afkorting
        or ""
    ).strip().lower()

    if not gezochte_afkorting:
        raise ValueError(
            "commissie_afkorting mag niet leeg zijn."
        )

    # Zoek de commissiegegevens die horen bij
    # de opgegeven afkorting.
    doelcommissies = [
        commissie
        for commissie in commissies
        if (
            commissie.get("Afkorting")
            or ""
        ).strip().lower()
        == gezochte_afkorting
    ]

    if not doelcommissies:
        beschikbare_afkortingen = sorted({
            (
                commissie.get("Afkorting")
                or ""
            ).strip()
            for commissie in commissies
            if commissie.get("Afkorting")
        })

        raise ValueError(
            f"Commissie met afkorting "
            f"'{commissie_afkorting}' "
            f"niet gevonden. "
            f"Beschikbaar: "
            f"{', '.join(beschikbare_afkortingen)}"
        )

    # Mogelijke representaties van de commissie.
    # Bijvoorbeeld:
    # - ienw
    # - vaste commissie voor infrastructuur
    #   en waterstaat
    doelcommissie_identifiers = set()

    for commissie in doelcommissies:
        afkorting = (
            commissie.get("Afkorting")
            or ""
        ).strip().lower()

        naam_nl = (
            commissie.get("NaamNL")
            or ""
        ).strip().lower()

        if afkorting:
            doelcommissie_identifiers.add(
                afkorting
            )

        if naam_nl:
            doelcommissie_identifiers.add(
                naam_nl
            )

    # Gebruik één nette afkorting voor logging
    # en opgeslagen selectieredenen.
    nette_afkorting = (
        doelcommissies[0].get(
            "Afkorting"
        )
        or commissie_afkorting
    ).strip()

    activiteiten_op_nummer = {
        activiteit.get("Nummer"):
            activiteit
        for activiteit in activiteiten
        if activiteit.get("Nummer")
    }

    commissies_op_id = {
        commissie.get("Id"):
            commissie
        for commissie in commissies
        if commissie.get("Id")
    }

    # Maak per activiteit een verzameling
    # van volgcommissies.
    volgcommissies_per_activiteit = {}

    relevante_activiteit_ids = {
        activiteit.get("Id")
        for activiteit in activiteiten
        if activiteit.get("Id")
    }

    for actor in volgcommissie_actoren:
        activiteit_id = actor.get(
            "Activiteit_Id"
        )

        commissie_id = actor.get(
            "Commissie_Id"
        )

        if (
            activiteit_id
            not in relevante_activiteit_ids
        ):
            continue

        commissie = commissies_op_id.get(
            commissie_id
        )

        if not commissie:
            continue

        actor_afkorting = (
            commissie.get("Afkorting")
            or ""
        ).strip().lower()

        actor_naam = (
            commissie.get("NaamNL")
            or ""
        ).strip().lower()

        activiteit_commissies = (
            volgcommissies_per_activiteit
            .setdefault(
                activiteit_id,
                set()
            )
        )

        if actor_afkorting:
            activiteit_commissies.add(
                actor_afkorting
            )

        if actor_naam:
            activiteit_commissies.add(
                actor_naam
            )

    for toezegging in toezeggingen:
        activiteit_nummer = (
            toezegging.get(
                "ActiviteitNummer"
            )
        )

        if not activiteit_nummer:
            zonder_activiteit += 1
            continue

        activiteit = (
            activiteiten_op_nummer.get(
                activiteit_nummer
            )
        )

        if not activiteit:
            activiteit_niet_gevonden += 1

            niet_gevonden_records.append({
                "Nummer":
                    toezegging.get("Nummer"),

                "Status":
                    toezegging.get("Status"),

                "ActiviteitNummer":
                    activiteit_nummer,

                "Tekst":
                    toezegging.get("Tekst"),
            })

            continue

        soort = activiteit.get(
            "Soort",
            ""
        )

        voortouw = (
            activiteit.get(
                "VoortouwCommissieNaam"
            )
            or ""
        ).strip().lower()

        is_geselecteerd = False
        selectiereden = None

        # Route 1: commissieactiviteiten.
        if soort in {
            "Commissiedebat",
            "Notaoverleg",
            "Wetgevingsoverleg",
        }:
            if (
                voortouw
                in doelcommissie_identifiers
            ):
                is_geselecteerd = True

                selectiereden = (
                    f"{nette_afkorting} "
                    f"is voortouwcommissie"
                )

        # Route 2: plenaire debatten.
        elif soort.startswith(
            "Plenair debat"
        ):
            activiteit_id = activiteit.get(
                "Id"
            )

            volgcommissies = (
                volgcommissies_per_activiteit
                .get(
                    activiteit_id,
                    set()
                )
            )

            if (
                doelcommissie_identifiers
                & volgcommissies
            ):
                is_geselecteerd = True

                selectiereden = (
                    f"{nette_afkorting} "
                    f"is volgcommissie"
                )

            else:
                plenair_zonder_volgcommissie += 1

        if is_geselecteerd:
            # Maak een kopie. Daardoor kan dezelfde
            # toezegging later veilig voor meerdere
            # commissies worden geselecteerd zonder
            # dat velden elkaar overschrijven.
            geselecteerde_toezegging = dict(
                toezegging
            )

            geselecteerde_toezegging[
                "Activiteit"
            ] = activiteit

            geselecteerde_toezegging[
                "Selectiereden"
            ] = selectiereden

            geselecteerde_toezegging[
                "CommissieAfkorting"
            ] = nette_afkorting

            geselecteerd.append(
                geselecteerde_toezegging
            )

    print(
        f"\nSELECTIE COMMISSIE: "
        f"{nette_afkorting}"
    )

    print(
        f"Commissie-identifiers: "
        f"{sorted(doelcommissie_identifiers)}"
    )

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
        f"Plenaire activiteiten zonder "
        f"{nette_afkorting} als volgcommissie: "
        f"{plenair_zonder_volgcommissie}"
    )

    print(
        f"Geselecteerde toezeggingen "
        f"voor {nette_afkorting}: "
        f"{len(geselecteerd)}"
    )

    print("\nNIET-GEVONDEN ACTIVITEITEN:")

    if niet_gevonden_records:
        for record in niet_gevonden_records:
            print(
                record.get("Nummer"),
                "|",
                record.get("Status"),
                "|",
                record.get(
                    "ActiviteitNummer"
                ),
                "|",
                record.get("Tekst"),
            )
    else:
        print("Geen.")

    return geselecteerd

def get_ienw_toezeggingen(
    toezeggingen,
    activiteiten,
    volgcommissie_actoren,
    commissies
):
    return get_toezeggingen_per_commissie(
        toezeggingen,
        activiteiten,
        volgcommissie_actoren,
        commissies,
        commissie_afkorting="IenW",
    )
        
if __name__ == "__main__":
    print("Openstaande en deels afgedane toezeggingen ophalen...")

    toezeggingen = get_open_toezeggingen()

    print(
        f"Alle open/deels afgedane toezeggingen: "
        f"{len(toezeggingen)}"
    )

    alle_statussen = Counter(
        toezegging.get("Status", "Onbekend")
        for toezegging in toezeggingen
    )

    print("\nSTATUS ALLE OPGEHAALDE TOEZEGGINGEN:")

    for status, aantal in alle_statussen.most_common():
        print(f"{status}: {aantal}")

    print("\nRecent afgedane toezeggingen ophalen...")

    recent_afgedaan = get_recent_afgedane_toezeggingen(
        aantal_dagen=14
    )

    print(
        f"Recent afgedane toezeggingen: "
        f"{len(recent_afgedaan)}"
    )

    toezeggingen = combineer_toezeggingen(
        toezeggingen,
        recent_afgedaan
    )

    print(
        f"Totaal te onderzoeken toezeggingen: "
        f"{len(toezeggingen)}"
    )

    print("\nRelevante activiteiten ophalen...")

    activiteiten = get_relevante_activiteiten()

    print(
        f"Totaal relevante activiteiten: "
        f"{len(activiteiten)}"
    )

    print(
        "\nOntbrekende activiteiten gericht ophalen..."
    )

    activiteiten = (
        vul_ontbrekende_activiteiten_aan(
            toezeggingen,
            activiteiten
        )
    )

    print(
        f"Totaal relevante activiteiten "
        f"na fallback: {len(activiteiten)}"
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

    print(
        "\nACTUELE VASTE COMMISSIES:\n"
    )

    vaste_commissies = (
        get_actuele_vaste_commissies(
            commissies
        )
    )

    for commissie in vaste_commissies:
        print(
            commissie.get("Id"),
            "|",
            commissie.get("Afkorting"),
            "| slug:",
            maak_commissieslug(
                commissie
            ),
            "|",
            (
                commissie.get("NaamNL")
                or commissie.get("NaamWebNL")
            ),
            "| actief vanaf:",
            commissie.get("DatumActief"),
            "| inactief:",
            commissie.get("DatumInactief"),
        )

    commissie_index = (
        maak_commissie_index(
            vaste_commissies
        )
    )

    print(
        f"\nActuele commissie-ID's "
        f"in index: "
        f"{len(commissie_index)}"
    )

    print(
        "\nCONTROLE COMMISSIE-INDEX:\n"
    )

    for commissie_id, gegevens in (
        commissie_index.items()
    ):
        print(
            commissie_id,
            "|",
            gegevens["afkorting"],
            "|",
            gegevens["slug"],
            "|",
            gegevens["naam"],
        )
    
    print(
        f"\nAantal actuele vaste commissies: "
        f"{len(vaste_commissies)}"
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
