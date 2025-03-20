from fastapi import APIRouter, Request, Response, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from database.auth import verify_access_token, authenticate_user, generate_access_token
from config import templates

auth_router = APIRouter()

@auth_router.get('/')
async def root():
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

@auth_router.get('/login')
async def login_page(request: Request):
    try:
        token = request.cookies.get("access_token")
        # check access_token
        if verify_access_token(token):
            return RedirectResponse("/dashboard", status_code=status.HTTP_302_FOUND)
    except:
        return templates.TemplateResponse('login.html', context={'request': request, 'error': None})

@auth_router.post('/login')
async def login(response: Response, username=Form(...), password=Form(...)):
    user = authenticate_user(username, password)
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