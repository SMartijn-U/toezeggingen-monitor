import requests


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v5"


def test_document():
    url = f"{BASE_URL}/Document"

    params = {
        "$top": "5",
        "$filter": "Verwijderd eq false",
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()
    documenten = data.get("value", [])

    print(
        f"Aantal testdocumenten: "
        f"{len(documenten)}"
    )

    if documenten:
        print("\nEERSTE DOCUMENTRECORD:\n")
        print(documenten[0])


if __name__ == "__main__":
    test_document()
