from database.dbmain import get_connection_pool

async def get_user_info(user_id):
    async with (await get_connection_pool()).acquire() as conn:
        user_id=int(user_id)
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
