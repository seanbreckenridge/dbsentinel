from pydantic import BaseSettings


class Settings(BaseSettings):
    SQL_ECHO: bool = True
    BEARER_SECRET: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str
    S3_URL_PREFIX: str
    IMAGE_CACHE_AUTO_DUMP: bool

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

if __name__ == "__main__":
    print(settings.dict())
