from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
# Import models to ensure they are registered with Base (will be used later for migrations/creation)
from app.models import user, line, stop, route, trip, transfer, payment, pattern, pattern_stop, poi
from app.database import engine, Base
from sqlalchemy import text

# Create tables (for development purposes, usually handled by Alembic in prod)
with engine.connect() as connection:
    try:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        connection.commit()
    except Exception as e:
        print(f"Warning: Could not enable PostGIS extension. Geospatial features may fail. Error: {e}")
        connection.rollback()
        
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS transporte"))
    connection.commit()
    
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware - Permitir peticiones desde el frontend trufi-core
# Nota: allow_credentials=True NO funciona con allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes (desarrollo)
    allow_credentials=False,  # Debe ser False cuando origins es "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to Planificador Rutas Micros SC API"}

# Include routers here later
from app.api.v1 import api_router

app.include_router(api_router, prefix=settings.API_V1_STR)

# Photon-compatible endpoints (for trufi-core compatibility)
from app.api.photon_compat import router as photon_router
app.include_router(photon_router)

# GraphQL endpoint (for trufi-core transit routes)
from strawberry.fastapi import GraphQLRouter
from app.graphql_schema import schema
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
