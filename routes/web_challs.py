from fastapi import Request, APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from config import templates, docker_client, traefik_container, DOMAIN
from database.web_challs import get_all_web_topics, get_topic_details, get_web_lab_list, get_web_lab_details, get_docker_image, get_correct_flag
from database.dbmain import redis_client, get_connection_pool
import json
import time
import uuid

router = APIRouter()

@router.get("/web")
async def dashboard_page(request: Request):
    topics = await get_all_web_topics()
    server_side_topics = [topic for topic in topics if topic['type'] == 'server-side']
    client_side_topics = [topic for topic in topics if topic['type'] == 'client-side']
    advanced_topics = [topic for topic in topics if topic['type'] == 'advanced']
    return templates.TemplateResponse(
        '/web_challs/web_challs.html',
        context={
            'request': request,
            'active_page': 'web_challs',
            'server_side_topics': server_side_topics,
            'client_side_topics': client_side_topics,
            'advanced_topics': advanced_topics
        }
    )
@router.get("/web/{topic_slug}")
async def get_web_topic(request: Request, topic_slug):
    user_id = request.state.user["id"]
    topic_data = await get_topic_details(topic_slug)
    if not topic_data:
        return templates.TemplateResponse('404.html', context={"request": request})
    challenges = await get_web_lab_list(user_id, topic_data['topic_id'])
    return templates.TemplateResponse(
        '/web_challs/web_topic.html',
        context={
            'request': request,
            'active_page': 'web_challs',
            'topic': topic_data,
            'challenges': challenges
        }
    )

@router.get("/web/{topic_slug}/{lab_slug}")
async def get_web_topic(request: Request, topic_slug, lab_slug):
    user_id = request.state.user["id"]
    topic_data = await get_topic_details(topic_slug)
    if not topic_data:
        return templates.TemplateResponse('404.html', context={"request": request})
    challenge = await get_web_lab_details(user_id, lab_slug, topic_data['topic_id'])
    if not challenge:
        return templates.TemplateResponse('404.html', context={"request": request})
    return templates.TemplateResponse(
        '/web_challs/web_lab.html',
        context={
            'request': request,
            'active_page': 'web_challs',
            'topic': topic_data,
            'challenge': challenge
        }
    )

@router.post("/web/{topic_slug}/{lab_slug}/access")
async def access_lab(request: Request, topic_slug, lab_slug):
    user_id = request.state.user["id"]
    network_name = f"web_lab_user_{user_id}"

    existing_network = await redis_client.get(f"user:lab_net:{user_id}")
    existing_container = await redis_client.get(f"user:container:{user_id}")
    if existing_container or existing_network:
        return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "You already have a running challenge."}
        )
    
    topic_data = await get_topic_details(topic_slug)
    if not topic_data:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Topic not found"}
        )
    challenge = await get_web_lab_details(user_id, lab_slug, topic_data['topic_id'])
    if not challenge:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Challenge not found"}
        )

    docker_image = await get_docker_image(challenge['challenge_id'])
    if not docker_image:
        print(6)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "No docker image found for this challenge"}
        )
    
    # create isolating network 
    existing_networks = docker_client.networks.list(names=[network_name])
    if not existing_networks:
        docker_client.networks.create(
            name=network_name,
            driver="bridge",
            check_duplicate=True
        )
        
    subdomain = f"{uuid.uuid4()}.{DOMAIN}"
    # subdomain = f"user{user_id}-web.lab.local"
    #create new container
    try:
        container = docker_client.containers.run(
            docker_image['image_name'],
            detach=True,
            labels={
                "traefik.enable": "true",
                f"traefik.http.routers.user{user_id}.rule": f"Host(`{subdomain}`)",
                f"traefik.http.routers.user{user_id}.entrypoints": "web",
                f"traefik.http.services.user{user_id}.loadbalancer.server.port": docker_image['ports'],
                "user_id": str(user_id)
            },
            cpu_quota=30000,  # 30% CPU
            cpu_period=100000,
            mem_limit="100m",  # 100MB RAM
            network_mode=network_name,  # Mạng cô lập
        )

        network = docker_client.networks.get(network_name)
        try:
            network.connect(traefik_container)
        except Exception:
            pass

        container_data = {
            "container_id": container.id,
            "subdomain": subdomain,
            "challenge_id": challenge['challenge_id'],
            "expires_at": int(time.time() + 3600)
        }
        await redis_client.setex(
            f"user:container:{user_id}",
            3600,
            json.dumps(container_data)
        )
        print(7)
        return {
            "subdomain": subdomain,
            "message": "Container created successfully"
        }
    except Exception as e:
        print(8)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Failed to create container"}
        )

@router.post("/web/{topic_slug}/{lab_slug}/submit")
async def submit_flag(request: Request, topic_slug: str, lab_slug: str, body: dict):
    try:
        user_id = request.state.user["id"]

        # Kiểm tra container đang chạy trong Redis
        container_data_raw = await redis_client.get(f"user:container:{user_id}")
        if not container_data_raw:
            raise HTTPException(status_code=400, detail="No active lab found. Please access the lab first.")

        # Parse dữ liệu container từ Redis
        container_data = json.loads(container_data_raw.decode('utf-8'))
        current_time = int(time.time())
        if container_data["expires_at"] < current_time:
            # Nếu container đã hết hạn, xóa dữ liệu Redis và báo lỗi
            await redis_client.delete(f"user:container:{user_id}")
            raise HTTPException(status_code=400, detail="Lab session has expired. Please access the lab again.")

        # Lấy thông tin topic
        topic_data = await get_topic_details(topic_slug)
        if not topic_data:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Lấy thông tin challenge
        challenge = await get_web_lab_details(user_id, lab_slug, topic_data['topic_id'])
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        # Kiểm tra xem challenge hiện tại có trùng với challenge đang chạy trong container không
        running_challenge_id = int(container_data["challenge_id"])
        current_challenge_id = challenge["challenge_id"]
        if running_challenge_id != current_challenge_id:
            raise HTTPException(
                status_code=400,
                detail="You must access the correct challenge lab before submitting the flag."
            )

        # Kiểm tra flag
        submitted_flag = body.get("flag")
        if not submitted_flag:
            raise HTTPException(status_code=400, detail="Flag is required")

        correct_flag = await get_correct_flag(running_challenge_id)
        print(correct_flag)
        if submitted_flag != correct_flag:
            raise HTTPException(status_code=400, detail="Incorrect flag")

        # Cập nhật trạng thái solved trong database
        async with (await get_connection_pool()).acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_challenge_status (user_id, challenge_id, is_solved)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, challenge_id)
                DO UPDATE SET is_solved = $3
                """,
                user_id, challenge['challenge_id'], True
            )

        # Xóa container và dữ liệu Redis
        try:
            # Lấy container từ Docker
            container_id = container_data["container_id"]
            container = docker_client.containers.get(container_id)
            
            # Dừng và xóa container
            container.stop()
            container.remove()
            print(f"Container {container_id} has been stopped and removed.")
            
            # Xóa dữ liệu trong Redis
            await redis_client.delete(f"user:container:{user_id}")
            
            # Xóa network cô lập nếu cần
            network_name = f"web_lab_user_{user_id}"
            try:
                network = docker_client.networks.get(network_name)
                network.remove()
                print(f"Network {network_name} has been removed.")
            except Exception as network_err:
                print(f"Failed to remove network {network_name}: {network_err}")
                
        except Exception as cleanup_err:
            print(f"Error during cleanup: {cleanup_err}")

        return {"detail": "Flag correct! Challenge solved!"}
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An error occurred while processing your request."}
        )

@router.get("/all-labs")
async def get_all_labs(request: Request):
    user_id = request.state.user["id"]
    
    # Lấy tất cả challenges và trạng thái hoàn thành
    async with (await get_connection_pool()).acquire() as conn:
        challenges = await conn.fetch(
            """
            SELECT wc.challenge_id, wc.title, wc.level, wc.slug, wt.slug AS topic_slug,
                   ucs.is_solved
            FROM web_challenges wc
            JOIN web_topics wt ON wc.topic_id = wt.topic_id
            LEFT JOIN user_challenge_status ucs
                ON wc.challenge_id = ucs.challenge_id AND ucs.user_id = $1
            ORDER BY wc.level, wc.title
            """,
            user_id
        )

    return templates.TemplateResponse(
        'all_labs.html',
        context={
            'request': request,
            'active_page': 'all-labs',
            'challenges': challenges
        }
    )