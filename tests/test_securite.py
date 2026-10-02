import io
import time
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.extraction import (
    ExtractionTropLongue,
    TropDePages,
    extraire_texte,
    extraire_texte_avec_delai,
)
from app.schemas import QuizGenere

JETON = "jeton-de-test"
QUIZ = QuizGenere.model_validate(
    {
        "questions": [
            {
                "intitule": "Framework Python ?",
                "type": "choix_unique",
                "options": [
                    {"texte": "Django", "est_correcte": True},
                    {"texte": "React", "est_correcte": False},
                ],
            }
        ]
    }
)

client = TestClient(main.app)


@pytest.fixture
def jeton(monkeypatch):
    monkeypatch.setattr(settings, "service_token", JETON)
    monkeypatch.setattr(main, "generer_quiz", lambda *args: QUIZ)


def _generer(**entetes):
    return client.post("/generate/quiz", data={"texte": "cours"}, headers=entetes)


# ─── Jeton partagé ───────────────────────────────────────────────────────────

def test_health_sans_jeton():
    assert client.get("/health").status_code == 200


def test_generation_sans_jeton(jeton):
    assert _generer().status_code == 401


def test_generation_mauvais_jeton(jeton):
    assert _generer(**{"X-Service-Token": "faux"}).status_code == 401


def test_generation_bon_jeton(jeton):
    reponse = _generer(**{"X-Service-Token": JETON})
    assert reponse.status_code == 200
    assert reponse.json()["questions"][0]["intitule"] == "Framework Python ?"


def test_jeton_non_configure(monkeypatch):
    monkeypatch.setattr(settings, "service_token", None)
    assert _generer(**{"X-Service-Token": "n'importe"}).status_code == 503


# ─── Limites d'extraction ────────────────────────────────────────────────────

def test_pdf_trop_de_pages(monkeypatch):
    monkeypatch.setattr(settings, "nb_pages_max", 2)
    document = pymupdf.open()
    for _ in range(3):
        document.new_page().insert_text((72, 72), "Page de cours")
    with pytest.raises(TropDePages):
        extraire_texte("cours.pdf", document.tobytes())


def test_docx_trop_volumineux_une_fois_decompresse(jeton, monkeypatch):
    monkeypatch.setattr(settings, "taille_decompressee_max_mo", 1)
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"0" * (2 * 1024 * 1024))
    reponse = client.post(
        "/generate/quiz",
        files={"fichiers": ("bombe.docx", tampon.getvalue())},
        headers={"X-Service-Token": JETON},
    )
    assert reponse.status_code == 413


def extraction_bloquee(nom, contenu):
    time.sleep(30)


def test_extraction_arretee_au_dela_du_delai(monkeypatch):
    monkeypatch.setattr(settings, "extraction_delai_s", 1)
    debut = time.monotonic()
    with pytest.raises(ExtractionTropLongue):
        extraire_texte_avec_delai("cours.pdf", b"", extracteur=extraction_bloquee)
    assert time.monotonic() - debut < 10


def test_extraction_dans_un_processus_a_part():
    assert extraire_texte_avec_delai("cours.txt", "Bonjour".encode()) == "Bonjour"
