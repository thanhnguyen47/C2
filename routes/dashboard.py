from fastapi import Request, APIRouter
from config import templates

dashboard_router = APIRouter()

@dashboard_router.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse('dashboard.html', context={'request': request, 'error': None})  