# EduHub — service IA

Service FastAPI qui génère des quiz et des fiches de révision à partir de supports de cours (PDF, DOCX, PPTX, TXT ou texte brut). Il est appelé par le backend Django d'EduHub, jamais directement par le navigateur.

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

Le service tourne dans le `docker-compose.yml` du backend (service `ia`) : réseau interne joignable seulement par Celery, aucun port publié, sortie vers internet uniquement pour Gemini.

```bash
cd ../backend && docker compose up -d --build ia
```

## Sécurité

- Les appels à `/generate/...` exigent l'en-tête `X-Service-Token` (jeton partagé avec Django). Sans jeton configuré, tout est refusé.
- Fichiers : extension, signature, taille, nombre de pages ou de diapositives, taille une fois décompressé (DOCX, PPTX).
- L'extraction tourne dans un processus à part, arrêté au-delà du délai.

## Configuration

Toutes les valeurs se règlent dans `.env` (voir `.env.example`) ; les valeurs par défaut sont dans `app/config.py`.

| Variable | Rôle | Défaut |
|---|---|---|
| `SERVICE_TOKEN` | Jeton partagé avec Django | — |
| `LLM_API_KEY` | Clé de l'API Gemini (Google AI Studio) | — |
| `LLM_MODEL` | Modèle Gemini utilisé (en production : un Flash plus récent, en tier payant) | gemini-3.1-flash-lite |
| `LLM_DELAI_S` | Délai maximal d'une réponse du LLM, en secondes | 60 |
| `TAILLE_MAX_MO` | Taille maximale d'un fichier | 10 |
| `NB_FICHIERS_MAX` | Nombre maximal de fichiers par requête | 5 |
| `MAX_CHARS` | Longueur maximale du texte extrait | 30000 |
| `NB_QUESTIONS_MAX` | Nombre maximal de questions par quiz | 20 |
| `MAX_ESSAIS` | Essais auprès du LLM avant d'abandonner | 3 |
| `NB_PAGES_MAX` | Pages (PDF) ou diapositives (PPTX) maximum par fichier | 100 |
| `TAILLE_DECOMPRESSEE_MAX_MO` | Taille maximale d'un DOCX ou PPTX décompressé | 100 |
| `EXTRACTION_DELAI_S` | Délai maximal d'extraction d'un fichier, en secondes | 30 |

## Endpoints

- `GET /health` : état du service.
- `POST /generate/quiz` (jeton requis) : fichiers (`fichiers`) et/ou texte (`texte`), nombre de questions (`nb_questions`), difficulté (`difficulte` : `facile`, `moyen` ou `difficile`). Renvoie un quiz validé (questions à choix unique ou multiple, avec explication).
- `POST /generate/fiche` (jeton requis) : fichiers et/ou texte. Renvoie une fiche de révision (titre, résumé, sections en points, à retenir).

Codes d'erreur : `401` jeton invalide, `413` fichier ou texte trop gros, `415` format non supporté, `422` fichier illisible, `502` quiz invalide après plusieurs essais, `503` LLM injoignable (clé absente, quota atteint, délai dépassé) ou jeton non configuré.
