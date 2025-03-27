from database.dbmain import get_connection_pool

async def create_new_bot(token: str, username, hostname, ip, os, cpu, gpu, ram, disk):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            # start transaction
            async with conn.transaction():
                # insert new bot using ON CONFLICT to handle duplicate tokens
                bot = await conn.fetchrow("""
                INSERT INTO bots (token, status)
                VALUES ($1, $2)
                ON CONFLICT (token) DO NOTHING
                RETURNING id
                """, token, "online")

                if not bot:
                    raise Exception("failed to insert or retrieve bot")
                
                bot_id = bot["id"]

                # insert bot info
                await conn.execute("""
                INSERT INTO bot_info (bot_id, username, hostname, ip, os, cpu, gpu, ram, disk)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, bot_id, username, hostname, ip, os, cpu, gpu, ram, disk)

            return True
        except Exception as e:
            print(f"Exception: {str(e)}")
            return False

# async def get_bot(token: str):
#     async with connection_pool.acquire() as conn:
#         try:
#             bot = conn.fetchrow("""
#             SELECT * FROM bots WHERE token = %s
#             """, (token,))
#             if not bot:
#                 return None
#             bot_id = bot["id"]
#         except Exception as e:
#             pass