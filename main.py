import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from middlewares import check_access_token, add_security_headers
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.bot import router as bot_router
from routes.session import router as session_router
from database.dbmain import init_db 
from database.auth import add_user

app = FastAPI()
init_db()
add_user("wiener", "peter")

# config static files
app.mount('/static', StaticFiles(directory='static'), name='static')

# add middlewares
app.middleware("http")(check_access_token)
app.middleware("http")(add_security_headers)

app.include_router(auth_router)
app.include_router(dashboard_router)  
app.include_router(bot_router)
app.include_router(session_router)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)