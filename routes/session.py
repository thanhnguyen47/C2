from fastapi import Request, APIRouter, HTTPException, status, Form
from config import templates
from database.bot import get_bot, get_bot_info
from database.dbmain import get_connection_pool

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

@router.post("/session/{token}/command")
async def post_command(token: str, command: str=Form(...)):
        async with (await get_connection_pool()).acquire() as conn:
            try:
                # check if bot is existed
                bot = await conn.fetchrow(
                    "SELECT * FROM bots WHERE token = $1",
                    token
                )
                if not bot or not command:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="error")
                bot_id = bot["id"]
                # add this command to commands table with status=pending (default)
                await conn.execute(
                    """
                    INSERT INTO commands (bot_id, command)
                    VALUES ($1, $2)
                    """,
                    bot_id, command
                )
                return {"message":f"command '{command}' saved in database waiting for senting to bot {token}"}
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error sending command")
          