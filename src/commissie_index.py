from collections import Counter

from get_toezeggingen import (
    get_actuele_vaste_commissies,
    get_toezeggingen_per_commissie,
    maak_commissie_slug,
)


def bouw_commissie_index(
    toezeggingen,
    activiteiten,
    volgcommissie_actoren,
    commissies,
    uitgesloten_activiteitnummers=None,
):
    uitgesloten_activiteitnummers = (
        uitgesloten_activiteitnummers
        or set()
    )

    actuele_commissies = (
        get_actuele_vaste_commissies(
            commissies
        )
    )

    toezeggingen_op_nummer = {}
    selecties_per_commissie = {}

    for commissie in actuele_commissies:
        afkorting = (
            commissie.get("Afkorting")
            or ""
        ).strip()

        naam = (
            commissie.get("NaamNL")
            or ""
        ).strip()

        slug = maak_commissie_slug(
            afkorting
        )

        if not slug:
            print(
                "WAARSCHUWING: commissie zonder "
                "bruikbare technische slug:",
                afkorting,
                "|",
                naam,
            )
            continue

        geselecteerde_toezeggingen = (
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

        selecties_per_commissie[slug] = {
            "commissie_id":
                commissie.get("Id"),

            "slug":
                slug,

            "afkorting":
                afkorting,

            "naam":
                naam,

            "aantal_toezeggingen":
                len(
                    geselecteerde_toezeggingen
                ),
        }

        for toezegging in (
            geselecteerde_toezeggingen
        ):
            toezeggingnummer = (
                toezegging.get("Nummer")
            )

            if not toezeggingnummer:
                continue

            if (
                toezeggingnummer
                not in toezeggingen_op_nummer
            ):
                basis_record = dict(
                    toezegging
                )

                # Deze velden gelden voor één
                # specifieke commissieselectie
                # en worden daarom niet op het
                # hoofdniveau bewaard.
                basis_record.pop(
                    "CommissieAfkorting",
                    None
                )

                basis_record.pop(
                    "CommissieSlug",
                    None
                )

                basis_record.pop(
                    "Selectiereden",
                    None
                )

                basis_record[
                    "Commissies"
                ] = []

                toezeggingen_op_nummer[
                    toezeggingnummer
                ] = basis_record

            commissie_record = {
                "commissie_id":
                    commissie.get("Id"),

                "slug":
                    slug,

                "afkorting":
                    afkorting,

                "naam":
                    naam,

                "selectiereden":
                    toezegging.get(
                        "Selectiereden"
                    ),
            }

            bestaande_slugs = {
                item.get("slug")
                for item in (
                    toezeggingen_op_nummer[
                        toezeggingnummer
                    ]["Commissies"]
                )
            }

            if slug not in bestaande_slugs:
                toezeggingen_op_nummer[
                    toezeggingnummer
                ]["Commissies"].append(
                    commissie_record
                )

    unieke_toezeggingen = list(
        toezeggingen_op_nummer.values()
    )

    unieke_toezeggingen.sort(
        key=lambda toezegging: (
            toezegging.get("Nummer")
            or ""
        )
    )

    for toezegging in unieke_toezeggingen:
        toezegging["Commissies"].sort(
            key=lambda commissie: (
                commissie.get("slug")
                or ""
            )
        )

        toezegging[
            "CommissieSlugs"
        ] = [
            commissie.get("slug")
            for commissie
            in toezegging["Commissies"]
            if commissie.get("slug")
        ]

    aantal_commissies_per_toezegging = (
        Counter(
            len(
                toezegging.get(
                    "Commissies",
                    []
                )
            )
            for toezegging
            in unieke_toezeggingen
        )
    )

    totaal_commissieselecties = sum(
        item["aantal_toezeggingen"]
        for item
        in selecties_per_commissie.values()
    )

    meerdere_commissies = sum(
        1
        for toezegging
        in unieke_toezeggingen
        if len(
            toezegging.get(
                "Commissies",
                []
            )
        ) > 1
    )

    samenvatting = {
        "aantal_actuele_commissies":
            len(actuele_commissies),

        "totaal_commissieselecties":
            totaal_commissieselecties,

        "unieke_toezeggingen":
            len(unieke_toezeggingen),

        "toezeggingen_bij_meerdere_commissies":
            meerdere_commissies,

        "verdeling_aantal_commissies":
            dict(
                sorted(
                    aantal_commissies_per_toezegging
                    .items()
                )
            ),
    }

    return {
        "samenvatting":
            samenvatting,

        "commissies":
            selecties_per_commissie,

        "toezeggingen":
            unieke_toezeggingen,
    }
