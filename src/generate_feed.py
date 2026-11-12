import json
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

from feedgen.feed import FeedGenerator


RESULTS_PATH = Path(
    "data/published_results.json"
)

HISTORY_PATH = Path(
    "data/assessment_history.json"
)

FEED_PATH = Path(
    "public/feeds/ienw.xml"
)

STATUS_FEED_PATH = Path(
    "public/feeds/ienw-status.xml"
)

MAX_ITEMS = 200


def laad_json(path, standaard):
    if not path.exists():
        return standaard

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
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


def maak_beschrijving(resultaat):
    bewijs = resultaat.get(
        "bewijsfragmenten",
        []
    )

    ontbreekt = resultaat.get(
        "ontbrekende_onderdelen",
        []
    )

    bewijs_html = "".join(
        f"<blockquote>{escape(fragment)}</blockquote>"
        for fragment in bewijs[:3]
    )

    ontbreekt_html = ""

    if ontbreekt:
        ontbreekt_html = (
            "<p><strong>Nog ontbrekend:</strong></p>"
            "<ul>"
            + "".join(
                f"<li>{escape(item)}</li>"
                for item in ontbreekt
            )
            + "</ul>"
        )

    return f"""
<p><strong>Geautomatiseerde signalering
van een mogelijke afdoening.</strong></p>

<p>
<strong>Toezegging:</strong>
{escape(resultaat.get("toezeggingnummer", ""))}
<br>
<strong>Status registratie:</strong>
{escape(resultaat.get("status_registratie", ""))}
</p>

<p>
<strong>Document:</strong>
{escape(resultaat.get("documentnummer", ""))}
<br>
{escape(resultaat.get("documentonderwerp", ""))}
<br>
<strong>Datum:</strong>
{escape(resultaat.get("documentdatum", ""))}
</p>

<p>
<strong>Oordeel monitor:</strong>
{escape(resultaat.get("rapportagecategorie", ""))}
</p>

<p>
<strong>Motivering:</strong><br>
{escape(resultaat.get("motivering", ""))}
</p>

{ontbreekt_html}

<p><strong>Bewijs uit het document:</strong></p>
{bewijs_html}

<p>
Deze signalering is automatisch gegenereerd
op basis van openbare gegevens.
Controle van het document en de volledige
toezegging blijft noodzakelijk.
</p>
"""


def genereer_ienw_feed():
    gegevens = laad_json(
        RESULTS_PATH,
        {
            "resultaten": {}
        }
    )

    resultaten = list(
        gegevens.get(
            "resultaten",
            {}
        ).values()
    )

    resultaten.sort(
        key=lambda item:
            item.get(
                "eerste_signalering",
                ""
            ),
        reverse=True
    )

    resultaten = resultaten[
        :MAX_ITEMS
    ]

    fg = FeedGenerator()

    feed_url = (
        "https://SMartijn-U.github.io/"
        "toezeggingen-monitor/feeds/ienw.xml"
    )

    fg.id(feed_url)

    fg.title(
        "Mogelijke afdoeningen "
        "toezeggingen IenW"
    )

    fg.description(
        "Geautomatiseerde signaleringen van "
        "mogelijke afdoeningen van toezeggingen "
        "op het terrein van de commissie "
        "Infrastructuur en Waterstaat."
    )

    fg.link(
        href=feed_url,
        rel="self"
    )

    fg.language("nl")

    for resultaat in resultaten:
        sleutel = resultaat.get(
            "sleutel"
        )

        fe = fg.add_entry()

        fe.id(
            sleutel
        )

        fe.title(
            f"{resultaat.get('toezeggingnummer')} | "
            f"{resultaat.get('rapportagecategorie')}"
        )

        fe.description(
            maak_beschrijving(
                resultaat
            )
        )

        signalering = parse_datum(
            resultaat.get(
                "eerste_signalering"
            )
        )

        fe.published(
            signalering
        )

        fe.updated(
            signalering
        )

    FEED_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fg.rss_file(
        FEED_PATH,
        pretty=True
    )

    print(
        f"IenW-feed aangemaakt met "
        f"{len(resultaten)} items."
    )


def genereer_statusfeed():
    historie = laad_json(
        HISTORY_PATH,
        {
            "verwerkt": {},
            "wacht_op_herhaling": {},
        }
    )

    gepubliceerd = laad_json(
        RESULTS_PATH,
        {
            "resultaten": {}
        }
    )

    aantal_verwerkt = len(
        historie.get(
            "verwerkt",
            {}
        )
    )

    aantal_wachtrij = len(
        historie.get(
            "wacht_op_herhaling",
            {}
        )
    )

    aantal_resultaten = len(
        gepubliceerd.get(
            "resultaten",
            {}
        )
    )

    nu = datetime.now(
        timezone.utc
    )

    fg = FeedGenerator()

    feed_url = (
        "https://SMartijn-U.github.io/"
        "toezeggingen-monitor/feeds/"
        "ienw-status.xml"
    )

    fg.id(feed_url)

    fg.title(
        "Technische status "
        "IenW-toezeggingenmonitor"
    )

    fg.description(
        "Technische uitvoeringsstatus van "
        "de automatische toezeggingenmonitor."
    )

    fg.link(
        href=feed_url,
        rel="self"
    )

    fg.language("nl")

    item = fg.add_entry()

    item.id(
        f"status-{nu.isoformat()}"
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
<p><strong>Monitorrun voltooid</strong></p>
<ul>
<li>Documenten succesvol verwerkt:
{aantal_verwerkt}</li>
<li>Documenten in wachtrij:
{aantal_wachtrij}</li>
<li>Gepubliceerde signaleringen:
{aantal_resultaten}</li>
</ul>
"""
    )

    STATUS_FEED_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fg.rss_file(
        STATUS_FEED_PATH,
        pretty=True
    )

    print(
        "Statusfeed aangemaakt."
    )


if __name__ == "__main__":
    genereer_ienw_feed()
    genereer_statusfeed()
