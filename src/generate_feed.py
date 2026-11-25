from datetime import datetime, timezone
from html import escape
from pathlib import Path

from feedgen.feed import FeedGenerator

from get_toezeggingen import (
    get_commissies,
    get_actuele_vaste_commissies,
    maak_commissieslug,
)

from state_store import (
    laad_historie,
    laad_gepubliceerde_resultaten,
)


FEEDS_MAP = Path(
    "public/feeds"
)

MAX_ITEMS = 200

BASIS_URL = (
    "https://SMartijn-U.github.io/"
    "toezeggingen-monitor/feeds"
)


def parse_datum(waarde):
    if not waarde:
        return datetime.now(
            timezone.utc
        )

    return datetime.fromisoformat(
        waarde.replace(
            "Z",
            "+00:00"
        )
    )

def formatteer_activiteitdatum(
    waarde
):
    if not waarde:
        return ""

    try:
        datum = parse_datum(
            waarde
        )

        return datum.strftime(
            "%d-%m-%Y"
        )

    except (
        TypeError,
        ValueError,
    ):
        return str(
            waarde
        )


def maak_activiteit_url(
    activiteitnummer,
    activiteitvoortouw
):
    if not activiteitnummer:
        return None

    voortouw = (
        activiteitvoortouw
        or ""
    ).strip().upper()

    if voortouw == "TK":
        return (
            "https://www.tweedekamer.nl/"
            "debat_en_vergadering/"
            "plenaire_vergaderingen/"
            "details/activiteit"
            f"?id={activiteitnummer}"
        )

    return (
        "https://www.tweedekamer.nl/"
        "debat_en_vergadering/"
        "commissievergaderingen/details"
        f"?id={activiteitnummer}"
    )


def maak_activiteit_html(
    resultaat
):
    activiteitnummer = (
        resultaat.get(
            "activiteitnummer"
        )
        or ""
    ).strip()

    activiteitsoort = (
        resultaat.get(
            "activiteitsoort"
        )
        or ""
    ).strip()

    activiteitonderwerp = (
        resultaat.get(
            "activiteitonderwerp"
        )
        or ""
    ).strip()

    activiteitvoortouw = (
        resultaat.get(
            "activiteitvoortouw"
        )
        or ""
    ).strip()

    activiteitdatum = (
        formatteer_activiteitdatum(
            resultaat.get(
                "activiteitdatum"
            )
        )
    )

    onderdelen = []

    if activiteitsoort:
        weergegeven_soort = (
            activiteitsoort[0].lower()
            + activiteitsoort[1:]
        )

        onderdelen.append(
            weergegeven_soort
        )

    if activiteitonderwerp:
        onderdelen.append(
            activiteitonderwerp
        )

    activiteittekst = " ".join(
        onderdelen
    ).strip()

    if activiteitdatum:
        activiteittekst = (
            f"{activiteittekst} "
            f"({activiteitdatum})"
        ).strip()

    if not activiteittekst:
        return ""

    activiteit_url = (
        maak_activiteit_url(
            activiteitnummer,
            activiteitvoortouw
        )
    )

    if activiteit_url:
        weergegeven_activiteit = (
            f'&lt;a href="'
            f'{escape(activiteit_url)}'
            f'"&gt;'
            f'{escape(activiteittekst)}'
            f'&lt;/a&gt;'
        )
    else:
        weergegeven_activiteit = (
            escape(
                activiteittekst
            )
        )

    return (
        "&lt;p&gt;"
        "&lt;strong&gt;"
        "Activiteit:"
        "&lt;/strong&gt;"
        "&lt;br&gt;"
        f"{weergegeven_activiteit}"
        "&lt;/p&gt;"
    )

def maak_beschrijving(resultaat):
    bewijs = resultaat.get(
        "bewijsfragmenten",
        []
    )

    ontbreekt = resultaat.get(
        "ontbrekende_onderdelen",
        []
    )

    activiteit_html = (
        maak_activiteit_html(
            resultaat
        )
    )

    bewijs_html = "".join(
        (
            f"<blockquote>"
            f"{escape(fragment)}"
            f"</blockquote>"
        )
        for fragment in bewijs[:3]
    )

    ontbreekt_html = ""

    if ontbreekt:
        ontbreekt_html = (
            "<p><strong>"
            "Nog ontbrekend:"
            "</strong></p>"
            "<ul>"
            + "".join(
                (
                    f"<li>"
                    f"{escape(item)}"
                    f"</li>"
                )
                for item in ontbreekt
            )
            + "</ul>"
        )

    return f"""
<p><strong>
Geautomatiseerde signalering van
een mogelijke afdoening.
</strong></p>

<p>
<strong>Commissie:</strong>
{escape(
    resultaat.get(
        "commissie_afkorting",
        ""
    )
)}
<br>
{escape(
    resultaat.get(
        "commissie_naam",
        ""
    )
)}
</p>

<p>
<strong>Toezegging:</strong>
{escape(
    resultaat.get(
        "toezeggingnummer",
        ""
    )
)}
<br>
<strong>Status registratie:</strong>
{escape(
    resultaat.get(
        "status_registratie",
        ""
    )
)}
</p>

{activiteit_html}

<p>
<strong>Herkomst commissieselectie:</strong>
{escape(
    resultaat.get(
        "selectiereden",
        ""
    )
)}
</p>

<p>
<strong>Document:</strong>
{escape(
    resultaat.get(
        "documentnummer",
        ""
    )
)}
<br>
{escape(
    resultaat.get(
        "documentonderwerp",
        ""
    )
)}
<br>
<strong>Datum:</strong>
{escape(
    resultaat.get(
        "documentdatum",
        ""
    )
)}
</p>

<p>
<strong>Oordeel monitor:</strong>
{escape(
    resultaat.get(
        "rapportagecategorie",
        ""
    )
)}
</p>

<p>
<strong>Motivering:</strong><br>
{escape(
    resultaat.get(
        "motivering",
        ""
    )
)}
</p>

{ontbreekt_html}

<p>
<strong>Bewijs uit het document:</strong>
</p>

{bewijs_html}

<p>
Deze signalering is automatisch gegenereerd
op basis van openbare gegevens.
Controle van het document en de volledige
toezegging blijft noodzakelijk.
</p>
"""


def maak_commissiegegevens():
    commissies = get_commissies()

    vaste_commissies = (
        get_actuele_vaste_commissies(
            commissies
        )
    )

    commissiegegevens = []

    for commissie in vaste_commissies:
        slug = maak_commissieslug(
            commissie
        )

        afkorting = (
            commissie.get("Afkorting")
            or slug.upper()
        ).strip()

        naam = (
            commissie.get("NaamNL")
            or commissie.get("NaamWebNL")
            or afkorting
        ).strip()

        if not slug:
            continue

        commissiegegevens.append({
            "commissie_id":
                commissie.get("Id"),

            "commissie_slug":
                slug,

            "commissie_afkorting":
                afkorting,

            "commissie_naam":
                naam,
        })

    return commissiegegevens


def selecteer_resultaten(
    alle_resultaten,
    commissie_slug
):
    resultaten = [
        resultaat
        for resultaat
        in alle_resultaten.values()
        if resultaat.get(
            "commissie_slug"
        ) == commissie_slug
    ]

    resultaten.sort(
        key=lambda item:
            item.get(
                "eerste_signalering",
                ""
            ),
        reverse=True
    )

    return resultaten[:MAX_ITEMS]


def genereer_commissiefeed(
    commissie,
    alle_resultaten
):
    slug = commissie[
        "commissie_slug"
    ]

    afkorting = commissie[
        "commissie_afkorting"
    ]

    naam = commissie[
        "commissie_naam"
    ]

    resultaten = selecteer_resultaten(
        alle_resultaten,
        slug
    )

    feed_url = (
        f"{BASIS_URL}/{slug}.xml"
    )

    feed_path = (
        FEEDS_MAP / f"{slug}.xml"
    )

    fg = FeedGenerator()

    fg.id(
        feed_url
    )

    fg.title(
        "Mogelijke afdoeningen "
        f"toezeggingen {afkorting}"
    )

    fg.description(
        "Geautomatiseerde signaleringen "
        "van mogelijke afdoeningen van "
        "toezeggingen voor "
        f"{naam}."
    )

    fg.link(
        href=feed_url,
        rel="self"
    )

    fg.language(
        "nl"
    )

    for resultaat in resultaten:
        sleutel = resultaat.get(
            "sleutel"
        )

        if not sleutel:
            continue

        item = fg.add_entry()

        delen = sleutel.split("|", 1)

        item_id = "|".join([
            delen[0],
            afkorting,
            delen[1],
        ])

        item.id(
            item_id
        )

        item.title(
            f"{resultaat.get('toezeggingnummer')} "
            f"| "
            f"{resultaat.get('rapportagecategorie')}"
        )

        item.description(
            maak_beschrijving(
                resultaat
            )
        )

        signalering = parse_datum(
            resultaat.get(
                "eerste_signalering"
            )
        )

        item.published(
            signalering
        )

        item.updated(
            signalering
        )

    feed_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fg.rss_file(
        feed_path,
        pretty=True
    )

    print(
        f"{afkorting}-feed aangemaakt met "
        f"{len(resultaten)} items: "
        f"{feed_path}"
    )


def tel_sleutels_met_slug(
    verzameling,
    commissie_slug
):
    voorvoegsel = (
        f"{commissie_slug}|"
    )

    return sum(
        1
        for sleutel
        in verzameling
        if sleutel.startswith(
            voorvoegsel
        )
    )


def genereer_statusfeed(
    commissie,
    historie,
    alle_resultaten
):
    slug = commissie[
        "commissie_slug"
    ]

    afkorting = commissie[
        "commissie_afkorting"
    ]

    verwerkt = historie.get(
        "verwerkt",
        {}
    )

    wachtrij = historie.get(
        "wacht_op_herhaling",
        {}
    )

    aantal_verwerkt = (
        tel_sleutels_met_slug(
            verwerkt,
            slug
        )
    )

    aantal_wachtrij = (
        tel_sleutels_met_slug(
            wachtrij,
            slug
        )
    )

    aantal_resultaten = (
        tel_sleutels_met_slug(
            alle_resultaten,
            slug
        )
    )

    nu = datetime.now(
        timezone.utc
    )

    feed_url = (
        f"{BASIS_URL}/"
        f"{slug}-status.xml"
    )

    feed_path = (
        FEEDS_MAP
        / f"{slug}-status.xml"
    )

    fg = FeedGenerator()

    fg.id(
        feed_url
    )

    fg.title(
        "Technische status "
        f"{afkorting}-toezeggingenmonitor"
    )

    fg.description(
        "Technische uitvoeringsstatus "
        "van de automatische "
        "toezeggingenmonitor voor "
        f"{afkorting}."
    )

    fg.link(
        href=feed_url,
        rel="self"
    )

    fg.language(
        "nl"
    )

    item = fg.add_entry()

    item.id(
        f"status|{slug}|{afkorting}|"
        f"{nu.isoformat()}"
    )

    item.title(
        "Monitorrun voltooid"
    )

    item.published(
        nu
    )

    item.updated(
        nu
    )

    item.description(
        f"""
<p><strong>
Monitorrun voltooid
</strong></p>

<ul>
<li>
Beoordelingseenheden succesvol verwerkt:
{aantal_verwerkt}
</li>
<li>
Beoordelingseenheden in wachtrij:
{aantal_wachtrij}
</li>
<li>
Gepubliceerde signaleringen:
{aantal_resultaten}
</li>
</ul>
"""
    )

    feed_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fg.rss_file(
        feed_path,
        pretty=True
    )

    print(
        f"Statusfeed voor {afkorting} "
        f"aangemaakt: {feed_path}"
    )


def main():
    gepubliceerde_gegevens = (
        laad_gepubliceerde_resultaten()
    )

    alle_resultaten = (
        gepubliceerde_gegevens.get(
            "resultaten",
            {}
        )
    )

    historie = laad_historie()

    commissies = (
        maak_commissiegegevens()
    )

    print(
        f"Actuele vaste commissies voor "
        f"RSS-generatie: "
        f"{len(commissies)}"
    )

    for commissie in commissies:
        genereer_commissiefeed(
            commissie,
            alle_resultaten
        )

        genereer_statusfeed(
            commissie,
            historie,
            alle_resultaten
        )

    print(
        f"\nRSS-generatie voltooid voor "
        f"{len(commissies)} commissies."
    )


if __name__ == "__main__":
    main()
