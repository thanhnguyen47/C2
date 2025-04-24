from fastapi import Request, APIRouter
from config import templates

router = APIRouter()

@router.get("/web")
async def dashboard_page(request: Request):
    return templates.TemplateResponse('/web_challs/web_challs.html', context={'request': request, 'active_page': 'web_challs'})  

@router.get("/web/{topic}")
async def get_web_topic(request: Request, topic):
    return templates.TemplateResponse('/web_challs/web_topic.html', context={'request': request, 'active_page': 'web_challs'})  