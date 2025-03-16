# import the library to run Postgres instance
import psycopg2

DB_NAME = 'c2_db'
DB_USER = 'c2_user'
DB_PASSWD = 'thanh'
DB_HOST = 'localhost'
DB_PORT = '5432'

try:
    # establish a new connection
    conn = psycopg2.connect(
        database=DB_NAME,
        user=DB_USER,
        password = DB_PASSWD,
        host=DB_HOST,
        port=DB_PORT
    )
    print('DB connected succesfully')
except:
    print('DB connected fail')
# using cursor function to execute postgres's commands
# cur = conn.cursor()

# # commit queries auto
# conn.set_session(autocommit=True)

