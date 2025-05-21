from fastapi import Request, APIRouter, status, UploadFile, Form, File, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from PIL import Image
from pathlib import Path
from config import templates
from database.dashboard import get_user_info, get_user_progress
from database.dbmain import get_connection_pool
from io import BytesIO
import uuid
import os
from utils.tools import validate_date_of_birth, validate_phone_number, validate_timezone
import re

router = APIRouter()

UPLOAD_FOLDER = Path("uploads")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

@router.get("/dashboard")
async def dashboard_page(request: Request):
    user_id = request.state.user["id"]
    user_info = await get_user_info(user_id)
    progress = await get_user_progress(user_id)
    progress["DDoS"] = 50
    return templates.TemplateResponse(
        'dashboard.html',
        context={
            'request': request,
            'active_page': 'dashboard',
            'user_info': user_info,
            'progress': progress
        }
    )
@router.get("/profile")
async def get_profile(request: Request):
    user_id = request.state.user["id"]
    # user info
    user_info = await get_user_info(user_id)
    progress = await get_user_progress(user_id)
    return templates.TemplateResponse('profile.html', context={'request': request, 'active_page': 'dashboard', 'user_info': user_info, 'progress': progress})

@router.post("/profile/update")
async def update_profile(
    request: Request,
    fullname: str = Form(...),
    date_of_birth: str = Form(None),
    country: str = Form(None),
    timezone: str = Form(None),
    phone_number: str = Form(None),
    website: str = Form(None),
    avatar: UploadFile = File(None),
    delete_avatar: str = Form(None)
):
    user_id = request.state.user["id"]
    avatar_url = None

    # check input
    try:
        if not fullname.strip():
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        validated_dob = validate_date_of_birth(date_of_birth)
        validated_timezone = validate_timezone(timezone)
        validated_phone = validate_phone_number(phone_number)
        if website and not re.match(r"^(https?://)?[\w\-\.]+(\.[\w\-]+)+[/#?]?.*$", website):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid website URL")
    except Exception as e:
        print(3)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, 
            content={"detail": str(e)}
        )

    # resolve the image
    if avatar:
        try:
            ext = os.path.splitext(avatar.filename)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS or avatar.content_type not in {"image/jpeg", "image/png"}:
                raise HTTPException(status_code=400, detail="File type not allowed")

            # Check Content-Length header
            content_length = request.headers.get("Content-Length")
            if content_length:
                try:
                    content_length = int(content_length)
                    if content_length > MAX_FILE_SIZE:
                        raise HTTPException(status_code=400, detail="Image too large (max 2MB)")
                except ValueError:
                    pass  # Ignore invalid Content-Length

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
                    print(5)
                    raise HTTPException(status_code=400, detail="Image too large (max 2MB)")
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
                print(6)
                raise HTTPException(status_code=400, detail="Invalid image file")

            width, height = image.size
            if width < 300 or height < 300:
                print(7)
                raise HTTPException(status_code=400, detail="Image must be at least 300x300 pixels")

            # Resize
            image = image.convert("RGB")
            ratio = min(300 / width, 300 / height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

            filename = f"{uuid.uuid4().hex}.jpg"
            save_path = UPLOAD_FOLDER / filename
            try:
                image.save(save_path, format="JPEG", quality=85)
                avatar_url = f"/uploads/{filename}"
            except Exception as e:
                print(8)
                raise HTTPException(status_code=500, detail=f"Failed to save avatar: {str(e)}")

            # delete old image
            async with (await get_connection_pool()).acquire() as conn:
                old_avatar = await conn.fetchval(
                    "SELECT avatar_url FROM c2_user_info WHERE user_id = $1", user_id
                )
                if old_avatar and old_avatar != avatar_url:
                    old_path = UPLOAD_FOLDER / old_avatar.lstrip("/uploads/")
                    try:
                        if old_path.exists():
                            old_path.unlink()
                    except Exception:
                        pass  # Ignore deletion errors
        except Exception as e:
            print(9)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST, 
                content={"detail":str(e)}
            )

    elif delete_avatar == "true":
        try:
            async with (await get_connection_pool()).acquire() as conn:
                old_avatar = await conn.fetchval(
                    "SELECT avatar_url FROM c2_user_info WHERE user_id = $1", user_id
                )
                if old_avatar:
                    old_path = UPLOAD_FOLDER / old_avatar.lstrip("/uploads/")
                    try:
                        if old_path.exists():
                            old_path.unlink()
                    except Exception:
                        pass  # Ignore deletion errors
            avatar_url = None
        except Exception as e:
            print(10)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                content={"detail": str(e)}
            )

    # update into database
    try:
        async with (await get_connection_pool()).acquire() as conn:
            async with conn.transaction():
                # update c2_users
                await conn.execute(
                    """
                    UPDATE c2_users
                    SET fullname = $1
                    WHERE id = $2
                    """,
                    fullname, user_id
                )

                # insert into c2_user_info
                exists = await conn.fetchval(
                    "SELECT 1 FROM c2_user_info WHERE user_id = $1", user_id
                )
                if exists:
                    await conn.execute(
                        """
                        UPDATE c2_user_info
                        SET date_of_birth = $1,
                            country = $2,
                            timezone = $3,
                            phone_number = $4,
                            website = $5,
                            avatar_url = $6
                        WHERE user_id = $7
                        """,
                        validated_dob, country, validated_timezone, validated_phone, website, avatar_url, user_id
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO c2_user_info (user_id, date_of_birth, country, timezone, phone_number, website, avatar_url)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        user_id, validated_dob, country, validated_timezone, validated_phone, website, avatar_url
                    )

    except Exception as e:
        print(11)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            content={"detail": str(e)}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Profile updated successfully", "avatar_url": avatar_url}
    )

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=True,
        max_age=0,
        samesite="lax"
    )
    return response