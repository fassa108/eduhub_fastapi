from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Jeton partagé avec Django (en-tête X-Service-Token). Absent : tout est refusé.
    service_token: str | None = None

    # LLM (Gemini)
    llm_api_key: str | None = None
    llm_model: str = "gemini-3.1-flash-lite"
    llm_delai_s: int = 60

    # Limites
    taille_max_mo: int = 10
    nb_fichiers_max: int = 5
    max_chars: int = 30000
    nb_questions_max: int = 20
    max_essais: int = 3
    nb_pages_max: int = 100
    taille_decompressee_max_mo: int = 100
    extraction_delai_s: int = 30


settings = Settings()