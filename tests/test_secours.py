import pytest
from google.genai import errors

from app import generation
from app.config import settings
from app.generation import LLMIndisponible, appeler_llm, appeler_llm_chat


class Reponse:
    def __init__(self, text):
        self.text = text


def client_simule(monkeypatch, comportements):
    """comportements : modèle → code d'erreur (int) ou texte de la réponse."""
    appels = []

    class Models:
        def generate_content(self, model, **kwargs):
            appels.append(model)
            resultat = comportements[model]
            if isinstance(resultat, int):
                raise errors.ServerError(resultat, {"error": {"message": "erreur"}}) if resultat >= 500 \
                    else errors.ClientError(resultat, {"error": {"message": "erreur"}})
            return Reponse(resultat)

    class Client:
        models = Models()

    monkeypatch.setattr(generation, "_client", lambda: Client())
    monkeypatch.setattr(settings, "llm_model", "principal")
    monkeypatch.setattr(settings, "llm_modeles_secours", "secours-1, secours-2")
    return appels


def test_modele_de_secours_si_surcharge(monkeypatch):
    appels = client_simule(monkeypatch, {"principal": 503, "secours-1": "{}", "secours-2": "jamais"})
    assert appeler_llm("prompt") == "{}"
    assert appels == ["principal", "secours-1"]


def test_quota_puis_dernier_secours_pour_le_chat(monkeypatch):
    appels = client_simule(monkeypatch, {"principal": 429, "secours-1": 500, "secours-2": "Bonjour"})
    assert appeler_llm_chat("consignes", [("user", "Bonjour")]) == "Bonjour"
    assert appels == ["principal", "secours-1", "secours-2"]


def test_requete_refusee_sans_secours(monkeypatch):
    appels = client_simule(monkeypatch, {"principal": 400, "secours-1": "{}", "secours-2": "{}"})
    with pytest.raises(LLMIndisponible, match="400"):
        appeler_llm("prompt")
    assert appels == ["principal"]


def test_tous_indisponibles(monkeypatch):
    client_simule(monkeypatch, {"principal": 503, "secours-1": 503, "secours-2": 503})
    with pytest.raises(LLMIndisponible, match="503"):
        appeler_llm("prompt")


def test_liste_des_modeles_sans_doublon(monkeypatch):
    monkeypatch.setattr(settings, "llm_model", "a")
    monkeypatch.setattr(settings, "llm_modeles_secours", "b, a,,c")
    assert settings.modeles == ["a", "b", "c"]
    monkeypatch.setattr(settings, "llm_modeles_secours", "")
    assert settings.modeles == ["a"]
