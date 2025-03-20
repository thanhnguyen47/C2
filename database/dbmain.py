# import the library to run Postgres instance
# import psycopg2
from psycopg2 import pool #https://github.com/psycopg/psycopg2/issues/582
from config import DB_NAME, DB_USER, DB_PASSWD, DB_HOST, DB_PORT
# establish a new connection
connection_pool = pool.SimpleConnectionPool(
    1, 20,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWD,
    host=DB_HOST,
    port=DB_PORT
)


def init_db():
    conn = connection_pool.getconn()
    # using cursor function to execute postgres's commands
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS c2_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        hashed_passwd VARCHAR(255) NOT NULL
    )
    """)
    conn.commit()
    connection_pool.putconn(conn)
