from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import RedirectResponse, Response, JSONResponse
from database.auth import verify_access_token, authenticate_user, generate_access_token, hash_passwd
from database.dbmain import get_connection_pool
from config import templates

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

@router.post('/register')
async def register(username=Form(...), password=Form(...)):
    try:
        async with (await get_connection_pool()).acquire() as conn:
            # Check if username already exists
            existing_user = await conn.fetchrow("SELECT * FROM c2_users WHERE username = $1", username)
            if existing_user:
                raise

            hashed_passwd = hash_passwd(password)
            print(username, password, hashed_passwd)
            # Insert new user
            await conn.execute("INSERT INTO c2_users (username, hashed_passwd) VALUES ($1, $2)", username, hashed_passwd)

        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "User registered successfully"})
    except Exception:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Registration failed"})


