from fastapi import FastAPI
from app.config import settings
# Import models to ensure they are registered with Base (will be used later for migrations/creation)
# from app.models import user, line, stop, route, trip, transfer, payment
from app.database import engine, Base

# Create tables (for development purposes, usually handled by Alembic in prod)
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.get("/")
def root():
    return {"message": "Welcome to Planificador Rutas Micros SC API"}

# Include routers here later
from app.api.v1 import api_router

app.include_router(api_router, prefix=settings.API_V1_STR)
