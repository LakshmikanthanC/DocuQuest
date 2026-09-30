from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI-Powered RAG Document Assistant"
    api_prefix: str = "/api"
    debug: bool = False

    # ---- Security ----
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # ---- Default account (seeded on startup) ----
    seed_default_user: bool = True
    default_user_email: str = "admin@example.com"
    default_user_password: str = "admin12345"
    default_user_name: str = "Admin"

    # ---- Ollama ----
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1"
    llm_temperature: float = 0.1
    llm_num_ctx: int = 4096
    # Reloading a model into memory costs several seconds on CPU, so hold it
    # resident well past the Ollama default of 5 minutes.
    llm_keep_alive: str = "30m"
    # Hard cap on generated tokens. Bounds worst-case latency; an answer that
    # needs more is already past the point of being useful.
    llm_num_predict: int = 512

    # ---- Embeddings ----
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ---- HTTP / CORS ----
    # Comma-separated. Defaults to the local dev frontend so a fresh clone works
    # with no configuration; set CORS_ORIGINS in any deployed environment.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- Storage ----
    chroma_persist_directory: Path = BACKEND_DIR / "chroma_db"
    upload_directory: Path = PROJECT_ROOT / "documents"
    database_url: str | None = None

    # ---- RAG tuning ----
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_top_k: int = 4
    max_upload_mb: int = 25
    # Retrieved chunks scoring below this are treated as "no relevant context"
    # and the model is never called. Catches unrelated questions before they
    # reach the LLM, instead of relying on the model to decline.
    #
    # This is measured on the same 0..1 scale the UI shows, where
    # ``score = 1 / (1 + squared_l2_distance)``. That transform is hyperbolic, so
    # it never approaches zero: with normalised embeddings, orthogonal vectors
    # sit at ``1 / (1 + 2) = 0.333``. Any floor below ~0.33 is therefore dead
    # code. 0.4 corresponds to a cosine similarity of 0.4 and matches the
    # frontend's "weak match" boundary, so nothing is dropped that the UI would
    # have rendered as a bare, unlabelled bar.
    min_relevance_score: float = 0.4

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS origins, with blanks and duplicates removed."""
        seen: dict[str, None] = {}
        for raw in self.cors_origins.split(","):
            origin = raw.strip().rstrip("/")
            if origin and origin != "*":
                seen.setdefault(origin, None)
        return list(seen)

    def ensure_directories(self) -> None:
        self.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
        self.upload_directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


settings = get_settings()
