from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (Gemini)
    llm_api_key: str | None = None
    llm_model: str = "gemini-3.8-flash"
    llm_delai_s: int = 60

    # Limites
    taille_max_mo: int = 10
    nb_fichiers_max: int = 5
    max_chars: int = 30000
    nb_questions_max: int = 20
    max_essais: int = 3


settings = Settings()