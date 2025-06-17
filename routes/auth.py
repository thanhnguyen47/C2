from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import RedirectResponse, Response, JSONResponse, HTMLResponse
from database.auth import verify_access_token, authenticate_user, generate_access_token, hash_passwd, register_user, verify_account, send_reset_password_request
from database.dbmain import get_connection_pool
from config import templates
from utils.tools import is_strong_password, is_valid_email
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
    # Kiểm tra trường không trống
    if not all([fullname.strip(), username.strip(), email.strip(), password.strip()]):
        raise HTTPException(status_code=400, detail="All fields are required")

    # Kiểm tra định dạng email
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ")

    # Kiểm tra độ mạnh mật khẩu
    if not is_strong_password(password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters with upper, lower case and numbers."
        )

    if await register_user(fullname, username, email, password) is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Register failed."}
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Register successful. Please check your email to verify your account."}
    )

@router.get('/verify/{token}', response_class=HTMLResponse)
async def verify_email(token: str):
    
        if await verify_account(token) is False:
            return HTMLResponse(status_code=400, content="<h3>Invalid or expired verification token</h3>")
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

@router.post("/forgot-password")
async def forgot_password(email: str = Form(...)):
    if await send_reset_password_request(email) is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Failed to send reset password email. Please check if the email is registered."}
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Reset password email sent successfully"}
    )

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