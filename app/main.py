from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.extraction import ExtractionError, FormatNonSupporte, extraire_texte
from app.generation import Difficulte, GenerationInvalide, LLMIndisponible, generer_quiz
from app.schemas import QuizGenere
from app.validation import (
    ErreurValidation,
    lire_fichier_valide,
    valider_longueur_texte,
    valider_nombre_fichiers,
)

app = FastAPI(title="Synapse IA")


def _erreur(status: int, e: Exception) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": str(e)})


@app.exception_handler(ErreurValidation)
async def gerer_validation(request, e):
    return _erreur(e.status_code, e)


@app.exception_handler(FormatNonSupporte)
async def gerer_format(request, e):
    return _erreur(415, e)


@app.exception_handler(ExtractionError)
async def gerer_extraction(request, e):
    return _erreur(422, e)


@app.exception_handler(GenerationInvalide)
async def gerer_generation(request, e):
    return _erreur(502, e)


@app.exception_handler(LLMIndisponible)
async def gerer_llm_indisponible(request, e):
    return _erreur(503, e)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate/quiz", response_model=QuizGenere)
def generate_quiz(
    fichiers: list[UploadFile] = File(default=[]),
    texte: str | None = Form(default=None),
    nb_questions: int = Form(default=5, ge=1, le=settings.nb_questions_max),
    difficulte: Difficulte = Form(default="moyen"),
):
    valider_nombre_fichiers(fichiers)

    morceaux = [
        extraire_texte(f.filename, lire_fichier_valide(f)) for f in fichiers
    ]
    if texte and texte.strip():
        morceaux.append(texte.strip())

    if not morceaux:
        raise HTTPException(status_code=422, detail="Aucune source fournie")

    texte_complet = "\n\n".join(morceaux)
    valider_longueur_texte(texte_complet)

    return generer_quiz(texte_complet, nb_questions, difficulte)