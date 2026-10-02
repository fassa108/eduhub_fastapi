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