from typing import Literal
from pydantic import BaseModel, Field, model_validator


class OptionGeneree(BaseModel):
    texte: str = Field(min_length=1)
    est_correcte: bool


class QuestionGeneree(BaseModel):
    intitule: str = Field(min_length=1)
    type: Literal["choix_unique", "choix_multiple"]
    options: list[OptionGeneree] = Field(min_length=2)
    explication: str | None = None

    @model_validator(mode="after")
    def verifier_coherence(self):
        nb_correctes = sum(o.est_correcte for o in self.options)
        if nb_correctes == 0:
            raise ValueError("Au moins une option doit être correcte")
        if self.type == "choix_unique" and nb_correctes != 1:
            raise ValueError("Un choix unique doit avoir exactement une bonne option")
        return self


class QuizGenere(BaseModel):
    questions: list[QuestionGeneree] = Field(min_length=1)

class SectionFiche(BaseModel):
    titre: str = Field(min_length=1)
    points: list[str] = Field(min_length=1)


class FicheGeneree(BaseModel):
    titre: str = Field(min_length=1)
    resume: str = Field(min_length=1)
    sections: list[SectionFiche] = Field(min_length=1)
    a_retenir: list[str] = Field(min_length=1)


# ─── Accompagnement d'un apprenant en difficulté ─────────────────────────────

class BriefAccompagnement(BaseModel):
    titre: str = Field(min_length=1, max_length=255)
    statut: Literal["en_retard", "en_cours"]
    date_limite: str = Field(max_length=40)
    description: str = Field(default="", max_length=4000)
    modalites_evaluation: str = Field(default="", max_length=3000)
    livrables_attendus: str = Field(default="", max_length=3000)


class CompetenceAccompagnement(BaseModel):
    competence: str = Field(min_length=1, max_length=255)
    niveau: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=1000)
    brief: str = Field(default="", max_length=255)


class DemandeAccompagnement(BaseModel):
    """Situation d'un apprenant, anonymisée par Django (ni nom ni email)."""

    signaux: list[str] = Field(min_length=1, max_length=10)
    briefs: list[BriefAccompagnement] = Field(default=[], max_length=10)
    competences_non_acquises: list[CompetenceAccompagnement] = Field(default=[], max_length=30)
    commentaires_formateur: list[str] = Field(default=[], max_length=10)
    progression_pct: int | None = Field(default=None, ge=0, le=100)
    moyenne_promotion_pct: int | None = Field(default=None, ge=0, le=100)


class SuggestionFormateur(BaseModel):
    action: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class EtapePlan(BaseModel):
    titre: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    brief: str | None = None


class PlanApprenant(BaseModel):
    message: str = Field(min_length=1)
    etapes: list[EtapePlan] = Field(min_length=1)


class AccompagnementGenere(BaseModel):
    diagnostic: str = Field(min_length=1)
    suggestions_formateur: list[SuggestionFormateur] = Field(min_length=1)
    plan_apprenant: PlanApprenant


# ─── Assistant de l'apprenant (chat) ─────────────────────────────────────────

class ModuleChat(BaseModel):
    nom: str = Field(min_length=1, max_length=255)
    competences: list[str] = Field(default=[], max_length=60)


class BriefChat(BaseModel):
    titre: str = Field(min_length=1, max_length=255)
    module: str = Field(default="", max_length=255)
    date_limite: str = Field(default="", max_length=40)
    rendu: bool = False
    description: str = Field(default="", max_length=4000)
    contexte: str = Field(default="", max_length=4000)
    modalites_pedagogiques: str = Field(default="", max_length=3000)
    modalites_evaluation: str = Field(default="", max_length=3000)
    criteres_performance: str = Field(default="", max_length=3000)
    livrables_attendus: str = Field(default="", max_length=3000)
    competences_visees: list[str] = Field(default=[], max_length=30)


class ContexteChat(BaseModel):
    """Contexte pédagogique fourni par Django (anonymisé : ni nom ni email)."""

    formation: str = Field(min_length=1, max_length=255)
    description_formation: str = Field(default="", max_length=2000)
    modules: list[ModuleChat] = Field(default=[], max_length=40)
    brief: BriefChat | None = None
    competences_non_acquises: list[str] = Field(default=[], max_length=30)
    commentaires_formateur: list[str] = Field(default=[], max_length=10)


class MessageChat(BaseModel):
    role: Literal["apprenant", "assistant"]
    contenu: str = Field(min_length=1, max_length=6000)


class DemandeChat(BaseModel):
    contexte: ContexteChat
    historique: list[MessageChat] = Field(default=[], max_length=10)
    question: str = Field(min_length=1, max_length=1000)


class ReponseChat(BaseModel):
    reponse: str = Field(min_length=1)
