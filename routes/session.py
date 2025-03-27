from fastapi import Request, APIRouter
from config import templates

router = APIRouter()

@router.get("/session/{token}")
async def get_session(request: Request, token):
    return templates.TemplateResponse('session.html', context={'request': request, 'error': None})