from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    xai_api_key: str = ""
    xai_model: str = "grok-3-mini"
    app_port: int = 8000
    confidence_threshold: float = 0.6
    max_retries: int = 3
    chroma_db_path: str = "./chroma_db"
    knowledge_base_path: str = "./knowledge_base"
    tool_log_path: str = "./tool_log.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
