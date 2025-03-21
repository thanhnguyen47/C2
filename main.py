import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database.dbmain import init_db
from middlewares import check_access_token, add_security_headers
from routes.auth import auth_router
from routes.dashboard import dashboard_router

app = FastAPI()
init_db()

# config static files
app.mount('/static', StaticFiles(directory='static'), name='static')

# add middlewares
app.middleware("http")(check_access_token)
app.middleware("http")(add_security_headers)

app.include_router(auth_router)
app.include_router(dashboard_router)  

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)