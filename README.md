# EduHub — service IA

Service FastAPI qui génère des quiz à partir de supports de cours (PDF, DOCX, PPTX, TXT ou texte brut). Il est appelé par le backend Django d'EduHub, jamais directement par le navigateur.

## Lancer en local

```bash
cp .env.example .env        # puis renseigner les valeurs
uv sync
uv run uvicorn app.main:app --reload
```

Documentation interactive : http://localhost:8000/docs

## Tests

```bash
uv run pytest
```

## Docker

```bash
docker build -t eduhub-ia .
docker run --env-file .env -p 8000:8000 eduhub-ia
```

## Configuration

Toutes les valeurs se règlent dans `.env` (voir `.env.example`) ; les valeurs par défaut sont dans `app/config.py`.

| Variable | Rôle | Défaut |
|---|---|---|
| `LLM_API_KEY` | Clé de l'API Gemini (Google AI Studio) | — |
| `LLM_MODEL` | Modèle Gemini utilisé | gemini-3.8-flash |
| `LLM_DELAI_S` | Délai maximal d'une réponse du LLM, en secondes | 60 |
| `TAILLE_MAX_MO` | Taille maximale d'un fichier | 10 |
| `NB_FICHIERS_MAX` | Nombre maximal de fichiers par requête | 5 |
| `MAX_CHARS` | Longueur maximale du texte extrait | 30000 |
| `NB_QUESTIONS_MAX` | Nombre maximal de questions par quiz | 20 |
| `MAX_ESSAIS` | Essais auprès du LLM avant d'abandonner | 3 |

## Endpoints

- `GET /health` : état du service.
- `POST /generate/quiz` : fichiers (`fichiers`) et/ou texte (`texte`), nombre de questions (`nb_questions`), difficulté (`difficulte` : `facile`, `moyen` ou `difficile`). Renvoie un quiz validé (questions à choix unique ou multiple, avec explication).

Si le LLM est injoignable (clé absente, quota atteint, délai dépassé), la génération répond `503`.
