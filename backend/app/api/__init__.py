from fastapi import APIRouter

from app.api.routes.execution import router as execution_router
from app.api.routes.comparisons import router as comparisons_router
from app.api.routes.explanations import router as explanations_router
from app.api.routes.health import router as health_router
from app.api.routes.playground import router as playground_router
from app.api.routes.presets import router as presets_router
from app.api.routes.shares import router as shares_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(execution_router)
api_router.include_router(playground_router)
api_router.include_router(explanations_router)
api_router.include_router(comparisons_router)
api_router.include_router(presets_router)
api_router.include_router(shares_router)
