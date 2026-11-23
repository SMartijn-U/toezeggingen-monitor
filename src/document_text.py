import io
import requests
import zipfile

from xml.etree import ElementTree

from docx import Document
from pypdf import PdfReader


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v5"


def download_document(document_id):
    url = (
        f"{BASE_URL}/Document"
        f"({document_id})/resource"
    )

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    return (
        response.content,
        response.headers.get(
            "Content-Type",
            ""
        )
    )

def extract_docx_footnotes(content):
    teksten = []

    try:
        with zipfile.ZipFile(
            io.BytesIO(content)
        ) as zip_bestand:
            pad = "word/footnotes.xml"

            if pad not in zip_bestand.namelist():
                return []

            xml_data = zip_bestand.read(
                pad
            )

        root = ElementTree.fromstring(
            xml_data
        )

        namespace = {
            "w": (
                "http://schemas.openxmlformats.org/"
                "wordprocessingml/2006/main"
            )
        }

        for footnote in root.findall(
            "w:footnote",
            namespace
        ):
            footnote_id = footnote.get(
                (
                    "{http://schemas.openxmlformats.org/"
                    "wordprocessingml/2006/main}"
                    "id"
                )
            )

            # Word bevat technische voetnoten
            # met negatieve IDs. Die bevatten
            # geen inhoudelijke voetnoottekst.
            try:
                if (
                    footnote_id is not None
                    and int(footnote_id) < 0
                ):
                    continue
            except ValueError:
                pass

            delen = []

            for text_node in footnote.findall(
                ".//w:t",
                namespace
            ):
                if (
                    text_node.text
                    and text_node.text.strip()
                ):
                    delen.append(
                        text_node.text.strip()
                    )

            tekst = " ".join(
                delen
            ).strip()

            if tekst:
                teksten.append(
                    tekst
                )

    except (
        zipfile.BadZipFile,
        KeyError,
        ElementTree.ParseError,
    ) as fout:
        print(
            "WAARSCHUWING: voetnoten "
            "konden niet worden uitgelezen:",
            fout
        )

    return teksten


def extract_docx_text(content):
    bestand = io.BytesIO(content)
    document = Document(bestand)

    teksten = []

    for paragraph in document.paragraphs:
        tekst = paragraph.text.strip()

        if tekst:
            teksten.append(
                tekst
            )

    voetnoten = extract_docx_footnotes(
        content
    )

    if voetnoten:
        print(
            "DOCX-voetnoten uitgelezen:",
            len(voetnoten)
        )

        teksten.extend(
            voetnoten
        )

    return "\n".join(
        teksten
    )


def extract_pdf_text(content):
    bestand = io.BytesIO(content)
    reader = PdfReader(bestand)

    teksten = []

    for pagina in reader.pages:
        tekst = pagina.extract_text() or ""

        if tekst.strip():
            teksten.append(tekst.strip())

    return "\n".join(teksten)


def get_document_text(document):
    document_id = document.get("Id")
    nummer = document.get("Nummer")
    content_type = document.get("ContentType", "")

    print(
        f"Document uitlezen: "
        f"{nummer} | {content_type}"
    )

    content, response_content_type = (
        download_document(document_id)
    )

    type_voor_extractie = (
        content_type
        or response_content_type
        or ""
    ).lower()

    if "wordprocessingml" in type_voor_extractie:
        tekst = extract_docx_text(content)

    elif "pdf" in type_voor_extractie:
        tekst = extract_pdf_text(content)

    else:
        raise ValueError(
            f"Niet-ondersteund bestandstype voor "
            f"{nummer}: {type_voor_extractie}"
        )

    if len(tekst.strip()) < 200:
        raise ValueError(
            f"Te weinig leesbare tekst in "
            f"{nummer}: {len(tekst)} tekens"
        )

    return tekst
