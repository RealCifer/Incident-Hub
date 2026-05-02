from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Incident Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    REDIS_URI: str = "redis://localhost:6379/0"
    MONGODB_URI: str = "mongodb://localhost:27017/ims"
    MONGODB_DB_NAME: str = "ims"
    
    class Config:
        case_sensitive = True

settings = Settings()
