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
    ALTER TABLE commands
    DROP CONSTRAINT fk_commands_bot_id;
    """)

    cur.execute("""
    ALTER TABLE logs
    DROP CONSTRAINT fk_logs_bot_id;
    """)

    cur.execute("""
    ALTER TABLE logs
    DROP CONSTRAINT fk_logs_command_id;
    """)

    cur.execute("""
    ALTER TABLE bot_info
    DROP CONSTRAINT fk_bot_info_bots_id;
    """)
    cur.execute("DROP TABLE IF EXISTS c2_users;")
    cur.execute("DROP TABLE IF EXISTS bots;")
    cur.execute("DROP TABLE IF EXISTS bot_info;")
    cur.execute("DROP TABLE IF EXISTS commands;")
    cur.execute("DROP TABLE IF EXISTS logs;")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS c2_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        hashed_passwd VARCHAR(255) NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bots (
        id SERIAL PRIMARY KEY,
        token VARCHAR(50) UNIQUE,
        status VARCHAR(10) NOT NULL DEFAULT 'offline'
    )
    """)

    # ip???
    cur.execute("""
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
        disk VARCHAR(256)
    )    
""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS commands(
        id SERIAL PRIMARY KEY,
        bot_id INTEGER NOT NULL,
        command TEXT NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'pending',
        issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id SERIAL PRIMARY KEY,
        bot_id INTEGER NOT NULL,
        command_id INTEGER NOT NULL,
        result TEXT,
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    ALTER TABLE commands
    ADD CONSTRAINT fk_commands_bot_id
    FOREIGN KEY (bot_id) REFERENCES bots(id);
    """)

    cur.execute("""
    ALTER TABLE logs
    ADD CONSTRAINT fk_logs_bot_id
    FOREIGN KEY (bot_id) REFERENCES bots(id);
    """)

    cur.execute("""
    ALTER TABLE logs
    ADD CONSTRAINT fk_logs_command_id
    FOREIGN KEY (command_id) REFERENCES commands(id);
    """)

    cur.execute("""
    ALTER TABLE bot_info
    ADD CONSTRAINT fk_bot_info_bots_id
    FOREIGN KEY (bot_id) REFERENCES bots(id);
    """)
    conn.commit()
    connection_pool.putconn(conn)
