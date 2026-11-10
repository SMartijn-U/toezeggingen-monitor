import io
import requests

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


def extract_docx_text(content):
    bestand = io.BytesIO(content)
    document = Document(bestand)

    teksten = []

    for paragraph in document.paragraphs:
        tekst = paragraph.text.strip()

        if tekst:
            teksten.append(tekst)

    return "\n".join(teksten)


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
