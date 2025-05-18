from database.dbmain import get_connection_pool

async def get_user_info(user_id):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            user_info = await conn.fetchrow("""
                SELECT 
                    u.id, u.fullname, u.username, u.email,
                    i.date_of_birth, i.country, i.timezone, i.phone_number, i.website, i.avatar_url
                FROM c2_users u
                LEFT JOIN c2_user_info i ON u.id = i.user_id
                WHERE u.id = $1
            """, user_id)
            return user_info
        except Exception as e:
            print(f"Error fetching user info: {e}")
            return None

async def get_user_progress(user_id):
    # Ánh xạ type từ database sang tên hiển thị
    type_mapping = {
        "server-side": "Server Side",
        "client-side": "Client Side",
        "advanced": "Advanced"
    }
    progress = {}

    async with (await get_connection_pool()).acquire() as conn:
        for db_type, display_name in type_mapping.items():
            # Đếm tổng số challenge trong topic_type
            total_challenges = await conn.fetchval(
                """
                SELECT COUNT(wc.challenge_id)
                FROM web_challenges wc
                JOIN web_topics wt ON wc.topic_id = wt.topic_id
                WHERE wt.type = $1
                """,
                db_type
            )

            # count number of completed challenges in challenge typ 
            completed_challenges = await conn.fetchval(
                """
                SELECT COUNT(ucs.challenge_id)
                FROM user_challenge_status ucs
                JOIN web_challenges wc ON ucs.challenge_id = wc.challenge_id
                JOIN web_topics wt ON wc.topic_id = wt.topic_id
                WHERE ucs.user_id = $1 AND ucs.is_solved = true AND wt.type = $2
                """,
                user_id, db_type
            )

            # calc percentage
            if total_challenges and total_challenges > 0:
                percentage = (completed_challenges / total_challenges) * 100
            else:
                percentage = 0

            progress[display_name] = round(percentage)

    return progress
