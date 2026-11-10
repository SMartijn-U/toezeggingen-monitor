from datetime import datetime, timezone
from pathlib import Path
from feedgen.feed import FeedGenerator


def main():
    output_dir = Path("public/feeds")
    output_dir.mkdir(parents=True, exist_ok=True)

    fg = FeedGenerator()
    fg.id("https://SMartijn-U.github.io/toezeggingen-monitor/feeds/ienw.xml")
    fg.title("Mogelijke afdoeningen toezeggingen IenW")
    fg.link(
        href="https://SMartijn-U.github.io/toezeggingen-monitor/feeds/ienw.xml",
        rel="self",
    )
    fg.description(
        "Geautomatiseerde signalering van mogelijke afdoeningen "
        "van toezeggingen op het terrein van de commissie IenW."
    )
    fg.language("nl")

    item = fg.add_entry()
    item.id("TEST-TZ000000-2026D00000")
    item.title("Testitem: mogelijke afdoening IenW-toezegging")
    item.link(href="https://opendata.tweedekamer.nl/")
    item.published(datetime.now(timezone.utc))
    item.description(
        """
        <p><strong>Dit is een technisch testitem.</strong></p>
        <p>Er heeft nog geen inhoudelijke beoordeling plaatsgevonden.</p>
        """
    )

    fg.rss_file(output_dir / "ienw.xml", pretty=True)

    print("RSS-feed aangemaakt: public/feeds/ienw.xml")


if __name__ == "__main__":
    main()
