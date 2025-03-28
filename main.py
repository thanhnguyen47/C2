import uvicorn

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException


from middlewares import check_access_token, add_security_headers
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.bot import router as bot_router
from routes.session import router as session_router
from database.dbmain import create_db_pool, close_db_pool
from config import templates
# from database.auth import add_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup logic
    print("Starting app initialization...")
    await create_db_pool()
    # await init_db()
    # await add_user("wiener", "peter")

    yield # this is where the app will run

    # shutdown logic 
    await close_db_pool()
    print("App shutdown completed.")


app = FastAPI(lifespan=lifespan)

# config static files
app.mount('/static', StaticFiles(directory='static'), name='static')

# add middlewares
app.middleware("http")(check_access_token)
app.middleware("http")(add_security_headers)

app.include_router(auth_router)
app.include_router(dashboard_router)  
app.include_router(bot_router)
app.include_router(session_router)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, e: HTTPException):
    if e.status_code == 404:
        return templates.TemplateResponse("404.html", context={"request": request})

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8000)