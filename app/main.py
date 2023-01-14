from fastapi import FastAPI


def create_app() -> FastAPI:
    current_app = FastAPI(title="malsentinel")

    @current_app.on_event("startup")
    async def _startup() -> None:
        from app.db import update_database, init_db

        init_db()
        await update_database()

    return current_app


app = create_app()
