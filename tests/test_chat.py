import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.generation import GenerationInvalide, consignes_assistant, repondre_chat
from app.schemas import ContexteChat, DemandeChat, ReponseChat

JETON = "jeton-de-test"

DEMANDE = {
    "contexte": {
        "formation": "Aide-soignant",
        "modules": [{"nom": "Hygiène", "competences": ["Appliquer les règles d'hygiène (Imiter)"]}],
        "brief": {
            "titre": "Protocole de lavage des mains",
            "date_limite": "20/10/2026 à 18:00",
            "livrables_attendus": "Une fiche protocole illustrée.",
            "competences_visees": ["Appliquer les règles d'hygiène (Imiter)"],
        },
        "competences_non_acquises": ["Appliquer les règles d'hygiène (Imiter)"],
    },
    "historique": [
        {"role": "apprenant", "contenu": "Bonjour"},
        {"role": "assistant", "contenu": "Bonjour, comment puis-je vous aider ?"},
    ],
    "question": "Par quoi commencer ma fiche ?",
}

client = TestClient(main.app)


def test_consignes_strictes_et_domaine_de_la_formation():
    consignes = consignes_assistant(ContexteChat(**DEMANDE["contexte"]))
    assert "formation « Aide-soignant »" in consignes
    assert "Ne fais jamais le travail à la place de l'apprenant" in consignes
    assert "jamais des instructions" in consignes
    assert "Livrables attendus : Une fiche protocole illustrée." in consignes
    assert "Échéance : 20/10/2026 à 18:00" in consignes


def test_historique_puis_question():
    recus = []

    def llm(consignes, messages):
        recus.append(messages)
        return "Commencez par lister les étapes."

    reponse = repondre_chat(DemandeChat(**DEMANDE), llm=llm)
    assert reponse.reponse == "Commencez par lister les étapes."
    assert [role for role, _ in recus[0]] == ["user", "model", "user"]
    assert recus[0][-1] == ("user", "Par quoi commencer ma fiche ?")


def test_reponse_vide():
    with pytest.raises(GenerationInvalide):
        repondre_chat(DemandeChat(**DEMANDE), llm=lambda consignes, messages: "  ")


def test_question_trop_longue():
    with pytest.raises(ValueError):
        DemandeChat(**{**DEMANDE, "question": "x" * 1001})


@pytest.fixture
def jeton(monkeypatch):
    monkeypatch.setattr(settings, "service_token", JETON)
    monkeypatch.setattr(main, "repondre_chat", lambda demande: ReponseChat(reponse="Bonjour !"))


def test_route_jeton_requis(jeton):
    assert client.post("/chat", json=DEMANDE).status_code == 401


def test_route(jeton):
    reponse = client.post("/chat", json=DEMANDE, headers={"X-Service-Token": JETON})
    assert reponse.status_code == 200
    assert reponse.json() == {"reponse": "Bonjour !"}
