from fastapi import Request, APIRouter
from config import templates

router = APIRouter()

@router.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse('dashboard.html', context={'request': request, 'active_page': 'dashboard'})  
