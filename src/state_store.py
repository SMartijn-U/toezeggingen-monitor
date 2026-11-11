import json
import os
from pathlib import Path


HISTORY_PATH = Path(
    "data/assessment_history.json"
)

PUBLISHED_PATH = Path(
    "data/published_results.json"
)


def laad_json(path, standaard):
    if not path.exists():
        return standaard

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        json.JSONDecodeError,
        OSError
    ) as fout:
        print(
            f"WAARSCHUWING: {path} kon "
            f"niet worden gelezen: {fout}"
        )

        return standaard


def schrijf_json_atomair(
    path,
    gegevens
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    tijdelijk_pad = path.with_suffix(
        path.suffix + ".tmp"
    )

    tijdelijk_pad.write_text(
        json.dumps(
            gegevens,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    os.replace(
        tijdelijk_pad,
        path
    )


def laad_historie():
    gegevens = laad_json(
        HISTORY_PATH,
        {
            "verwerkt": {},
            "wacht_op_herhaling": {},
        }
    )

    gegevens.setdefault(
        "verwerkt",
        {}
    )

    gegevens.setdefault(
        "wacht_op_herhaling",
        {}
    )

    return gegevens


def schrijf_historie(historie):
    schrijf_json_atomair(
        HISTORY_PATH,
        historie
    )


def laad_gepubliceerde_resultaten():
    gegevens = laad_json(
        PUBLISHED_PATH,
        {
            "resultaten": {}
        }
    )

    gegevens.setdefault(
        "resultaten",
        {}
    )

    return gegevens


def schrijf_gepubliceerde_resultaten(
    gegevens
):
    schrijf_json_atomair(
        PUBLISHED_PATH,
        gegevens
    )
