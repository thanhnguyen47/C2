from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import RedirectResponse, Response, JSONResponse, HTMLResponse
from database.auth import verify_access_token, authenticate_user, generate_access_token, hash_passwd
from database.dbmain import get_connection_pool
from config import templates
from utils.tools import is_strong_password, is_valid_email, send_verification_email, send_reset_password_email
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
            secure=True,
            max_age=60*60*24*3,
            samesite="lax"
        )
        return {"message": "login successful"}
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An error occurred during login"}
        )

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

@router.get('/verify/{token}', response_class=HTMLResponse)
async def verify_email(token: str):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            pending_user = await conn.fetchrow(
                "SELECT * FROM pending_users WHERE verification_token = $1",
                token
            )
            if not pending_user:
                raise HTTPException(status_code=400, detail="Invalid verification token")

            if datetime.utcnow() > pending_user["token_expiry"]:
                await conn.execute("DELETE FROM pending_users WHERE verification_token = $1", token)
                raise HTTPException(status_code=400, detail="Verification token has expired")

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

        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verified</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light d-flex align-items-center justify-content-center" style="height: 100vh;">
            <div class="text-center p-4 bg-white shadow rounded">
                <h2 class="mb-3 text-success">Email Verified Successfully</h2>
                <p class="mb-4">Your email has been successfully verified. You can now log in to your account.</p>
                <a href="/login" class="btn btn-primary">Go to Login</a>
            </div>
        </body>
        </html>
        """, status_code=200)

    except HTTPException as e:
        return HTMLResponse(content=f"<h3>{e.detail}</h3>", status_code=e.status_code)
    except Exception as e:
        return HTMLResponse(content=f"<h3>Server Error: {str(e)}</h3>", status_code=500)


@router.post("/forgot-password")
async def forgot_password(email: str = Form(...)):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Kiểm tra email tồn tại
            user = await conn.fetchrow("SELECT id, email FROM c2_users WHERE email = $1", email)
            if not user:
                raise HTTPException(status_code=404, detail="Email does not exist")

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

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Reset password email sent successfully"}
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Server error: {str(e)}"})

@router.get('/reset-password/{token}', response_class=HTMLResponse)
async def reset_password_page(token: str):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Truy xuất thông tin từ bảng password_reset_tokens
            reset_record = await conn.fetchrow(
                """
                SELECT prt.*, cu.username 
                FROM password_reset_tokens prt
                JOIN c2_users cu ON prt.user_id = cu.id
                WHERE prt.token = $1
                """,
                token
            )
            if not reset_record:
                raise HTTPException(status_code=400, detail="Invalid or expired reset token")

            if datetime.utcnow() > reset_record["expiry"]:
                await conn.execute("DELETE FROM password_reset_tokens WHERE token = $1", token)
                raise HTTPException(status_code=400, detail="Reset token has expired")

            username = reset_record["username"]

        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reset Password</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light d-flex align-items-center justify-content-center" style="height: 100vh;">
            <div class="p-4 bg-white shadow rounded" style="min-width: 320px;">
                <h4 class="mb-3">Hello, <span class="text-primary">{username}</span></h4>
                <form method="POST" action="/reset-password/{token}">
                    <div class="mb-3">
                        <label for="new_password" class="form-label">New Password</label>
                        <input type="password" class="form-control" id="new_password" name="new_password" required>
                    </div>
                    <button type="submit" class="btn btn-success w-100">Reset Password</button>
                </form>
            </div>
        </body>
        </html>
        """, status_code=200)

    except HTTPException as e:
        return HTMLResponse(content=f"<h3>{e.detail}</h3>", status_code=e.status_code)
    except Exception as e:
        return HTMLResponse(content=f"<h3>Server Error: {str(e)}</h3>", status_code=500)

@router.post("/reset-password/{token}")
async def handle_reset_password(token: str, new_password: str = Form(...)):
    try:
        # Kiểm tra độ mạnh mật khẩu
        if not is_strong_password(new_password):
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters with upper, lower case and numbers."
            )

        async with (await get_connection_pool()).acquire() as conn:
            # Tìm token và lấy user_id
            reset_record = await conn.fetchrow(
                "SELECT * FROM password_reset_tokens WHERE token = $1",
                token
            )
            if not reset_record:
                raise HTTPException(status_code=400, detail="Invalid or expired token")

            if datetime.utcnow() > reset_record["expiry"]:
                await conn.execute("DELETE FROM password_reset_tokens WHERE token = $1", token)
                raise HTTPException(status_code=400, detail="Reset token expired")

            user_id = reset_record["user_id"]
            hashed_password = hash_passwd(new_password)

            # Cập nhật mật khẩu
            await conn.execute(
                "UPDATE c2_users SET hashed_passwd = $1 WHERE id = $2",
                hashed_password, user_id
            )

            # Xoá token
            await conn.execute(
                "DELETE FROM password_reset_tokens WHERE token = $1",
                token
            )

        return RedirectResponse(url="/login", status_code=302)

    except HTTPException as e:
        return HTMLResponse(content=f"<h3>{e.detail}</h3>", status_code=e.status_code)
    except Exception as e:
        return HTMLResponse(content=f"<h3>Server Error: {str(e)}</h3>", status_code=500)