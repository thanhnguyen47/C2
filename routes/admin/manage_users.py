from fastapi import Request, APIRouter, Form, File, UploadFile, HTTPException, status
from fastapi.responses import Response, JSONResponse
from config import templates
from utils.tools import validate_date_of_birth, validate_phone_number, validate_timezone, is_valid_email, is_strong_password
import re
from pathlib import Path
import os
from PIL import Image
from io import BytesIO
import uuid
from database.dbmain import get_connection_pool
from database.auth import hash_passwd
from datetime import date

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
UPLOAD_FOLDER = Path("uploads")

@router.get("/admin/users")
async def get_manage_users(request: Request):
    async with (await get_connection_pool()).acquire() as conn:
        users = await conn.fetch(
            """
            SELECT u.id, u.username, u.fullname, u.email, u.role, ui.date_of_birth, ui.phone_number, ui.country, ui.timezone, ui.website, ui.avatar_url
            FROM c2_users u
            LEFT JOIN c2_user_info ui ON u.id = ui.user_id
            ORDER BY u.id
            """
        )
    return templates.TemplateResponse("admin/manage_users.html", context={'request': request, 'active_page': 'users', 'users': users, "today": date.today().isoformat()})

@router.post("/admin/users/add")
async def create_new_user(request: Request,
    username: str = Form(...),
    fullname: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    date_of_birth: str = Form(None),
    phone_number: str=Form(None),
    country: str = Form(None),
    timezone: str = Form(None),
    website: str = Form(None),
    avatar: UploadFile=File(None)
):
    # validate first
    try:
        if not username.strip() or not fullname.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Required fields cannot be empty")
        # Kiểm tra định dạng email
        if not is_valid_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid email")

        # Kiểm tra độ mạnh mật khẩu
        if not is_strong_password(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường và số"
            )
        validated_dob = validate_date_of_birth(date_of_birth)
        validated_timezone = validate_timezone(timezone)
        validated_phone = validate_phone_number(phone_number)
        if website and not re.match(r"^(https?://)?[\w\-\.]+(\.[\w\-]+)+[/#?]?.*$", website):
                raise HTTPException(status_code=400, detail="Invalid website URL")
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)}
        )
    avatar_url=None
    # validate avatar
    if avatar:
        try:
            ext = os.path.splitext(avatar.filename)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS or avatar.content_type not in {"image/jpeg", "image/png"}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")
             # Check Content-Length header
            content_length = request.headers.get("Content-Length")
            if content_length:
                content_length = int(content_length)
                if content_length > MAX_FILE_SIZE:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large (max 2MB)")
            # Read file in chunks to verify size safely
            buffer = BytesIO()
            total_size = 0
            chunk_size = 8192  # 8KB chunks
            while True:
                chunk = await avatar.read(chunk_size)
                if not chunk:  # Hết file
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large (max 2MB)")
                buffer.write(chunk)

            # Move buffer to start for PIL
            buffer.seek(0)

            # Validate image
            try:
                image = Image.open(buffer)
                image.verify()  # Verify image integrity
                buffer.seek(0)  # Reset buffer for further processing
                image = Image.open(buffer)  # Re-open for processing
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

            width, height = image.size
            if width < 300 or height < 300:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be at least 300x300 pixels")

            # Resize
            image = image.convert("RGB")
            ratio = min(300 / width, 300 / height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Lưu ảnh
            filename = f"{uuid.uuid4().hex}.jpg"
            save_path = UPLOAD_FOLDER / filename
            image.save(save_path, format="JPEG", quality=85)
            avatar_url = f"/uploads/{filename}"
        except HTTPException as e:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})
        except Exception as e:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"Failed to process avatar: {str(e)}"})

    # check existing username or email
    async with (await get_connection_pool()).acquire() as conn:
        # Kiểm tra username và email trùng lặp trong c2_users
        existing_user = await conn.fetchrow(
            "SELECT username, email FROM c2_users WHERE username = $1 OR email = $2",
            username, email
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email is existed")

        # Kiểm tra username và email trùng lặp trong pending_users
        existing_pending = await conn.fetchrow(
            "SELECT username, email FROM pending_users WHERE username = $1 OR email = $2",
            username, email
        )
        if existing_pending:
            raise HTTPException(status_code=400, detail="Username or email is waiting for verifying")
        
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
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"detail": "Register successful"}
    )

@router.post("/admin/users/delete")
async def delete_user(request: Request, user_id: str=Form(...)):
    # validate user_id
    try:
        if not user_id.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty user id")
        user_id = int(user_id)
        if user_id <= 0:
            raise ValueError()
            
    except HTTPException as e:
        print('fetch here')
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except ValueError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "invalid user id"})
    
    # check self-delete
    uid = request.state.user["id"]
    if uid == user_id:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "not allow to self-delete"})
    
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
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail":"user not found"})
        
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
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"detail": "User deleted successfully"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Failed to delete user: {str(e)}"}
            )

@router.post("/admin/users/edit")
async def edit_user(
    request: Request,
    user_id: str = Form(...),
    username: str = Form(...),
    fullname: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(None),
    date_of_birth: str = Form(None),
    phone_number: str = Form(None),
    country: str = Form(None),
    timezone: str = Form(None),
    website: str = Form(None),
    avatar: UploadFile = File(None)
):
    # valid user_id
    try: 
        if not user_id.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID cannot be empty")
        user_id = int(user_id)
        if user_id <= 0:
            raise ValueError()
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except ValueError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid user id"})
    
    # validate required fields
    try:
        if not username.strip() or not fullname.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Required fields cannot be empty")
        if not is_valid_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email")
        if role not in ["admin", "user"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        if password and not is_strong_password(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters, including uppercase, lowercase, and number"
            )
        validated_dob = validate_date_of_birth(date_of_birth)
        validated_timezone = validate_timezone(timezone)
        validated_phone = validate_phone_number(phone_number)
        if website and not re.match(r"^(https?://)?[\w\-\.]+(\.[\w\-]+)+[/#?]?.*$", website):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid website URL")
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    
    avatar_url=None
    if avatar:
        try:
            ext = os.path.splitext(avatar.filename)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS or avatar.content_type not in {"image/jpeg", "image/png"}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")

            content_length = request.headers.get("Content-Length")
            if content_length:
                content_length = int(content_length)
                if content_length > MAX_FILE_SIZE:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large (max 2MB)")

            buffer = BytesIO()
            total_size = 0
            chunk_size = 8192
            while True:
                chunk = await avatar.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large (max 2MB)")
                buffer.write(chunk)

            buffer.seek(0)
            try:
                image = Image.open(buffer)
                image.verify()
                buffer.seek(0)
                image = Image.open(buffer)
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

            width, height = image.size
            if width < 300 or height < 300:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be at least 300x300 pixels")

            image = image.convert("RGB")
            ratio = min(300 / width, 300 / height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

            filename = f"{uuid.uuid4().hex}.jpg"
            save_path = UPLOAD_FOLDER / filename
            image.save(save_path, format="JPEG", quality=85)
            avatar_url = f"/uploads/{filename}"
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"Failed to process avatar: {str(e)}"})

    async with (await get_connection_pool()).acquire() as conn:
        existing_user = await conn.fetchrow(
            """
            SELECT id FROM c2_users 
            WHERE (username = $1 OR email = $2) AND id != $3
            """,
            username, email, user_id
        )
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email is existed")

        existing_pending = await conn.fetchrow(
            """
            SELECT id FROM pending_users 
            WHERE username = $1 OR email = $2
            """,
            username, email
        )
        if existing_pending:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email is waiting for verifying")

        # get old avatar to remove if upload new avatar
        current_user = await conn.fetchrow(
            """
            SELECT avatar_url FROM c2_user_info WHERE user_id = $1
            """,
            user_id
        )
        current_avatar_url = current_user["avatar_url"] if current_user else None

        if avatar_url and current_avatar_url:
            old_avatar_path = os.path.join(UPLOAD_FOLDER, current_avatar_url.split("/")[-1])
            if os.path.exists(old_avatar_path):
                try:
                    os.remove(old_avatar_path)
                except Exception as e:
                    pass

        # upadte user info
        try:
            hashed_passwd = hash_passwd(password) if password else None

            if hashed_passwd:
                await conn.execute(
                    """
                    UPDATE c2_users 
                    SET username = $1, fullname = $2, email = $3, role = $4, hashed_passwd = $5 
                    WHERE id = $6
                    """,
                    username, fullname, email, role, hashed_passwd, user_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE c2_users 
                    SET username = $1, fullname = $2, email = $3, role = $4 
                    WHERE id = $5
                    """,
                    username, fullname, email, role, user_id
                )

            # Cập nhật hoặc tạo c2_user_info
            await conn.execute(
                """
                INSERT INTO c2_user_info (user_id, date_of_birth, country, timezone, phone_number, website, avatar_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (user_id) DO UPDATE 
                SET date_of_birth = $2, country = $3, timezone = $4, phone_number = $5, website = $6, avatar_url = $7
                """,
                user_id, validated_dob, country, validated_timezone, validated_phone, website, avatar_url
            )        

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"detail": "User updated successfully"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Failed to update user: {str(e)}"}
            )

@router.get("/admin/users/{user_id}")
async def get_user_profile(request: Request, user_id: int):
    # valid user_id
    if user_id <= 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid user id"})
    
    async with (await get_connection_pool()).acquire() as conn:
        user_info = await conn.fetchrow(
            """
            SELECT 
                u.id, u.username, u.fullname, u.email, u.role,
                ui.date_of_birth, ui.country, ui.timezone, ui.phone_number, ui.website, ui.avatar_url
            FROM c2_users u
            LEFT JOIN c2_user_info ui ON u.id = ui.user_id
            WHERE u.id = $1
            """,
            user_id
        )
        if not user_info:
            return templates.TemplateResponse("404.html", context={"request": request})

    return templates.TemplateResponse("admin/manage_user_detail.html", context={"request": request, 'active_page': 'users', 'user_info': user_info})