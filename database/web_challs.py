from database.dbmain import get_connection_pool

async def get_all_web_topics():
    pool = await get_connection_pool()
    
    async with pool.acquire() as conn:
        # Truy vấn tất cả các chủ đề từ bảng web_topics
        topics = await conn.fetch("""
            SELECT topic_id, title, short_description, type, slug, icon
            FROM web_topics
        """)
        return topics
    
async def get_topic_details(slug):
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        # 1. Truy vấn thông tin chủ đề (web_topics) dựa trên slug
        topic_data = await conn.fetchrow("""
            SELECT topic_id, title, description, short_description, slug
            FROM web_topics
            WHERE slug = $1
        """, slug)
        return topic_data
    
async def get_web_lab_list(user_id, topic_id):
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        challenges = await conn.fetch("""
                SELECT 
                    wc.challenge_id,
                    wc.title,
                    wc.description,
                    wc.level,
                    wc.slug,
                    COALESCE(ucs.is_solved, FALSE) AS is_solved
                FROM web_challenges wc
                LEFT JOIN user_challenge_status ucs 
                    ON wc.challenge_id = ucs.challenge_id 
                    AND ucs.user_id = $1
                WHERE wc.topic_id = $2
                ORDER BY 
                    CASE 
                        WHEN wc.level = 'APPRENTICE' THEN 1
                        WHEN wc.level = 'PRACTITIONER' THEN 2
                        WHEN wc.level = 'EXPERT' THEN 3
                    END, wc.title
            """, user_id, topic_id)
        
        return challenges

async def get_web_lab_details(user_id, lab_slug, topic_id):
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        challenge = await conn.fetchrow("""
            SELECT 
                wc.challenge_id,
                wc.title,
                wc.description,
                wc.level,
                wc.solution,
                wc.slug,
                COALESCE(ucs.is_solved, FALSE) AS is_solved
            FROM web_challenges wc
            LEFT JOIN user_challenge_status ucs 
                ON wc.challenge_id = ucs.challenge_id 
                AND ucs.user_id = $1
            WHERE wc.slug = $2 AND wc.topic_id = $3
        """, user_id, lab_slug, topic_id)
        return challenge
    
async def get_docker_image(challenge_id):
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        image = await conn.fetchrow("""
            SELECT image_name, ports, run_parameters
            FROM docker_images
            WHERE challenge_id = $1
        """, challenge_id)
        return image

async def get_correct_flag(challenge_id):
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        flag = await conn.fetchrow("""
            SELECT correct_flag
            FROM challenge_flags
            WHERE challenge_id = $1
        """, challenge_id)
        return flag['correct_flag'] if flag else None