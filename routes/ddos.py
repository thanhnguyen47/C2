from fastapi import Request, APIRouter, HTTPException, status, Form, Response
from fastapi.responses import JSONResponse
from config import templates, C2_URL, AttackRequest, AttackResponse, SUPPORTED_ATTACK_TYPES, docker_client, traefik_container, DOMAIN
from database.bot import get_bot, get_bot_info, get_logs
from database.dbmain import get_connection_pool, redis_client
from sse_starlette import EventSourceResponse
import json
import random
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter()

BOT_TTL = 3600

@router.get("/ddos")
async def ddos_simulation(request: Request):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            bots = await conn.fetch("""
                SELECT id, token, status
                FROM bots
            """)

            bot_list = []
            for bot in bots:
                bot_id = bot["id"]
                token = bot["token"]
                status = bot["status"]

                bot_info = await conn.fetchrow("""
                    SELECT ip, os
                    FROM bot_info
                    WHERE bot_id = $1
                """, bot_id)

                last_seen = await conn.fetchrow("""
                    SELECT timestamp
                    FROM logs
                    WHERE bot_id = $1
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, bot_id)

                bot_list.append({
                    "id": bot_id,
                    "token": token,
                    "status": status,
                    "ip": bot_info["ip"] if bot_info else "N/A",
                    "os": bot_info["os"] if bot_info else "N/A",
                    "last_seen": last_seen["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if last_seen else "N/A",
                })

            return templates.TemplateResponse(
                'ddos_simulation/ddos2.html',
                context={
                    'request': request,
                    'active_page': 'ddos',
                    'bots': bot_list  # Truyền danh sách bot vào template
                }
            )
        except Exception as e:
            print(f"Error fetching bots: {str(e)}")
            return templates.TemplateResponse(
                'ddos_simulation/ddos2.html',
                context={
                    'request': request,
                    'active_page': 'ddos',
                    'bots': []  # Trả về danh sách rỗng nếu có lỗi
                }
            )

@router.post("/ddos/start-target")
async def start_target(request: Request, bot_count: int = Form(1)):
    user_id = str(request.state.user["id"])
    network_name = f"ddos_net_user_{user_id}"

    existing_target = await redis_client.get(f"user_containers:{user_id}")
    existing_botnets = await redis_client.get(f"user_botnets:{user_id}")

    # check if target for this user already running
    if existing_target or existing_botnets:
        return {"message": "Target is already running"}

    # create new isolating network for user
    existing_networks = docker_client.networks.list(names=[network_name])
    if not existing_networks:
        docker_client.networks.create(
            name=network_name,
            driver="bridge",
            check_duplicate=True
        )

    # create new container
    target_domain=f"{uuid.uuid4()}.{DOMAIN}"
    try:
        container = docker_client.containers.run(
            "ddos-target",
            detach=True,
            labels={
                "traefik.enable": "true",
                f"traefik.http.routers.user{user_id}.rule": f"Host(`{target_domain}`)",
                f"traefik.http.routers.user{user_id}.entrypoints": "websecure",  # Thay đổi từ "web" sang "websecure"
                f"traefik.http.routers.user{user_id}.tls": "true",  # Bật TLS
                f"traefik.http.routers.user{user_id}.tls.certresolver": "letsencrypt",  # Dùng resolver để cấp chứng chỉ
                f"traefik.http.services.user{user_id}.loadbalancer.server.port": "80",
                "user_id": user_id
            },
            cpu_quota=100000,  # 100% CPU
            cpu_period=100000,
            mem_limit="256m",
            network=network_name,
            # network_aliases=["ddos-target"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start target: {str(e)}")

    network = docker_client.networks.get(network_name)
    try:
        network.connect(traefik_container)
    except Exception:
        pass

    # save container id into Redis
    await redis_client.setex(f"user_containers:{user_id}", BOT_TTL, container.id)

    c2_network = docker_client.networks.get("ubuntu_c2-network")
    bot_ids = []
    bot_count = min(bot_count, 5)
    for i in range(bot_count):
        bot_id = f"{user_id}_bot_{i}"
        device_type = random.choice(["IoT", "PC", "SERVER", "Mobile"])
        try:
            bot = docker_client.containers.run(
                "ddos-bot",
                detach=True,
                environment={
                    "C2_URL": C2_URL,
                    "BOT_ID": bot_id,
                    "USER_ID": user_id,
                    "NETWORKD_NAME": network_name,
                    "POLLING_INTERVAL": "5",
                    "DEVICE_TYPE": device_type
                },
                labels={"user_id": user_id},
                cpu_quota=50000,  # 50% CPU
                cpu_period=100000,
                mem_limit="128m",
                network=network_name,
                cap_add=["NET_ADMIN", "NET_RAW"]
            )
            c2_network.connect(bot)
            bot_ids.append({"container_id": bot.id, "bot_id": bot_id, "user_id": user_id, "network_name": network_name})
            print(f"Started bot {i+1}/{bot_count} with ID: {bot.id}, BOT ID: {bot_id}, Device Type: {device_type}")
        except Exception as e:
            print(f"Failed to start bot {bot_id}: {str(e)}")
            continue

    # save bot list into Redis
    await redis_client.setex(f"user_botnets:{user_id}", BOT_TTL, json.dumps(bot_ids))

    # Create pending attack record
    attack_id = str(uuid.uuid4())
    target_url = f"https://{target_domain}"
    attack_info = {
        "attack_id": attack_id,
        "user_id": user_id,
        "attack_type": None,
        "target_url": target_url,
        "intensity": None,
        "duration": None,
        "spoof_headers": False,
        "custom_headers": {},
        "spoof_ip": False,
        "packet_size": None,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "bot_count": bot_count
    }
    await redis_client.setex(f"attack:{attack_id}", BOT_TTL, json.dumps(attack_info))

    return {"target": target_url}

@router.post("/ddos/stop-target")
async def stop_target(request: Request):
    user_id = str(request.state.user["id"])
    network_name = f"ddos_net_user_{user_id}"

    botnets = await redis_client.get(f"user_botnets:{user_id}")
    if botnets:
        bot_ids = json.loads(botnets)
        for bot in bot_ids:
            try:
                bot_container = docker_client.containers.get(bot["container_id"])
                container_user_id = bot_container.labels.get("user_id")
                if container_user_id != user_id:
                    continue
                bot_container.stop()
                bot_container.remove()
            except Exception as e:
                print(f"Failed to remove bot {bot['bot_id']}: {str(e)}")
        await redis_client.delete(f"user_botnets:{user_id}")
    print("delete botnet success")

    # Stop and delete the target
    container_id = await redis_client.get(f"user_containers:{user_id}")
    if not container_id:
        async for key in redis_client.scan_iter(f"attack:*"):
            attack_data = await redis_client.get(key)
            if attack_data:
                attack = json.loads(attack_data)
                if attack["user_id"] == user_id:
                    await redis_client.delete(key)
        return {"message": "No target running"}

    try:
        container = docker_client.containers.get(container_id.decode())
        container_user_id = container.labels.get("user_id")
        if container_user_id != user_id:
            raise HTTPException(status_code=403, detail="Target does not belong to this user")
        container.stop()
        container.remove()
        await redis_client.delete(f"user_containers:{user_id}")
    except Exception as e:
        print(f"Failed to stop target: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop target: {str(e)}")
    print("delete target success")

    # Delete any lingering attack info
    async for key in redis_client.scan_iter(f"attack:*"):
        attack_data = await redis_client.get(key)
        if attack_data:
            attack = json.loads(attack_data)
            if attack["user_id"] == user_id:
                await redis_client.delete(key)
    print("delete attack info success")

    # Delete the network
    try:
        network = docker_client.networks.get(network_name)
        try:
            network.disconnect(traefik_container)
        except Exception as e:
            print(f"Failed to disconnect traefik from network: {str(e)}")
        network.reload()
        for container in network.containers:
            try:
                network.disconnect(container)
                print(f"Disconnected container {container.id} from network {network_name}")
            except Exception as e:
                print(f"Failed to disconnect container {container.id}: {str(e)}")
        network.remove()
    except Exception as e:
        print(f"Failed to stop network: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop network: {str(e)}")
    print("delete network success")

    return {"message": "target stopped and removed"}

@router.post("/ddos/attack-target", response_model=AttackResponse)
async def initiate_ddos_attack(request: Request, attack_request: AttackRequest):
    try:
        if attack_request.attack_type not in SUPPORTED_ATTACK_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid attack type.")

        user_id = str(request.state.user["id"])
        network_name = f"ddos_net_user_{user_id}"

        # Check if target exists
        container_id = await redis_client.get(f"user_containers:{user_id}")
        if not container_id:
            raise HTTPException(status_code=400, detail="No target running")

        # Get the botnet of user from Redis
        botnets = await redis_client.get(f"user_botnets:{user_id}")
        if not botnets:
            raise HTTPException(status_code=400, detail="No bots available for this user")

        bot_ids = json.loads(botnets)
        bot_id_list = [bot["bot_id"] for bot in bot_ids]

        # Get the IP of the target container from Docker network
        try:
            target_container = docker_client.containers.get(container_id.decode())
            target_container.reload()
            target_ip = target_container.attrs["NetworkSettings"]["Networks"][network_name]["IPAddress"]
            target_url_for_bot = f"http://{target_ip}"
            print(target_url_for_bot)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get target IP: {str(e)}")

        # Find existing attack record
        attack_info = None
        existing_attack_id = None
        async for key in redis_client.scan_iter(f"attack:*"):
            attack_data = await redis_client.get(key)
            if attack_data:
                attack = json.loads(attack_data)
                if attack["user_id"] == user_id and attack["status"] == "pending":
                    attack_info = attack
                    existing_attack_id = attack["attack_id"]
                    break

        if not attack_info:
            raise HTTPException(status_code=400, detail="No pending attack found")

        # Create attack command with the target's internal IP
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=BOT_TTL)).isoformat()
        attack_command = {
            "attack_id": existing_attack_id,
            "user_id": user_id,
            "attack_type": attack_request.attack_type,
            "intensity": attack_request.intensity,
            "target_url": target_url_for_bot,
            "duration": attack_request.duration,
            "spoof_headers": attack_request.spoof_headers,
            "custom_headers": attack_request.custom_headers,
            "target_port": attack_request.target_port,
            "spoof_ip": attack_request.spoof_ip,
            "packet_size": attack_request.packet_size,
            "expires_at": expires_at
        }

        # Push attack_command into each bot's queue
        queue_keys = []
        for bot_id in bot_id_list:
            queue_key = f"command_queue:{bot_id}"
            try:
                await redis_client.rpush(queue_key, json.dumps(attack_command))
                await redis_client.expire(queue_key, BOT_TTL)
                queue_keys.append(queue_key)
            except Exception as e:
                print(f"Failed to push command to queue {queue_key}: {str(e)}")
                continue

        # Save the queues
        await redis_client.setex(f"user_queues:{user_id}", BOT_TTL, json.dumps(queue_keys))

        # Update attack info
        attack_info = {
            "attack_id": existing_attack_id,
            "user_id": user_id,
            "attack_type": attack_request.attack_type,
            "target_url": str(attack_request.target_url),
            "intensity": attack_request.intensity,
            "duration": attack_request.duration,
            "spoof_headers": attack_request.spoof_headers,
            "custom_headers": attack_request.custom_headers,
            "spoof_ip": attack_request.spoof_ip,
            "packet_size": attack_request.packet_size,
            "status": "started",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "bot_count": attack_info["bot_count"]
        }
        await redis_client.setex(f"attack:{existing_attack_id}", BOT_TTL, json.dumps(attack_info))

        # Initialize report for each bot in Redis
        for bot_id in bot_id_list:
            report_key = f"report:{existing_attack_id}:{bot_id}"
            bot_report = {
                "bot_id": bot_id,
                "requests_sent": 0,
                "status": "pending",
                "error_message": None,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            await redis_client.setex(report_key, BOT_TTL, json.dumps(bot_report))

        return AttackResponse(
            attack_id=existing_attack_id,
            status="started",
            message="Attack initiated successfully"
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"Failed to process avatar: {str(e)}"})

@router.get("/ddos/get-status")
async def get_status(request: Request):
    user_id = str(request.state.user["id"])

    # Check if target exists
    existing_target = await redis_client.get(f"user_containers:{user_id}")
    target_url = None
    if existing_target:
        target_url = f"https://{str(uuid.uuid4())}.{DOMAIN}"

    # Check if botnets exist
    existing_botnets = await redis_client.get(f"user_botnets:{user_id}")
    if not existing_target or not existing_botnets:
        return {"is_attacking": False, "attack_details": None, "target_url": target_url}

    # Check for attack record in Redis
    attack_info = None
    async for key in redis_client.scan_iter(f"attack:*"):
        attack_data = await redis_client.get(key)
        if attack_data:
            attack = json.loads(attack_data)
            if attack["user_id"] == user_id:
                attack_info = attack
                break

    if not attack_info:
        return {"is_attacking": False, "attack_details": None, "target_url": target_url}

    is_attacking = attack_info["status"] == "started"
    attack_details = {
        "attack_id": attack_info["attack_id"],
        "target_url": attack_info["target_url"],
        "attack_type": attack_info["attack_type"],
        "intensity": attack_info["intensity"],
        "duration": attack_info["duration"],
        "spoof_headers": attack_info["spoof_headers"],
        "custom_headers": attack_info["custom_headers"],
        "spoof_ip": attack_info["spoof_ip"],
        "packet_size": attack_info["packet_size"],
        "bot_count": attack_info["bot_count"]
    }
    return {"is_attacking": is_attacking, "attack_details": attack_details, "target_url": target_url}

@router.get("/ddos-bot/beacon/{bot_id}")
async def ddos_bot_beacon(bot_id: str):
    try:
        user_id = bot_id.split("_bot_")[0]
    except IndexError:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Bot not found")

    botnets = await redis_client.get(f"user_botnets:{user_id}")
    if not botnets:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Bot not found")

    bot_ids = json.loads(botnets)
    if not any(b["bot_id"] == bot_id for b in bot_ids):
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Bot not found")

    command = await redis_client.lpop(f"command_queue:{bot_id}")
    if command:
        command_data = json.loads(command)
        if command_data["user_id"] != user_id:
            return Response(status_code=status.HTTP_403_FORBIDDEN, content="Command does not belong to this user")
        return Response(content=command, status_code=status.HTTP_200_OK, media_type="application/json")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --------------------------------------------------------------------------------------------real bot
@router.get("/ddos/{token}")
async def get_session(request: Request, token):
    try:
        bot = await get_bot(token)
        bot_info = await get_bot_info(bot["id"])
        logs = await get_logs(bot["id"])
        if bot and bot_info:
            return templates.TemplateResponse('ddos_simulation/bot_c2.html', context={'request': request, 'bot': bot, 'bot_info': bot_info, 'logs': logs, 'active_page': 'ddos'})
        else:
            return templates.TemplateResponse('404.html', context={"request": request})
    except Exception as e:
        print(f"Exception: {str(e)}")
        return templates.TemplateResponse('404.html', context={"request": request})


@router.post("/ddos/{token}/command")
async def post_command(token: str, command: str = Form(...)):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            bot = await conn.fetchrow(
                "SELECT * FROM bots WHERE token = $1",
                token
            )
            if not bot or not command:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="error")
            bot_id = bot["id"]
            bot_info = await get_bot_info(bot_id)
            await conn.execute(
                """
                INSERT INTO commands (bot_id, command, directory)
                VALUES ($1, $2, $3)
                """,
                bot_id, command, bot_info["current_directory"]
            )
            return {"message": f"command '{command}' saved in database waiting for sending to bot {token}"}
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

