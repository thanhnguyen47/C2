import bcrypt
from database.dbmain import get_connection_pool
from config import PEPPER, SECRET_KEY, ALGORITHM
from datetime import datetime, timedelta
import jwt
from utils.tools import send_verification_email, send_reset_password_email
import uuid

def hash_passwd(passwd):
    salt = bcrypt.gensalt()
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
        # if isinstance(access_token, str):
        #     access_token = access_token.encode()
        payload = jwt.decode(access_token, bytes.fromhex(SECRET_KEY), algorithms=ALGORITHM)
        username = payload.get("sub")   
        if username is None:
            return None
        return username
    except Exception as e:
        print("Exception when verify access token: ", e)
        return None

async def get_current_user(username):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            user = await conn.fetchrow('''
                SELECT * FROM c2_users WHERE username= $1
            ''', username) # tuple
            return user
        except Exception as e:
            return None
async def get_current_user_avatar(uid):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            avatar_url = await conn.fetchrow("""
                SELECT avatar_url FROM c2_user_info WHERE user_id= $1
            """, uid)
            avatar_url = avatar_url["avatar_url"] if avatar_url else None
            return avatar_url
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

async def register_user(fullname, username, email, password):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Kiểm tra username và email trùng lặp trong c2_users
            existing_user = await conn.fetchrow(
                "SELECT username, email FROM c2_users WHERE username = $1 OR email = $2",
                username, email
            )
            if existing_user:
                return False

            # Kiểm tra username và email trùng lặp trong pending_users
            existing_pending = await conn.fetchrow(
                "SELECT username, email FROM pending_users WHERE username = $1 OR email = $2",
                username, email
            )
            if existing_pending:
                return False

            # Tạo mã xác minh và thời hạn
            verification_token = str(uuid.uuid4())  # Tạo UUID ngẫu nhiên
            token_expiry = datetime.utcnow() + timedelta(hours=1)  # Hết hạn sau 1 giờ

            # Mã hóa mật khẩu
            hashed_passwd = hash_passwd(password)

            # Lưu vào pending_users
            await conn.execute(
                """
                INSERT INTO pending_users (fullname, username, email, hashed_passwd, verification_token, token_expiry)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                fullname, username, email, hashed_passwd, verification_token, token_expiry
            )

            # Gửi email xác minh
            await send_verification_email(email, verification_token)
            return True
    except Exception as e:
        return False
    
async def verify_account(token):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            pending_user = await conn.fetchrow(
                "SELECT * FROM pending_users WHERE verification_token = $1",
                token
            )
            if not pending_user:
                return False

            if datetime.utcnow() > pending_user["token_expiry"]:
                await conn.execute("DELETE FROM pending_users WHERE verification_token = $1", token)
                return False

            await conn.execute(
                """
                INSERT INTO c2_users (fullname, username, email, hashed_passwd, role)
                VALUES ($1, $2, $3, $4, $5)
                """,
                pending_user["fullname"],
                pending_user["username"],
                pending_user["email"],
                pending_user["hashed_passwd"],
                pending_user["role"]
            )

            await conn.execute("DELETE FROM pending_users WHERE verification_token = $1", token)
            return True
    except Exception as e:
        print("Error verifying account:", e)
        return False

async def send_reset_password_request(email):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Kiểm tra email tồn tại
            user = await conn.fetchrow("SELECT id, email FROM c2_users WHERE email = $1", email)
            if not user:
                return False
            
            # Tạo token và thời hạn
            token = str(uuid.uuid4())
            expiry = datetime.utcnow() + timedelta(minutes=30)

            # Xóa các token cũ (nếu cần)
            await conn.execute("DELETE FROM password_reset_tokens WHERE user_id = $1", user["id"])

            # Lưu token mới
            await conn.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expiry) VALUES ($1, $2, $3)",
                user["id"], token, expiry
            )

            # Gửi email reset
            await send_reset_password_email(email, token)
            return True
    except Exception as e:
        return False