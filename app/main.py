from fastapi import FastAPI
from app.config import settings
from app.db import create_db_and_tables
from app.routes.voice import router as voice_router
from app.routes.sms import router as sms_router
from app.routes.leads import router as leads_router
from app.routes.dashboard import router as dashboard_router

app.include_router(dashboard_router)

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(voice_router)
app.include_router(sms_router)
app.include_router(leads_router)