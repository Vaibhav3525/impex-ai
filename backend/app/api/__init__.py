from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.analytics import router as analytics_router
from app.api.import_leads import router as import_router
from app.api.discovery import router as discovery_router
from app.api.products import router as products_router
from app.api.pipeline import router as pipeline_router
from app.api.outreach import router as outreach_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(leads_router)
api_router.include_router(analytics_router)
api_router.include_router(import_router)
api_router.include_router(discovery_router)
api_router.include_router(products_router)
api_router.include_router(pipeline_router)
api_router.include_router(outreach_router)
