import requests


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"


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

def get_activiteit(activiteit_nummer):
    url = f"{BASE_URL}/Activiteit"

    params = {
        "$filter": f"Nummer eq '{activiteit_nummer}'",
        "$top": "1"
    }

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    resultaten = data.get("value", [])

    if not resultaten:
        return None

    return resultaten[0]

def get_ienw_toezeggingen(toezeggingen):
    ienw = []
    zonder_activiteit = 0
    activiteit_niet_gevonden = 0

    for toezegging in toezeggingen:
        activiteit_nummer = toezegging.get("ActiviteitNummer")

        if not activiteit_nummer:
            zonder_activiteit += 1
            continue

        activiteit = get_activiteit(activiteit_nummer)

        if not activiteit:
            activiteit_niet_gevonden += 1
            continue

        voortouw = activiteit.get("Voortouwnaam", "")

        if (
            voortouw
            and voortouw.strip().lower()
            == "vaste commissie voor infrastructuur en waterstaat"
        ):
            toezegging["Activiteit"] = activiteit
            ienw.append(toezegging)

    print(f"Zonder ActiviteitNummer: {zonder_activiteit}")
    print(f"Activiteit niet gevonden: {activiteit_niet_gevonden}")

    return ienw

if __name__ == "__main__":
    toezeggingen = get_open_toezeggingen()

    print(
        f"Alle open/deels voldane toezeggingen: "
        f"{len(toezeggingen)}"
    )

    ienw = get_ienw_toezeggingen(toezeggingen)

    print(f"IenW-toezeggingen: {len(ienw)}")

    print("\nEERSTE 10 IENW-TOEZEGGINGEN:\n")

    for toezegging in ienw[:10]:
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
            activiteit.get("Voortouwnaam"),
        )
