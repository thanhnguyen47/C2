import uvicorn

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse,JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database.dbmain import init_db
from database.auth import authenticate_user, generate_access_token, verify_access_token, get_current_user

# from starlette.middleware.base import BaseHTTPMiddleware
# import time
# import logging

app = FastAPI()
init_db()

# config static files and templates
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

# middleware: add secure headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)

    # response.headers["Content-Security-Policy"] = (
    #     "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    # )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "deny"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get('/')
async def root():
    return {'message': 'hello'}

@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    try:
        token = request.cookies.get("access_token")
        # check access_token
        if verify_access_token(token):
            return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    except:
        return templates.TemplateResponse('login.html', context={'request': request, 'error': None})

@app.post('/login', response_class=JSONResponse)
async def login(response: Response, username=Form(...), password = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response.set_cookie(
        key="access_token",
        value=generate_access_token(username),
        httponly=True,
        secure=False, # replace = True in practice (HTTPS)
        max_age=60*60*24*3,
        samesite="lax"
    )
    return {
        "message": "login successful"
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)