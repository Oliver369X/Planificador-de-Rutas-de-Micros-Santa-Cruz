from fastapi import APIRouter
from app.api.v1 import auth, lines, stops, trips, routes, transfers, payments, otp_routes, geocoding_routes, pois_routes, favorites, reports, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(lines.router)
api_router.include_router(stops.router)
api_router.include_router(trips.router)
api_router.include_router(routes.router)
api_router.include_router(transfers.router)
api_router.include_router(payments.router)
api_router.include_router(otp_routes.router)
api_router.include_router(geocoding_routes.router)
api_router.include_router(pois_routes.router)
api_router.include_router(favorites.router)
api_router.include_router(reports.router)
api_router.include_router(users.router)
