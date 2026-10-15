from functools import cache, partial
from typing import Literal

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.schemas import AccompagnementGenere, DemandeAccompagnement, FicheGeneree, QuizGenere

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
    """Le LLM n'a pas produit un résultat valide après plusieurs essais."""


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


def appeler_llm(prompt: str, schema: type[BaseModel] = QuizGenere) -> str:
    """Appelle Gemini en imposant le schéma JSON attendu."""
    try:
        reponse = _client().models.generate_content(
            model=settings.llm_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=schema.model_json_schema(),
            ),
        )
    except errors.APIError as e:
        raise LLMIndisponible(f"Le LLM a renvoyé une erreur ({e.code})") from e
    except Exception as e:
        raise LLMIndisponible("Le LLM ne répond pas") from e
    return reponse.text or ""


def construire_prompt_fiche(texte: str) -> str:
    return (
        "Tu es un assistant pédagogique. À partir du cours ci-dessous, rédige "
        "une fiche de révision en français pour un apprenant.\n\n"
        "Règles :\n"
        '- "resume" : deux ou trois phrases qui situent le sujet.\n'
        '- "sections" : les grandes notions du cours, chacune avec des points '
        "courts et précis (définitions, règles, exemples).\n"
        '- "a_retenir" : l\'essentiel en quelques points.\n'
        "- Base-toi uniquement sur le cours fourni.\n\n"
        f"Cours :\n{texte}"
    )


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


def _generer(prompt: str, modele: type[BaseModel], llm) -> BaseModel:
    """Appelle le LLM et valide sa réponse ; réessaie si elle est invalide."""
    for _ in range(settings.max_essais):
        brut = llm(prompt)
        try:
            return modele.model_validate_json(isoler_json(brut))
        except ValidationError:
            continue

    raise GenerationInvalide(f"Réponse du LLM invalide après {settings.max_essais} essais")


def generer_quiz(
    texte: str,
    nb_questions: int = 5,
    difficulte: Difficulte = "moyen",
    llm=appeler_llm,
) -> QuizGenere:
    prompt = construire_prompt(texte[: settings.max_chars], nb_questions, difficulte)
    return _generer(prompt, QuizGenere, llm)


def generer_fiche(
    texte: str,
    llm=partial(appeler_llm, schema=FicheGeneree),
) -> FicheGeneree:
    return _generer(construire_prompt_fiche(texte[: settings.max_chars]), FicheGeneree, llm)


def _situation(demande: DemandeAccompagnement) -> str:
    """La situation de l'apprenant, en texte lisible par le LLM."""
    lignes = ["Signaux observés :"]
    lignes += [f"- {s}" for s in demande.signaux]
    if demande.progression_pct is not None:
        moyenne = (
            f" (moyenne de la promotion : {demande.moyenne_promotion_pct} %)"
            if demande.moyenne_promotion_pct is not None else ""
        )
        lignes.append(f"\nCompétences du référentiel acquises : {demande.progression_pct} %{moyenne}")

    for b in demande.briefs:
        etat = "en retard" if b.statut == "en_retard" else "en cours"
        lignes.append(f"\nBrief « {b.titre} » ({etat}, échéance : {b.date_limite})")
        if b.description:
            lignes.append(f"Sujet : {b.description}")
        if b.modalites_evaluation:
            lignes.append(f"Modalités d'évaluation : {b.modalites_evaluation}")
        if b.livrables_attendus:
            lignes.append(f"Livrables attendus : {b.livrables_attendus}")

    if demande.competences_non_acquises:
        lignes.append("\nCompétences non acquises dont l'échéance est passée :")
        for c in demande.competences_non_acquises:
            niveau = f" — niveau {c.niveau}" if c.niveau else ""
            detail = f" : {c.description}" if c.description else ""
            brief = f" (brief « {c.brief} »)" if c.brief else ""
            lignes.append(f"- {c.competence}{niveau}{detail}{brief}")

    if demande.commentaires_formateur:
        lignes.append("\nCommentaires du formateur sur les évaluations précédentes :")
        lignes += [f"- {c}" for c in demande.commentaires_formateur]
    return "\n".join(lignes)


def construire_prompt_accompagnement(demande: DemandeAccompagnement) -> str:
    return (
        "Tu es un conseiller pédagogique dans une formation par compétences. "
        "Un apprenant montre des signes de difficulté. À partir de sa situation "
        "ci-dessous, aide son formateur à l'accompagner. Réponds en français.\n\n"
        "Règles :\n"
        '- "diagnostic" : deux ou trois phrases factuelles sur ce qui se passe et '
        "les causes probables, sans juger l'apprenant.\n"
        '- "suggestions_formateur" : trois à cinq actions concrètes pour le '
        "formateur (entretien, découpage d'un brief en étapes, ressource, délai…), "
        'chacune avec un "detail" qui explique comment faire.\n'
        '- "plan_apprenant" : un plan que le formateur pourra transmettre à '
        "l'apprenant. \"message\" l'encourage en le vouvoyant, sans parler de "
        'décrochage ni de risque. "etapes" : trois à six étapes concrètes, dans '
        "l'ordre, qui s'appuient sur le sujet, les modalités d'évaluation et les "
        'livrables attendus des briefs ; "brief" indique le titre du brief concerné.\n'
        "- Priorise les briefs en retard et les compétences non acquises.\n"
        "- Base-toi uniquement sur les informations fournies, n'invente aucun fait.\n\n"
        f"{_situation(demande)[: settings.max_chars]}"
    )


def generer_accompagnement(
    demande: DemandeAccompagnement,
    llm=partial(appeler_llm, schema=AccompagnementGenere),
) -> AccompagnementGenere:
    return _generer(construire_prompt_accompagnement(demande), AccompagnementGenere, llm)
