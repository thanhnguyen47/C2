from database.dbmain import get_connection_pool
from slugify import slugify
from config import docker_client

async def get_web_topics():
    try:
        async with (await get_connection_pool()).acquire() as conn:
            topics = await conn.fetch(
                """
                SELECT * from web_topics
                """
            )
            return topics
    except Exception as e:
        print(f"Error fetching web topics: {e}")
        return None


async def add_web_topic(title, description, short_description, type, icon):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            slug = slugify(title)
            # check if slug exists
            existing_slug = await conn.fetchval("SELECT slug FROM web_challenges WHERE slug = $1", slug)
            if existing_slug:
                return False
            await conn.execute(
                """
                INSERT INTO web_topics (title, description, short_description, slug, type, icon)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                title,
                description,
                short_description,
                slug,
                type,
                icon
            )
            return True
    except Exception as e:
        return False
    
async def edit_web_topic(topic_id, title, description, short_description, type, icon):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            slug = slugify(title)
            # check if slug exists
            existing_slug = await conn.fetchval("SELECT slug FROM web_challenges WHERE slug = $1", slug)
            if existing_slug:
                return False
            
            exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM web_topics WHERE topic_id = $1)",
                    topic_id
                )
            if not exists:
                return False
            # update the topic
            await conn.execute(
                """
                UPDATE web_topics
                SET title = $1, description = $2, short_description = $3, slug = $4, type = $5, icon = $6
                WHERE topic_id = $7
                """,
                title,
                description,
                short_description,
                slug,
                type,
                icon,
                topic_id
            )
            return True
    except Exception as e:
        print(f"Error editing web topic: {e}")
        return False

async def delete_web_topic(topic_id):
    try:
        # cần thêm logic kiểm tra xem topic còn có challenge nào không nữa!!!
        async with (await get_connection_pool()).acquire() as conn:
            exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM web_topics WHERE topic_id = $1)",
                    topic_id
                )
            if not exists:
                return False

            # Kiểm tra xem topic có challenge nào không
            has_challenges = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM web_challenges WHERE topic_id = $1)",
                topic_id
            )
            if has_challenges:
                return False
            
            # delete the topic
            await conn.execute(
                """
                DELETE FROM web_topics
                WHERE topic_id = $1
                """,
                topic_id
            )
            return True
    except Exception as e:
        return False

async def get_web_topic_by_id(topic_id):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            topic = await conn.fetchrow(
                """
                SELECT * FROM web_topics WHERE topic_id = $1
                """,
                topic_id
            )
            return topic
    except Exception as e:
        print(f"Error fetching web topic by ID: {e}")
        return None

async def get_web_challenges_by_topic(topic_id):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            challenges = await conn.fetch(
                """
                SELECT * from web_challenges LEFT JOIN challenge_flags ON web_challenges.challenge_id = challenge_flags.challenge_id
                WHERE topic_id = $1
                """,
                topic_id
            )
            return challenges
    except Exception as e:
        print(f"Error fetching web challenges by topic: {e}")
        return None
    
async def add_challenge_to_topic(topic_id, title, level, description, challenge_status, lecture_link, source_code_link, correct_flag, solution, docker_image):
    pass

async def edit_challenge_in_topic(challenge_id, topic_id, title, level, description, challenge_status, lecture_link, source_code_link, correct_flag, solution, docker_image):
    pass

async def delete_challenge_from_topic(challenge_id):
    docker_image_name = None
    try:
        async with (await get_connection_pool()).acquire() as conn:
            #validate topic_id
            topic = await conn.fetchrow("SELECT * FROM web_topics WHERE topic_id = $1 ", topic_id)
            if not topic:
                return False
            #validate challenge_id
            challenge = await conn.fetchrow("SELECT * FROM web_challenges WHERE challenge_id = $1 AND topic_id = $2", challenge_id, topic_id)
            if not challenge:
                return False
            # get docker image info to delete 
            docker_image = await conn.fetchrow(
                "SELECT image_name FROM docker_images WHERE challenge_id = $1",
                challenge_id
            )
            if docker_image:
                docker_image_name = docker_image["image_name"]
                try:
                    docker_client.images.remove(docker_image_name, force=True)
                except Exception:
                    return False

            # delete 
            async with conn.transaction():
                # relevant data will be deleted automatically due to ON DELETE CASCADE
                await conn.execute(
                    "DELETE FROM web_challenges WHERE challenge_id = $1", challenge_id
                )
            return True
    except Exception as e:
        return False


async def get_challenge_details(challenge_id, topic_id):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Lấy thông tin topic
            topic = await conn.fetchrow(
                """
                SELECT * FROM web_topics
                WHERE topic_id = $1
                """,
                topic_id
            )
    
            # Lấy thông tin challenge và join với challenge_flags và docker_images
            challenge = await conn.fetchrow(
                """
                SELECT 
                    wc.*,
                    cf.correct_flag,
                    di.image_name,
                    di.ports,
                    di.run_parameters,
                    di.created_at AS docker_created_at
                FROM web_challenges wc
                LEFT JOIN challenge_flags cf ON wc.challenge_id = cf.challenge_id
                LEFT JOIN docker_images di ON wc.challenge_id = di.challenge_id
                WHERE wc.topic_id = $1 AND wc.challenge_id = $2
                """,
                topic_id, challenge_id
            )

            # Chuẩn bị dữ liệu docker_image (nếu có)
            docker_image = None
            if challenge.get("image_name"):
                docker_image = {
                    "image_name": challenge["image_name"] or "N/A",
                    "ports": challenge["ports"] or "N/A",
                    "run_parameters": challenge["run_parameters"] or "N/A",
                    "created_at": challenge["docker_created_at"] or "N/A"
                }
            return topic, challenge, docker_image
    except Exception as e:
        return None, None, None