from pydantic import BaseSettings


class Settings(BaseSettings):
    SQL_ECHO: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

if __name__ == "__main__":
    print(settings.dict())
