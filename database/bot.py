from database.dbmain import connection_pool
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
from psycopg2.extras import RealDictCursor

def create_new_bot(token: str, username, hostname, ip, os, cpu, gpu, ram, disk):
    conn = connection_pool.getconn()
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
        cur = conn.cursor(cursor_factory=RealDictCursor) # fetch will return a dict

        # start transaction
        # first, check if token is existed
        cur.execute("SELECT id from bots WHERE token = %s FOR UPDATE", (token, ))
        bot = cur.fetchone()
        if bot:
            raise Exception("bot id is already existed")
        
        # if not existed
        cur.execute("""
        INSERT INTO bots (token, status)
        VALUES (%s, %s)
        RETURNING id
        """, (token, "online"))
        bot = cur.fetchone()

        if not bot:
            raise Exception("failed to insert or retrieve bot")
        
        bot_id = bot["id"]

        cur.execute("""
        INSERT INTO bot_info (bot_id, username, hostname, ip, os, cpu, gpu, ram, disk)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (bot_id, username, hostname, ip, os, cpu, gpu, ram, disk))

        conn.commit()
        return True
    except Exception as e:
        print(f"Exception: {e}")
        conn.rollback()
        return False
    finally:
        connection_pool.putconn(conn)
