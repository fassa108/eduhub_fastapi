import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.generation import GenerationInvalide, construire_prompt_accompagnement, generer_accompagnement
from app.schemas import AccompagnementGenere, DemandeAccompagnement

JETON = "jeton-de-test"

DEMANDE = {
    "signaux": ["2 briefs échus non rendus", "Aucun dépôt depuis 16 jours"],
    "briefs": [
        {
            "titre": "Site vitrine responsive",
            "statut": "en_retard",
            "date_limite": "10/10/2026",
            "description": "Créer le site vitrine d'une boulangerie.",
            "modalites_evaluation": "Revue de code et démonstration.",
            "livrables_attendus": "Lien du dépôt GitHub.",
        }
    ],
    "competences_non_acquises": [
        {"competence": "Intégrer une maquette", "niveau": "Imiter", "brief": "Site vitrine responsive"}
    ],
    "commentaires_formateur": ["Pense à tester sur mobile."],
    "progression_pct": 20,
    "moyenne_promotion_pct": 55,
}

REPONSE_VALIDE = """{"diagnostic": "Deux briefs en retard.",
"suggestions_formateur": [{"action": "Entretien", "detail": "Faire le point cette semaine."}],
"plan_apprenant": {"message": "Vous pouvez y arriver.",
"etapes": [{"titre": "Structurer la page", "detail": "Commencer par le HTML.", "brief": "Site vitrine responsive"}]}}"""

client = TestClient(main.app)


def test_accompagnement_valide():
    resultat = generer_accompagnement(DemandeAccompagnement(**DEMANDE), llm=lambda prompt: REPONSE_VALIDE)
    assert resultat.plan_apprenant.etapes[0].brief == "Site vitrine responsive"


def test_reponse_invalide():
    with pytest.raises(GenerationInvalide):
        generer_accompagnement(DemandeAccompagnement(**DEMANDE), llm=lambda prompt: '{"diagnostic": ""}')


def test_le_prompt_reprend_les_directives_et_les_signaux():
    prompt = construire_prompt_accompagnement(DemandeAccompagnement(**DEMANDE))
    for attendu in (
        "Aucun dépôt depuis 16 jours",
        "Brief « Site vitrine responsive » (en retard, échéance : 10/10/2026)",
        "Modalités d'évaluation : Revue de code",
        "Livrables attendus : Lien du dépôt GitHub.",
        "- Intégrer une maquette — niveau Imiter (brief « Site vitrine responsive »)",
        "moyenne de la promotion : 55 %",
        "Pense à tester sur mobile.",
    ):
        assert attendu in prompt


def test_au_moins_un_signal():
    with pytest.raises(ValueError):
        DemandeAccompagnement(**{**DEMANDE, "signaux": []})


@pytest.fixture
def jeton(monkeypatch):
    monkeypatch.setattr(settings, "service_token", JETON)
    monkeypatch.setattr(
        main, "generer_accompagnement", lambda demande: AccompagnementGenere.model_validate_json(REPONSE_VALIDE)
    )


def test_route_jeton_requis(jeton):
    assert client.post("/generate/accompagnement", json=DEMANDE).status_code == 401


def test_route(jeton):
    reponse = client.post("/generate/accompagnement", json=DEMANDE, headers={"X-Service-Token": JETON})
    assert reponse.status_code == 200
    assert reponse.json()["diagnostic"] == "Deux briefs en retard."


def test_route_demande_invalide(jeton):
    reponse = client.post(
        "/generate/accompagnement", json={**DEMANDE, "progression_pct": 150}, headers={"X-Service-Token": JETON}
    )
    assert reponse.status_code == 422
