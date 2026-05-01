from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Incident Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    REDIS_URI: str = "redis://localhost:6379/0"
    
    class Config:
        case_sensitive = True

settings = Settings()
