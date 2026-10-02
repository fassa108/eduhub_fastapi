import pytest
from google.genai import errors

from app import generation
from app.config import settings
from app.generation import (
    GenerationInvalide,
    LLMIndisponible,
    _client,
    appeler_llm,
    generer_fiche,
    generer_quiz,
)

QUIZ_VALIDE = """Voici le quiz :
{"questions": [{"intitule": "Framework Python ?", "type": "choix_unique",
"options": [{"texte": "Django", "est_correcte": true},
{"texte": "React", "est_correcte": false}]}]}"""


def test_quiz_valide():
    quiz = generer_quiz("cours", 1, llm=lambda prompt: QUIZ_VALIDE)
    assert len(quiz.questions) == 1


def test_reessaie_apres_un_echec():
    reponses = iter(["pas du json", QUIZ_VALIDE])
    quiz = generer_quiz("cours", 1, llm=lambda prompt: next(reponses))
    assert quiz.questions[0].intitule == "Framework Python ?"


def test_echec_definitif():
    with pytest.raises(GenerationInvalide):
        generer_quiz("cours", 1, llm=lambda prompt: "n'importe quoi")

def test_consigne_de_difficulte_dans_le_prompt():
    prompts = []

    def llm(prompt):
        prompts.append(prompt)
        return QUIZ_VALIDE

    generer_quiz("cours", 1, "difficile", llm=llm)
    assert "Difficulté : difficile" in prompts[0]


def test_cle_absente(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", None)
    _client.cache_clear()
    with pytest.raises(LLMIndisponible):
        appeler_llm("prompt")
    _client.cache_clear()


def test_erreur_de_l_api(monkeypatch):
    class ModelsEnErreur:
        def generate_content(self, **kwargs):
            raise errors.ClientError(429, {"error": {"message": "quota"}})

    class ClientEnErreur:
        models = ModelsEnErreur()

    monkeypatch.setattr(generation, "_client", lambda: ClientEnErreur())
    with pytest.raises(LLMIndisponible, match="429"):
        appeler_llm("prompt")


FICHE_VALIDE = """{"titre": "Django", "resume": "Un framework web Python.",
"sections": [{"titre": "Architecture", "points": ["Motif MVT"]}],
"a_retenir": ["Django suit le motif MVT"]}"""


def test_fiche_valide():
    fiche = generer_fiche("cours", llm=lambda prompt: FICHE_VALIDE)
    assert fiche.sections[0].points == ["Motif MVT"]


def test_fiche_sans_section_rejetee():
    reponses = iter(['{"titre": "Django", "resume": "x", "sections": [], "a_retenir": ["x"]}', FICHE_VALIDE])
    fiche = generer_fiche("cours", llm=lambda prompt: next(reponses))
    assert fiche.titre == "Django"
