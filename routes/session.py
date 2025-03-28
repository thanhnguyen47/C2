from fastapi import Request, APIRouter
from config import templates
from database.bot import get_bot, get_bot_info

router = APIRouter()

@router.get("/session/{token}")
async def get_session(request: Request, token):
    try:
        bot = await get_bot(token)
        bot_info = await get_bot_info(bot["id"])
        if bot and bot_info:
            return templates.TemplateResponse('session.html', context={'request': request, 'bot': bot, 'bot_info': bot_info})
        else:
            return templates.TemplateResponse('404.html', context={"request": request})
    except Exception as e:
            return templates.TemplateResponse('404.html', context={"request": request})
