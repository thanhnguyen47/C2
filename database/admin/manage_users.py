from database.dbmain import get_connection_pool
from database.auth import hash_passwd
from pathlib import Path
import os


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
UPLOAD_FOLDER = Path("uploads")

async def get_users():
    try:
        async with (await get_connection_pool()).acquire() as conn:
            users = await conn.fetch(
                """
                SELECT u.id, u.username, u.fullname, u.email, u.role, ui.date_of_birth, ui.phone_number, ui.country, ui.timezone, ui.website, ui.avatar_url
                FROM c2_users u
                LEFT JOIN c2_user_info ui ON u.id = ui.user_id
                ORDER BY u.id
                """
            )
            return users
    except Exception as e:
        print(f"Error fetching users: {e}")
        return None
    
async def add_user(username, password, fullname, email, role, validated_dob=None, validated_phone=None, country=None, validated_timezone=None, website=None, avatar_url=None):
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
            
            # Mã hóa mật khẩu
            hashed_passwd = hash_passwd(password)
            uid = await conn.fetchrow(
                """
                INSERT INTO c2_users (fullname, username, email, hashed_passwd, role)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
                """,
                fullname, username, email, hashed_passwd, role
            )
            uid = uid["id"]
            await conn.execute(
                """
                INSERT INTO c2_user_info (user_id, date_of_birth, country, timezone, phone_number, website, avatar_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                uid, validated_dob, country, validated_timezone, validated_phone, website, avatar_url
            )
            return True
    except Exception as e:
        return False
    
async def delete_user(user_id):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # check existing user
            user = await conn.fetchrow(
                """
                SELECT c2_users.id, c2_users.username, c2_user_info.avatar_url
                FROM c2_users
                LEFT JOIN c2_user_info ON c2_users.id = c2_user_info.user_id
                WHERE c2_users.id=$1
                """,
                user_id
            )
            if not user:
                return False
            
            # delete avatar if there is
            avatar_url =user["avatar_url"]
            if avatar_url:
                avatar_path = os.path.join(UPLOAD_FOLDER, avatar_url.split("/")[-1])
                if os.path.exists(avatar_path):
                    try:
                        os.remove(avatar_path)
                    except Exception as e:
                        pass
            
            # after all, delete user on database in table c2_users, relevent tables will be automated deleting by ON DELETE CASCADE
            try:
                await conn.execute("DELETE FROM c2_users WHERE id = $1", user_id)
                return True
            except Exception as e:
                return False
    except Exception as e:
        return False