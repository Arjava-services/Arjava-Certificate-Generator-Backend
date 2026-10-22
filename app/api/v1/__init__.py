from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.v1.templates import router as templates_router
from app.api.v1.sheets import router as sheets_router
from app.api.v1.mappings import router as mappings_router
from app.api.v1.generate import router as generate_router
from app.api.v1.certificates import router as certificates_router

api_v1_router = APIRouter()
api_v1_router.include_router(projects_router)
api_v1_router.include_router(templates_router)
api_v1_router.include_router(sheets_router)
api_v1_router.include_router(mappings_router)
api_v1_router.include_router(generate_router)
api_v1_router.include_router(certificates_router)
