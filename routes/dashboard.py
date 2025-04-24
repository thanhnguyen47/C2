from fastapi import Request, APIRouter, status, UploadFile, Form, File, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from PIL import Image
from pathlib import Path
from config import templates
from database.dashboard import get_user_info
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
    return templates.TemplateResponse('dashboard.html', context={'request': request, 'active_page': 'dashboard'})  

@router.get("/profile")
async def get_profile(request: Request):
    user_id = str(request.state.user["id"])
    # user info
    user_info = await get_user_info(user_id)
    return templates.TemplateResponse('profile.html', context={'request': request, 'active_page': 'dashboard', 'user_info': user_info})

@router.post("/profile/update")
async def update_profile(
    request: Request,
    fullname: str = Form(...),
    date_of_birth: str = Form(...),
    country: str = Form(...),
    timezone: str = Form(...),
    phone_number: str = Form(...),
    website: str = Form(...),
    avatar: UploadFile = File(None),
    delete_avatar: str = Form(None)
):
    user_id = request.state.user["id"]
    avatar_url = None

    # check input
    if not fullname.strip():
        raise HTTPException(status_code=400, detail="Full name cannot be empty")
    validated_dob = validate_date_of_birth(date_of_birth)
    validated_timezone = validate_timezone(timezone)
    validated_phone = validate_phone_number(phone_number)
    if website and not re.match(r"^(https?://)?[\w\-\.]+(\.[\w\-]+)+[/#?]?.*$", website):
        raise HTTPException(status_code=400, detail="Invalid website URL")

    # resolve the image
    if avatar:
        ext = os.path.splitext(avatar.filename)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS or avatar.content_type not in {"image/jpeg", "image/png"}:
            raise HTTPException(status_code=400, detail="File type not allowed")

        await avatar.seek(0, os.SEEK_END)
        size = avatar.file.tell()
        await avatar.seek(0)
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Image too large (max 2MB)")

        try:
            content = await avatar.read()
            image = Image.open(BytesIO(content))
            width, height = image.size
            if width < 300 or height < 300:
                raise HTTPException(status_code=400, detail="Image must be at least 300x300 pixels")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Resize
        image = image.convert("RGB")
        ratio = min(300 / width, 300 / height)
        new_size = (int(width * ratio), int(height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

        filename = f"{uuid.uuid4().hex}.jpg"
        save_path = UPLOAD_FOLDER / filename
        image.save(save_path, format="JPEG", quality=85)
        avatar_url = f"/uploads/{filename}"

        # delete old image
        async with (await get_connection_pool()).acquire() as conn:
            old_avatar = await conn.fetchval(
                "SELECT avatar_url FROM c2_user_info WHERE user_id = $1", user_id
            )
            if old_avatar and old_avatar != avatar_url:
                old_path = UPLOAD_FOLDER / old_avatar.lstrip("/uploads/")
                if old_path.exists():
                    old_path.unlink()
    elif delete_avatar == "true":
        # delete avatar, set avatar_url by NULL
        async with (await get_connection_pool()).acquire() as conn:
            old_avatar = await conn.fetchval(
                "SELECT avatar_url FROM c2_user_info WHERE user_id = $1", user_id
            )
            if old_avatar:
                old_path = UPLOAD_FOLDER / old_avatar.lstrip("/uploads/")
                if old_path.exists():
                    old_path.unlink()
        avatar_url = None

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
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

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
        secure=False, # replace = True in practice (HTTPS)
        max_age=0,
        samesite="lax"
    )
    return response