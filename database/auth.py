import bcrypt
from database.dbmain import get_connection_pool
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

async def authenticate_user(username, passwd):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            user = await conn.fetchrow('''
                SELECT * FROM c2_users WHERE username= $1
            ''', username)
            
            if not user or not verify_passwd(passwd, user["hashed_passwd"]):
                return False
            return True
        except Exception as e:
            return False

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

async def get_current_user(username):
    async with await (get_connection_pool()).acquire() as conn:
        try:
            user = await conn.fetchrow('''
                SELECT * FROM c2_users WHERE username= $1
            ''', username) # tuple
            return user
        except Exception as e:
            return None

async def add_user(username, passwd):
    # check empty input
    if not username or not passwd:
        return False
    
    async with (await get_connection_pool()).acquire() as conn:
        try:    
            hashed_passwd = hash_passwd(passwd)
            await conn.execute("""
                INSERT INTO c2_users (username, hashed_passwd) 
                VALUES ($1, $2)
                ON CONFLICT (username) DO NOTHING
            """, username, hashed_passwd) 
            return True
        except Exception as e:
            return False

