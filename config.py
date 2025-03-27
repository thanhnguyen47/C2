from dotenv import load_dotenv
import os
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()
DB_NAME=os.getenv('DB_NAME')
DB_USER=os.getenv('DB_USER')
DB_PASSWD = os.getenv('DB_PASSWD')
DB_HOST=os.getenv('DB_HOST')
DB_PORT=os.getenv('DB_PORT')
PEPPER = os.getenv('PEPPER')
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

templates = Jinja2Templates(directory='templates')

class SystemDetails(BaseModel):
    username: str
    hostname: str
    os: str
    cpu: str
    gpu: str
    ram: str
    disk: str