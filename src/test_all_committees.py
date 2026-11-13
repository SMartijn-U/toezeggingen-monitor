from collections import Counter

from get_toezeggingen import (
    get_open_toezeggingen,
    get_recent_afgedane_toezeggingen,
    combineer_toezeggingen,
    get_relevante_activiteiten,
    vul_ontbrekende_activiteiten_aan,
    get_volgcommissie_actoren,
    get_commissies,
    get_actuele_vaste_commissies,
    get_toezeggingen_per_commissie,
)


def main():
    print("Toezeggingen ophalen...")

    actuele_toezeggingen = (
        get_open_toezeggingen()
    )

    recent_afgedaan = (
        get_recent_afgedane_toezeggingen(
            aantal_dagen=14
        )
    )

    toezeggingen = combineer_toezeggingen(
        actuele_toezeggingen,
        recent_afgedaan
    )

    print(
        f"Gecombineerde set toezeggingen: "
        f"{len(toezeggingen)}"
    )

    print("\nActiviteiten ophalen...")

    activiteiten = (
        get_relevante_activiteiten()
    )

    (
        activiteiten,
        uitgesloten_activiteitnummers,
    ) = vul_ontbrekende_activiteiten_aan(
        toezeggingen,
        activiteiten
    )

    print("\nVolgcommissies ophalen...")

    volgcommissie_actoren = (
        get_volgcommissie_actoren()
    )

    print("\nCommissies ophalen...")

    commissies = get_commissies()

    actuele_commissies = (
        get_actuele_vaste_commissies(
            commissies
        )
    )

    print(
        f"\nActuele vaste commissies: "
        f"{len(actuele_commissies)}"
    )

    resultaten = {}

    print(
        "\n"
        "========================================"
    )
    print(
        "SELECTIES ALLE VASTE COMMISSIES"
    )
    print(
        "========================================\n"
    )

    for commissie in actuele_commissies:
        slug = commissie["Slug"]

        geselecteerd = (
            get_toezeggingen_per_commissie(
                toezeggingen,
                activiteiten,
                volgcommissie_actoren,
                commissies,
                commissie_afkorting=slug,
                uitgesloten_activiteitnummers=(
                    uitgesloten_activiteitnummers
                ),
            )
        )

        statussen = Counter(
            toezegging.get(
                "Status",
                "Onbekend"
            )
            for toezegging in geselecteerd
        )

        redenen = Counter(
            toezegging.get(
                "Selectiereden",
                "Onbekend"
            )
            for toezegging in geselecteerd
        )

        resultaten[slug] = {
            "totaal": len(geselecteerd),
            "statussen": dict(statussen),
            "redenen": dict(redenen),
        }

        print(
            "SAMENVATTING |",
            slug,
            "|",
            commissie["Afkorting"],
            "|",
            commissie["NaamNL"],
            "| totaal:",
            len(geselecteerd),
            "| statussen:",
            dict(statussen),
            "| redenen:",
            dict(redenen),
        )

    print(
        "\nCOMMISSIES GETEST:",
        len(resultaten)
    )


if __name__ == "__main__":
    main()
