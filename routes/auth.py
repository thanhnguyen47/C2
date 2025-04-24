from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import RedirectResponse, Response, JSONResponse
from database.auth import verify_access_token, authenticate_user, generate_access_token, hash_passwd
from database.dbmain import get_connection_pool
from config import templates
from utils.tools import is_strong_password, is_valid_email, send_verification_email
import uuid
from datetime import datetime, timedelta

router = APIRouter()

@router.get('/')
async def root():
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

@router.get('/login')
async def login_page(request: Request):
    token = request.cookies.get("access_token")
    # check access_token
    if verify_access_token(token):
        return RedirectResponse("/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse('login.html', context={'request': request, 'error': None})

@router.post('/login')
async def login(response: Response, username=Form(...), password=Form(...)):
    try:
        user = await authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        response.set_cookie(
            key="access_token",
            value=generate_access_token(username),
            httponly=True,
            secure=False, # replace = True in practice (HTTPS)
            max_age=60*60*24*3,
            samesite="lax"
        )
        return {"message": "login successful"}
    except Exception as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})

@router.post('/register')
async def register(
    fullname: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        # Kiểm tra trường không trống
        if not all([fullname.strip(), username.strip(), email.strip(), password.strip()]):
            raise HTTPException(status_code=400, detail="Tất cả các trường không được để trống")

        # Kiểm tra định dạng email
        if not is_valid_email(email):
            raise HTTPException(status_code=400, detail="Email không hợp lệ")

        # Kiểm tra độ mạnh mật khẩu
        if not is_strong_password(password):
            raise HTTPException(
                status_code=400,
                detail="Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường và số"
            )

        async with (await get_connection_pool()).acquire() as conn:
            # Kiểm tra username và email trùng lặp trong c2_users
            existing_user = await conn.fetchrow(
                "SELECT username, email FROM c2_users WHERE username = $1 OR email = $2",
                username, email
            )
            if existing_user:
                raise HTTPException(status_code=400, detail="Username hoặc email đã tồn tại")

            # Kiểm tra username và email trùng lặp trong pending_users
            existing_pending = await conn.fetchrow(
                "SELECT username, email FROM pending_users WHERE username = $1 OR email = $2",
                username, email
            )
            if existing_pending:
                raise HTTPException(status_code=400, detail="Username hoặc email đang chờ xác minh")

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

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Đăng ký thành công, vui lòng kiểm tra email để xác minh"}
        )
    except HTTPException as e:
        print(str(e))
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Lỗi server: {str(e)}"})

@router.get('/verify')
async def verify_email(token: str):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Tìm bản ghi trong pending_users với token
            pending_user = await conn.fetchrow(
                "SELECT * FROM pending_users WHERE verification_token = $1",
                token
            )
            if not pending_user:
                raise HTTPException(status_code=400, detail="Mã xác minh không hợp lệ")

            # Kiểm tra token còn hạn
            if datetime.utcnow() > pending_user["token_expiry"]:
                await conn.execute("DELETE FROM pending_users WHERE verification_token = $1", token)
                raise HTTPException(status_code=400, detail="Mã xác minh đã hết hạn")

            # Chuyển dữ liệu sang c2_users
            await conn.execute(
                """
                INSERT INTO c2_users (fullname, username, email, hashed_passwd, is_admin)
                VALUES ($1, $2, $3, $4, $5)
                """,
                pending_user["fullname"],
                pending_user["username"],
                pending_user["email"],
                pending_user["hashed_passwd"],
                pending_user["is_admin"]
            )

            # Xóa bản ghi trong pending_users
            await conn.execute("DELETE FROM pending_users WHERE verification_token = $1", token)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Xác minh email thành công, vui lòng đăng nhập"}
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Lỗi server: {str(e)}"})
