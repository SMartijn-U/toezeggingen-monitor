import io
import requests
from docx import Document


BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v5"


TEST_DOCUMENT_ID = (
    "7f493f98-10f7-4a2a-bc6e-05d885fba0d9"
)


def download_document(document_id):
    url = (
        f"{BASE_URL}/Document"
        f"({document_id})/resource"
    )

    print(f"Document downloaden: {url}")

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    print(
        f"Download geslaagd: "
        f"{len(response.content)} bytes"
    )

    print(
        f"Content-Type: "
        f"{response.headers.get('Content-Type')}"
    )

    return response.content


def extract_docx_text(content):
    bestand = io.BytesIO(content)

    document = Document(bestand)

    teksten = []

    for paragraph in document.paragraphs:
        tekst = paragraph.text.strip()

        if tekst:
            teksten.append(tekst)

    return "\n".join(teksten)


if __name__ == "__main__":
    content = download_document(
        TEST_DOCUMENT_ID
    )

    tekst = extract_docx_text(content)

    print(
        f"\nAantal tekens uit document: "
        f"{len(tekst)}"
    )

    print("\nEERSTE 4000 TEKENS:\n")

    print(tekst[:4000])
