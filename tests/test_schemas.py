import pytest
from pydantic import ValidationError
from app.schemas import QuestionGeneree


def test_choix_unique_valide():
    q = QuestionGeneree(
        intitule="Framework web Python ?",
        type="choix_unique",
        options=[
            {"texte": "Django", "est_correcte": True},
            {"texte": "React", "est_correcte": False},
        ],
    )
    assert q.explication is None


def test_choix_unique_avec_deux_bonnes_reponses():
    with pytest.raises(ValidationError):
        QuestionGeneree(
            intitule="Framework web Python ?",
            type="choix_unique",
            options=[
                {"texte": "Django", "est_correcte": True},
                {"texte": "Flask", "est_correcte": True},
            ],
        )

def test_aucune_bonne_reponse():
    with pytest.raises(ValidationError):
        QuestionGeneree(
            intitule="Framework web Python ?",
            type="choix_multiple",
            options=[
                {"texte": "React", "est_correcte": False},
                {"texte": "Docker", "est_correcte": False},
            ],
        )
