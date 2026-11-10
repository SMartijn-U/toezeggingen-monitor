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

def get_activiteiten():
    url = f"{BASE_URL}/Activiteit"

    alle_activiteiten = []
    skip = 0
    batch_size = 250

    while True:
        params = {
            "$top": str(batch_size),
            "$skip": str(skip)
        }

        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()
        batch = data.get("value", [])

        alle_activiteiten.extend(batch)

        print(
            f"Pagina activiteiten opgehaald: {len(batch)} "
            f"(totaal: {len(alle_activiteiten)})"
        )

        if len(batch) < batch_size:
            break

        skip += batch_size

    return alle_activiteiten

def get_ienw_toezeggingen(toezeggingen, activiteiten):
    ienw = []
    zonder_activiteit = 0
    activiteit_niet_gevonden = 0

    activiteiten_op_nummer = {
        activiteit.get("Nummer"): activiteit
        for activiteit in activiteiten
        if activiteit.get("Nummer")
    }

    print(
        f"Activiteiten in index: "
        f"{len(activiteiten_op_nummer)}"
    )

    for toezegging in toezeggingen:
        activiteit_nummer = toezegging.get("ActiviteitNummer")

        if not activiteit_nummer:
            zonder_activiteit += 1
            continue

        activiteit = activiteiten_op_nummer.get(
            activiteit_nummer
        )

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
    print(
        f"Activiteit niet gevonden: "
        f"{activiteit_niet_gevonden}"
    )

    return ienw

if __name__ == "__main__":
    print("Openstaande toezeggingen ophalen...")

    toezeggingen = get_open_toezeggingen()

    print(
        f"Alle open/deels voldane toezeggingen: "
        f"{len(toezeggingen)}"
    )

    print("\nActiviteiten ophalen...")

    activiteiten = get_activiteiten()

    print(
        f"Totaal opgehaalde activiteiten: "
        f"{len(activiteiten)}"
    )

    print("\nIenW-selectie maken...")

    ienw = get_ienw_toezeggingen(
        toezeggingen,
        activiteiten
    )

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
