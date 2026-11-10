import requests


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"


def get_open_toezeggingen():
    url = f"{BASE_URL}/Toezegging"

    params = {
        "$filter": (
            "(Status eq 'Openstaand' or Status eq 'Deels Voldaan') "
            "and Verwijderd eq false"
        ),
        "$top": "250"
    }

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    return data.get("value", [])

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

if __name__ == "__main__":
    toezeggingen = get_open_toezeggingen()

    print(f"Aantal opgehaalde toezeggingen: {len(toezeggingen)}")

    if toezeggingen:
        eerste = toezeggingen[0]

        print("\nEERSTE TOEZEGGING:")
        print("Nummer:", eerste.get("Nummer"))
        print("ActiviteitNummer:", eerste.get("ActiviteitNummer"))
        print("Tekst:", eerste.get("Tekst"))

        activiteit_nummer = eerste.get("ActiviteitNummer")

        if activiteit_nummer:
            activiteit = get_activiteit(activiteit_nummer)

            print("\nGEKOPPELDE ACTIVITEIT:")

            if activiteit:
                print("Nummer:", activiteit.get("Nummer"))
                print("Soort:", activiteit.get("Soort"))
                print("Onderwerp:", activiteit.get("Onderwerp"))
                print("Voortouwnaam:", activiteit.get("Voortouwnaam"))
                print("Voortouwafkorting:", activiteit.get("Voortouwafkorting"))
            else:
                print("Geen activiteit gevonden.")
        else:
            print("Deze toezegging heeft geen ActiviteitNummer.")
