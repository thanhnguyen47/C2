import bcrypt
from database.dbmain import connection_pool
from config import PEPPER, SECRET_KEY, ALGORITHM
from datetime import datetime, timedelta
import jwt

def hash_passwd(passwd):
    salt = bcrypt.gensalt(rounds=15)
    passwd_with_pepper = passwd.encode() + bytes.fromhex(PEPPER)
    hashed_passwd = bcrypt.hashpw(passwd_with_pepper, salt)
    return hashed_passwd.decode()

def verify_passwd(passwd, hashed_passwd):
    passwd_with_pepper = passwd.encode() + bytes.fromhex(PEPPER)
    return bcrypt.checkpw(passwd_with_pepper, hashed_passwd.encode())

def authenticate_user(username, passwd):
    conn = connection_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM c2_users WHERE username= %s
    ''',(username,)) # tuple
        
        user = cur.fetchone()
        if not user or not verify_passwd(passwd, user[2]):
            return False
        return True
    except Exception as e:
        return False
    finally:
        cur.close()
        connection_pool.putconn(conn)

def generate_access_token(username):
    expire = datetime.utcnow() + timedelta(seconds=60*60*24*3) # expired after 3 days
    to_encode = {
        "sub": username, "exp": expire 
    }
    encoded_jwt = jwt.encode(to_encode, bytes.fromhex(SECRET_KEY), algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(access_token):
    try:
        payload = jwt.decode(access_token, bytes.fromhex(SECRET_KEY), algorithms=ALGORITHM)
        username = payload.get("sub")
        if username is None:
            return False
        return True
    except jwt.ExpiredSignatureError:
        return False

def get_current_user(username):
    conn = connection_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM c2_users WHERE username= %s
    ''',(username,)) # tuple
        
        user = cur.fetchone()
        return user
    except Exception as e:
        return None
    finally:
        cur.close()
        connection_pool.putconn(conn)

def add_user(username, passwd):
    # check empty input
    if not username or not passwd:
        return False
    
    conn = connection_pool.getconn()
    try:
        cur = conn.cursor()
        # check existed username
        cur.execute('''
            SELECT * FROM c2_users WHERE username= %s
    ''',(username,))
        user = cur.fetchone()
        if user:
            return False
            
        hashed_passwd = hash_passwd(passwd)
        cur.execute('''
            INSERT INTO c2_users (username, hashed_passwd) VALUES (%s,  %s)
    ''', (username, hashed_passwd)) 
        conn.commit()
        return True
    except Exception as e:
        conn.rollback() # restore if error
        return False
    finally:
        cur.close()
        connection_pool.putconn(conn)

