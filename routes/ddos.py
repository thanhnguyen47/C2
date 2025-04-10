from fastapi import Request, APIRouter, HTTPException, status, Form
from config import templates
from database.bot import get_bot, get_bot_info, get_logs
from database.dbmain import get_connection_pool, redis_client
from sse_starlette import EventSourceResponse
import json
import docker

router = APIRouter()

docker_client = docker.from_env()

@router.get("/ddos")
async def ddos_simulation(request: Request):
    return templates.TemplateResponse('ddos_simulation/ddos.html', context={'request': request, 'active_page':'ddos'})


# we need to store container id running
user_containers = {} # {user_id: container_id}

@router.post("/ddos/start-target")
async def start_target(request: Request):
    # check if target for this user already running
    user_id = str(request.state.user["id"])

    # create new container
    container = docker_client.containers.run(
         "target-machine",
         detach=True,
         ports={'80/tcp':None}, # docker will automatically assign a port for it
        labels={
             "traefik.enable": "true",
             f"traefik.http.routers.user{user_id}.rule": f"Host(`user{user_id}.lab.local`)"
        },
        cpu_count=1,
        mem_limit="256m",
        network="thanh_c2-network"
    )
    user_containers[user_id] = container.id
    container.reload()
    port = container.attrs['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']
    target_url = f"http://user{user_id}.lab.local"
    return {"target": target_url, "port": port}

@router.post("/ddos/stop-target")
async def stop_target(request: Request):
    user_id = str(request.state.user["id"])

    container_id = user_containers[user_id]
    container = docker_client.containers.get(container_id)
    container.stop()
    container.remove()
    del user_containers[user_id]
    
    return {"message": "target stopped and removed"}

@router.get("/ddos/{token}")
async def get_session(request: Request, token):
    try:
        bot = await get_bot(token)
        bot_info = await get_bot_info(bot["id"])
        logs = await get_logs(bot["id"])
        if bot and bot_info:
            return templates.TemplateResponse('ddos_simulation/bot_c2.html', context={'request': request, 'bot': bot, 'bot_info': bot_info, 'logs': logs, 'active_page':'ddos'})
        else:
            return templates.TemplateResponse('404.html', context={"request": request})
    except Exception as e:
            print(f"Exception: {str(e)}")
            return templates.TemplateResponse('404.html', context={"request": request})

@router.post("/ddos/{token}/command")
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
            bot_info = await get_bot_info(bot_id)
            # add this command to commands table with status=pending (default)
            await conn.execute(
                """
                INSERT INTO commands (bot_id, command, directory)
                VALUES ($1, $2, $3)
                """,
                bot_id, command, bot_info["current_directory"]
            )
            return {"message":f"command '{command}' saved in database waiting for senting to bot {token}"}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error sending command")
        
@router.get("/sse/{token}")
async def sse_endpoint(token):
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"bot_results:{token}")
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                yield {"event": "new_result", "data": json.dumps(data)}
    return EventSourceResponse(event_generator())