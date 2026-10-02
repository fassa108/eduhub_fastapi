from functools import cache
from typing import Literal

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.config import settings
from app.schemas import QuizGenere

Difficulte = Literal["facile", "moyen", "difficile"]

CONSIGNES_DIFFICULTE = {
    "facile": "Questions de restitution : définitions et notions clés du cours.",
    "moyen": "Questions de compréhension : relier des notions, reconnaître un exemple.",
    "difficile": (
        "Questions d'application et d'analyse : cas concrets, pièges fréquents, "
        "distinguer des notions proches."
    ),
}


class GenerationInvalide(Exception):
    """Le LLM n'a pas produit un quiz valide après plusieurs essais."""


class LLMIndisponible(Exception):
    """Le LLM ne répond pas : clé absente, quota atteint, erreur réseau ou délai dépassé."""


@cache
def _client() -> genai.Client:
    if not settings.llm_api_key:
        raise LLMIndisponible("Clé du LLM non configurée")
    return genai.Client(
        api_key=settings.llm_api_key,
        http_options=types.HttpOptions(
            timeout=settings.llm_delai_s * 1000,
            # Quota (429) ou surcharge passagère (503) : on réessaie en espaçant
            retry_options=types.HttpRetryOptions(
                attempts=4,
                initial_delay=2,
                max_delay=20,
                http_status_codes=[429, 500, 503],
            ),
        ),
    )


def appeler_llm(prompt: str) -> str:
    """Appelle Gemini en imposant le schéma JSON du quiz."""
    try:
        reponse = _client().models.generate_content(
            model=settings.llm_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=QuizGenere.model_json_schema(),
            ),
        )
    except errors.APIError as e:
        raise LLMIndisponible(f"Le LLM a renvoyé une erreur ({e.code})") from e
    except Exception as e:
        raise LLMIndisponible("Le LLM ne répond pas") from e
    return reponse.text or ""


def construire_prompt(texte: str, nb_questions: int, difficulte: Difficulte) -> str:
    return (
        "Tu es un assistant pédagogique. À partir du cours ci-dessous, "
        f"génère un quiz de {nb_questions} questions en français.\n\n"
        f"Difficulté : {difficulte}. {CONSIGNES_DIFFICULTE[difficulte]}\n\n"
        "Règles :\n"
        '- "type" vaut "choix_unique" (une seule bonne option) '
        'ou "choix_multiple" (plusieurs bonnes options).\n'
        "- Chaque question a entre 3 et 5 options, dont au moins une correcte.\n"
        "- Base-toi uniquement sur le cours fourni.\n"
        '- "explication" justifie brièvement la ou les bonnes réponses.\n\n'
        f"Cours :\n{texte}"
    )


def isoler_json(brut: str) -> str:
    """Garde ce qui est entre la première { et la dernière }."""
    debut = brut.find("{")
    fin = brut.rfind("}")
    if debut == -1 or fin == -1:
        return brut
    return brut[debut : fin + 1]


def generer_quiz(
    texte: str,
    nb_questions: int = 5,
    difficulte: Difficulte = "moyen",
    llm=appeler_llm,
) -> QuizGenere:
    prompt = construire_prompt(texte[: settings.max_chars], nb_questions, difficulte)

    for _ in range(settings.max_essais):
        brut = llm(prompt)
        try:
            return QuizGenere.model_validate_json(isoler_json(brut))
        except ValidationError:
            continue

    raise GenerationInvalide(f"Quiz invalide après {settings.max_essais} essais")
