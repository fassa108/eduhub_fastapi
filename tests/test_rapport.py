import json

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.generation import GenerationInvalide, construire_prompt_rapport, generer_rapport
from app.schemas import DemandeRapport, RapportGenere

JETON = "jeton-de-test"

PROMOTION = {
    "type": "promotion",
    "formation": "Aide-soignant",
    "promotion": "P12",
    "periode": "Du 01/09/2026 au 30/06/2027",
    "indicateurs": [{"libelle": "Apprenants", "valeur": "2"}, {"libelle": "Progression moyenne", "valeur": "40 %"}],
    "evolution": [{"semaine": "07/09/2026", "pct": 10}, {"semaine": "14/09/2026", "pct": 40}],
    "competences": [{"competence": "Soins d'hygiène", "niveau": "Imiter", "module": "Soins", "pct": 50}],
    "apprenants": [
        {"reference": "Apprenant 1", "progression_pct": 70, "rendus": 3, "attendus": 3, "retards": 0},
        {
            "reference": "Apprenant 2", "progression_pct": 10, "rendus": 1, "attendus": 3, "retards": 2,
            "niveau": "à risque de décrochage", "signaux": ["2 briefs échus non rendus"],
        },
    ],
}

BILAN = {
    "type": "apprenant",
    "formation": "Aide-soignant",
    "promotion": "P12",
    "indicateurs": [{"libelle": "Progression", "valeur": "10 %"}],
    "competences": [{"competence": "Soins d'hygiène", "niveau": "Imiter", "module": "Soins", "acquise": False}],
    "briefs": [{"titre": "Toilette au lit", "date_limite": "10/10/2026", "statut": "Non rendu", "en_retard": True}],
    "signaux": ["2 briefs échus non rendus"],
    "commentaires_formateur": ["Revoir le protocole."],
}


def reponse(**champs):
    return json.dumps({
        "synthese": "La promotion avance.",
        "points_forts": ["Rendus réguliers"],
        "points_vigilance": ["Hygiène"],
        "apprenants_a_suivre": [
            {"apprenant": "Apprenant 2", "constat": "Deux retards.", "action": "Entretien."},
            {"apprenant": "Awa Ndiaye", "constat": "Inventé.", "action": "Rien."},
        ],
        "recommandations": ["Séance de rattrapage"],
        **champs,
    })


def test_rapport_de_promotion():
    resultat = generer_rapport(DemandeRapport(**PROMOTION), llm=lambda prompt: reponse())
    assert resultat.synthese == "La promotion avance."
    # Une référence inconnue (un nom, par exemple) est écartée
    assert [a.apprenant for a in resultat.apprenants_a_suivre] == ["Apprenant 2"]


def test_bilan_sans_apprenants_a_suivre():
    resultat = generer_rapport(DemandeRapport(**BILAN), llm=lambda prompt: reponse())
    assert resultat.apprenants_a_suivre == []


def test_reponse_invalide():
    with pytest.raises(GenerationInvalide):
        generer_rapport(DemandeRapport(**PROMOTION), llm=lambda prompt: reponse(recommandations=[]))


def test_prompt_de_promotion():
    prompt = construire_prompt_rapport(DemandeRapport(**PROMOTION))
    for attendu in (
        "rapport d'une promotion",
        "n'en calcule ni n'en invente aucun",
        "- Progression moyenne : 40 %",
        "07/09/2026 : 10 %, 14/09/2026 : 40 %",
        "- Soins d'hygiène (Imiter, module Soins) : 50 %",
        "- Apprenant 2 : 10 % du référentiel, 1 rendus sur 3, 2 briefs échus non rendus, à risque de décrochage",
    ):
        assert attendu in prompt


def test_prompt_du_bilan():
    prompt = construire_prompt_rapport(DemandeRapport(**BILAN))
    for attendu in (
        "bilan individuel",
        "Soins d'hygiène (Imiter, module Soins) : pas encore acquise",
        "« Toilette au lit » (échéance 10/10/2026) : Non rendu, rendu en retard",
        "- Revoir le protocole.",
        "- 2 briefs échus non rendus",
    ):
        assert attendu in prompt


def test_reference_pseudonymisee_obligatoire():
    with pytest.raises(ValueError):
        DemandeRapport(**{**PROMOTION, "apprenants": [{**PROMOTION["apprenants"][0], "reference": "Awa Ndiaye"}]})


@pytest.fixture
def jeton(monkeypatch):
    monkeypatch.setattr(settings, "service_token", JETON)
    monkeypatch.setattr(main, "generer_rapport", lambda demande: RapportGenere.model_validate_json(reponse()))


def test_route_jeton_requis(jeton):
    assert client.post("/generate/rapport", json=PROMOTION).status_code == 401


def test_route(jeton):
    resultat = client.post("/generate/rapport", json=PROMOTION, headers={"X-Service-Token": JETON})
    assert resultat.status_code == 200
    assert resultat.json()["recommandations"] == ["Séance de rattrapage"]


def test_route_demande_invalide(jeton):
    resultat = client.post("/generate/rapport", json={**PROMOTION, "type": "autre"}, headers={"X-Service-Token": JETON})
    assert resultat.status_code == 422


client = TestClient(main.app)
