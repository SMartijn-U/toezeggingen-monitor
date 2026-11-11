import random
import time

import requests


def get_met_retries(
    url,
    params=None,
    timeout=60,
    max_pogingen=5
):
    laatste_fout = None

    for poging in range(1, max_pogingen + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=timeout
            )

            if response.status_code < 500:
                response.raise_for_status()
                return response

            laatste_fout = (
                f"HTTP {response.status_code}"
            )

            print(
                f"Tijdelijke OData-serverfout "
                f"{response.status_code}. "
                f"Poging {poging} van "
                f"{max_pogingen}."
            )

        except (
            requests.ConnectionError,
            requests.Timeout
        ) as fout:
            laatste_fout = str(fout)

            print(
                f"Tijdelijke OData-netwerkfout. "
                f"Poging {poging} van "
                f"{max_pogingen}: {fout}"
            )

        if poging < max_pogingen:
            wachttijd = (
                2 ** poging
                + random.uniform(0, 1)
            )

            print(
                f"{wachttijd:.1f} seconden wachten..."
            )

            time.sleep(wachttijd)

    raise RuntimeError(
        f"OData-verzoek mislukt na "
        f"{max_pogingen} pogingen. "
        f"Laatste fout: {laatste_fout}. "
        f"URL: {url}"
    )
