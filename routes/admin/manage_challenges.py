from fastapi import Request, APIRouter, Form, File, UploadFile, status, HTTPException
from fastapi.responses import Response, JSONResponse
from config import templates
from database.dbmain import get_connection_pool
import uuid
import aiofiles
import tarfile
import os
from docker.errors import DockerException, ImageLoadError
from database.admin.manage_challenges import get_web_topics, add_web_topic, edit_web_topic, delete_web_topic, get_web_topic_by_id, get_web_challenges_by_topic, delete_challenge_from_topic, get_challenge_details

router = APIRouter()

@router.get("/admin/topics")
async def get_topics(request: Request):
    topics = await get_web_topics()
    return templates.TemplateResponse("admin/manage_topics.html", context={"request": request, "active_page": "challenges", "topics": topics})

@router.post("/admin/topics/add")
async def add_topic(
    request: Request,
    title: str=Form(...),
    description: str=Form(None),
    short_description: str=Form(None),
    type: str=Form(..., regex="^(server-side|client-side|advanced)$"),
    icon: str=Form(..., regex="^bi-[a-z-]+$")
):
    if await add_web_topic(title, description, short_description, type, icon) is False:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "error adding topic, maybe slug conflict"})

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"details": "Topic added successfully"}
    )


@router.post("/admin/topics/edit")
async def edit_topic(
    request: Request,
    topic_id: int=Form(...),
    title: str=Form(...),
    description: str=Form(None),
    short_description: str=Form(None),
    type: str=Form(..., regex="^(server-side|client-side|advanced)$"),
    icon: str=Form(..., regex="^bi-[a-z-]+$")
):
    if await edit_web_topic(topic_id, title, description, short_description, type, icon) is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"details": "Error editing topic, maybe slug conflict or topic not found"}
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"details": "Topic updated successfully"}
    )

@router.post("/admin/topics/delete")
async def delete_topic(
    request: Request,
    topic_id: int=Form(...)
):
    if await delete_web_topic(topic_id) is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"details": "Error deleting topic, maybe topic not found or has challenges"}
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"details": "Topic deleted successfully"}
    )
    

@router.get("/admin/topics/{topic_id}")
async def topic_details(
    request: Request,
    topic_id: int
):
    topic = await get_web_topic_by_id(topic_id)
    if not topic:
        return templates.TemplateResponse("404.html", context={"request": request})
    challenges = await get_web_challenges_by_topic(topic_id)
    return templates.TemplateResponse("admin/manage_challenges.html", context={"request": request, "active_page": "challenges", "topic": topic, "challenges": challenges})

@router.post("/admin/topics/{topic_id}/challenges/add")
async def add_challenge(
    request: Request,
    topic_id: int,
    title: str = Form(...),
    level: str = Form(..., regex="^(apprentice|practitioner|expert)$"),
    description: str = Form(...),
    challenge_status: str = Form(..., regex="^(active|inactive)$"),
    lecture_link: str = Form(None),
    source_code_link: str = Form(None),
    correct_flag: str = Form(...),
    solution: str = Form(...),
    docker_image: UploadFile = Form(...)
):
    temp_file = f"/tmp/{uuid.uuid4()}.tar"
    docker_image_name = None
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Validate topic_id
            topic = await conn.fetchrow("SELECT * FROM web_topics WHERE topic_id = $1", topic_id)
            if not topic:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"details": "Topic not found"})

            # Prepare data
            level = level.upper()
            slug = slugify(title)
            if await conn.fetchval("SELECT slug FROM web_challenges WHERE slug = $1", slug):
                raise HTTPException(status_code=400, detail="A challenge with this title already exists (slug conflict)")

            # Validate correct_flag
            if not correct_flag.startswith("C2{") or len(correct_flag) > 100:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "Invalid flag format"})

            # Validate Docker image
            if not docker_image.filename.endswith(".tar"):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "Docker image must be a .tar file"})
            if docker_image.size > 500 * 1024 * 1024:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "Docker image size must be less than 500MB"})

            # Process Docker image
            try:
                async with aiofiles.open(temp_file, 'wb') as out_file:
                    while content := await docker_image.read(1024):
                        await out_file.write(content)
                with tarfile.open(temp_file, "r") as tar:
                    tar.getmembers()
                with open(temp_file, "rb") as tar_file:
                    docker_image_data = docker_client.images.load(tar_file.read())
                    if not docker_image_data or not docker_image_data[0]:
                        raise HTTPException(status_code=400, detail="Docker image is invalid")
                    image_id = docker_image_data[0].id  # Lấy ID của image
                    docker_image_name = f"challenge_{slug}:{uuid.uuid4()}"
                    # new tag for this image
                    docker_client.images.get(image_id).tag(docker_image_name)
                    # remove old tag
                    original_tags = docker_image_data[0].tags
                    if original_tags:
                        for tag in original_tags:
                            if tag != docker_image_name:
                                try:
                                    docker_client.images.remove(tag, force=True)
                                except Exception:
                                    pass 
            except (tarfile.TarError, DockerException, ImageLoadError) as e:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": f"Docker image is invalid: {str(e)}"})
            except Exception as e:
                return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"details": f"Error uploading docker image: {str(e)}"})
            finally:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass

            if not docker_image_name:
                return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"details": "Error uploading docker image"})

            # Insert data within transaction
            ports = "80"
            run_parameters = '{"cpu_quota": 30000, "cpu_period": 100000, "mem_limit": "100m"}'
            async with conn.transaction():
                result = await conn.fetchrow(
                    """
                    INSERT INTO web_challenges (topic_id, title, level, description, status, lecture_link, source_code_link, solution, slug)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING challenge_id
                    """,
                    topic_id, title, level, description, challenge_status, lecture_link, source_code_link, solution, slug
                )
                challenge_id = result["challenge_id"]
                await conn.execute(
                    """
                    INSERT INTO challenge_flags (challenge_id, correct_flag)
                    VALUES ($1, $2)
                    """,
                    challenge_id, correct_flag
                )
                await conn.execute(
                    """
                    INSERT INTO docker_images (challenge_id, image_name, ports, run_parameters)
                    VALUES ($1, $2, $3, $4)
                    """,
                    challenge_id, docker_image_name, ports, run_parameters
                )

            return JSONResponse(status_code=status.HTTP_201_CREATED, content={"details": "Challenge added successfully"})

    except HTTPException as e:
        # Rollback Docker image if loaded
        if docker_image_name:
            try:
                docker_client.images.remove(docker_image_name, force=True)
            except Exception:
                pass 
        return JSONResponse(status_code=e.status_code, content={"details": e.detail})
    except Exception as e:
        # Rollback Docker image if loaded
        if docker_image_name:
            try:
                docker_client.images.remove(docker_image_name, force=True)
            except Exception:
                pass
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"details": f"Error adding challenge: {str(e)}"})
    
@router.post("/admin/topics/{topic_id}/challenges/edit")
async def edit_challenge(
    request: Request,
    topic_id: int,
    challenge_id: int=Form(...),
    title: str = Form(...),
    level: str = Form(..., regex="^(apprentice|practitioner|expert)$"),
    description: str = Form(...),
    challenge_status: str = Form(..., regex="^(active|inactive)$"),
    lecture_link: str = Form(None),
    source_code_link: str = Form(None),
    correct_flag: str = Form(...),
    solution: str = Form(...),
    docker_image: UploadFile = Form(None)
):
    temp_file = None
    new_docker_image_name = None
    old_docker_image_name = None
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Validate topic_id
            topic = await conn.fetchrow("SELECT * FROM web_topics WHERE topic_id = $1", topic_id)
            if not topic:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"details": "Topic not found"})

            # Validate challenge_id
            challenge = await conn.fetchrow("SELECT * FROM web_challenges WHERE challenge_id = $1 AND topic_id = $2", challenge_id, topic_id)
            if not challenge:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"details": "Challenge not found"})

            # Prepare data
            level = level.upper()
            slug = slugify(title)
            if await conn.fetchval("SELECT slug FROM web_challenges WHERE slug = $1 AND challenge_id != $2", slug, challenge_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A challenge with this title already exists (slug conflict)")

            # Validate correct_flag
            if not correct_flag.startswith("C2{") or len(correct_flag) > 100:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "Invalid flag format"})

            old_docker_image = await conn.fetchrow(
                "SELECT image_name FROM docker_images WHERE challenge_id = $1",
                challenge_id
            )

            if old_docker_image:
                old_docker_image_name = old_docker_image["image_name"] 
            
            if docker_image is not None and docker_image.filename and docker_image.size > 0:
                temp_file = f"/tmp/{uuid.uuid4()}.tar" 
                # Validate Docker image
                if not docker_image.filename.endswith(".tar"):
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "Docker image must be a .tar file"})
                if docker_image.size > 500 * 1024 * 1024:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "Docker image size must be less than 500MB"})
                # Process Docker image
                try:
                    async with aiofiles.open(temp_file, 'wb') as out_file:
                        while content := await docker_image.read(1024):
                            await out_file.write(content)
                    with tarfile.open(temp_file, "r") as tar:
                        tar.getmembers()
                    with open(temp_file, "rb") as tar_file:
                        docker_image_data = docker_client.images.load(tar_file.read())
                        if not docker_image_data or not docker_image_data[0]:
                            raise HTTPException(status_code=400, detail="Docker image is invalid")
                        image_id = docker_image_data[0].id
                        new_docker_image_name = f"challenge_{slug}:{uuid.uuid4()}"
                        # new tag for this image
                        docker_client.images.get(image_id).tag(new_docker_image_name)
                        # remove old tag
                        original_tags = docker_image_data[0].tags
                        if original_tags:
                            for tag in original_tags:
                                if tag != new_docker_image_name:
                                    try:
                                        docker_client.images.remove(tag, force=True)
                                    except Exception:
                                        pass
                except (tarfile.TarError, DockerException, ImageLoadError) as e:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": f"Docker image is invalid: {str(e)}"})
                except Exception as e:
                    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"details": f"Error uploading docker image: {str(e)}"})
            
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE web_challenges
                    SET title = $1, level = $2, description = $3, status = $4, lecture_link = $5, source_code_link = $6, solution = $7, slug = $8
                    WHERE challenge_id = $9
                    """,
                    title, level, description, challenge_status, lecture_link, source_code_link, solution, slug, challenge_id
                )
                await conn.execute(
                    """
                    UPDATE challenge_flags
                    SET correct_flag = $1
                    WHERE challenge_id = $2
                    """,
                    correct_flag, challenge_id
                )
                if new_docker_image_name:
                    print(new_docker_image_name)
                    ports = "80"
                    run_parameters = '{"cpu_quota": 30000, "cpu_period": 100000, "mem_limit": "100m"}'
                    # await conn.execute(
                    #     """
                    #     UPDATE docker_images
                    #     SET image_name = $1, ports = $2, run_parameters = $3
                    #     WHERE challenge_id = $4
                    #     """,
                    #     new_docker_image_name, ports, run_parameters, challenge_id
                    # )
                    await conn.execute(
                        """
                        INSERT INTO docker_images (challenge_id, image_name, ports, run_parameters)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (challenge_id) DO UPDATE
                        SET image_name = $2, ports = $3, run_parameters = $4
                        """,
                        challenge_id, new_docker_image_name, ports, run_parameters
                    )
                    # delete old image
                    if old_docker_image_name:
                        try:
                            docker_client.images.remove(old_docker_image_name, force=True)
                        except Exception:
                            pass

        
            return JSONResponse(status_code=status.HTTP_200_OK, content={"details": "Challenge updated successfully"})
    except HTTPException as e:
        # Rollback Docker image if loaded
        if new_docker_image_name:
            try:
                docker_client.images.remove(new_docker_image_name, force=True)
            except Exception:
                pass
        return JSONResponse(status_code=e.status_code, content={"details": e.detail})
    except Exception as e:
        # Rollback Docker image if loaded
        if new_docker_image_name:
            try:
                docker_client.images.remove(new_docker_image_name, force=True)
            except Exception:
                pass
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"details": f"Error editing challenge: {str(e)}"})
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


"""
verify topic_id, challenge_id,
delete data in table web_challenges, challenge_flags, docker_images
delete docker image
rollback if error
"""
@router.post("/admin/topics/{topic_id}/challenges/delete")
async def delete_challenge(
    request: Request,
    topic_id: int,
    challenge_id: int=Form(...),
):
    if await delete_challenge_from_topic(challenge_id) is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"details": "Error deleting challenge, maybe challenge not found or has related data"}
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"details": "Challenge deleted successfully"})

@router.get("/admin/topics/{topic_id}/challenges/{challenge_id}")
async def challenge_details(
    request: Request,
    topic_id: int,
    challenge_id: int
):
    topic, challenge, docker_image = await get_challenge_details(challenge_id, topic_id)

    if not topic or not challenge or not docker_image:
        return templates.TemplateResponse("404.html", context={"request": request})
    
    return templates.TemplateResponse(
        "admin/manage_challenge_detail.html",
        context={
            "request": request,
            "active_page": "challenges",
            "topic": topic,
            "challenge": challenge,
            "docker_image": docker_image
        }
    )