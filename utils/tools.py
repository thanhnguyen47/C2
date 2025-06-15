import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from fastapi import HTTPException
from config import SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER, SMTP_PORT, DOMAIN, docker_client, scheduler, traefik_container
from dateutil.parser import parse
import pytz
import json
from database.dbmain import redis_client
from datetime import datetime, timedelta

async def delete_web_container_job(container_id: str, user_id: str):
    try:
        container = docker_client.containers.get(container_id)
        network_name = f"web_lab_user_{user_id}"
        container.stop()
        container.remove()
        await redis_client.delete(f"user:container:{user_id}")
        await redis_client.delete(f"user:lab_net:{user_id}")
        docker_client.networks.get(network_name).remove()
        print("delete web container triggered")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete container: {str(e)}")

def schedule_web_container_deletion(container_id: str, user_id: str, delay: int):
    try:
        job = scheduler.add_job(
            delete_web_container_job,
            'date',
            run_date=datetime.now() + timedelta(seconds=delay),
            args=[container_id, user_id],
            id=f"delete_container_{container_id}",
            replace_existing=True
        )
        return job.id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule container deletion: {str(e)}")

async def delete_ddos_container_jobs(user_id: str):
    try:
        network_name = f"ddos_net_user_{user_id}"

        # get ddos-target container id and botnets from redis first before deleting
        botnets = await redis_client.get(f"user_botnets:{user_id}")
        print(f"botnets: {botnets}")
        container_id = await redis_client.get(f"user_containers:{user_id}")
        print(f"container_id: {container_id}")
        if botnets:
            bot_ids = json.loads(botnets)
            for bot in bot_ids:
                try:
                    bot_container = docker_client.containers.get(bot["container_id"])
                    print(f"bot container: {bot_container}")
                    container_user_id = bot_container.labels.get("user_id")
                    if container_user_id != user_id:
                        continue
                    bot_container.stop()
                    bot_container.remove()
                except Exception as e:
                    print(f"Failed to remove bot {bot['bot_id']}: {str(e)}")
            await redis_client.delete(f"user_botnets:{user_id}")

       
        if not container_id:
            async for key in redis_client.scan_iter(f"attack:*"):
                attack_data = await redis_client.get(key)
                if attack_data:
                    attack = json.loads(attack_data)
                    if attack["user_id"] == user_id:
                        await redis_client.delete(key)
            return {"message": "No target running"}

        try:
            container = docker_client.containers.get(container_id.decode())
            container_user_id = container.labels.get("user_id")
            if container_user_id != user_id:
                print(f"container_user_id: {container_user_id} and user_id: {user_id}")
                raise HTTPException(status_code=403, detail="Target does not belong to this user")
            container.stop()
            container.remove()
            await redis_client.delete(f"user_containers:{user_id}")
        except Exception as e:
            print(f"Failed to stop target: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to stop target: {str(e)}")
        print("delete target success")


        # Xóa thông tin attack
        async for key in redis_client.scan_iter(f"attack:*"):
            attack_data = await redis_client.get(key)
            if attack_data:
                attack = json.loads(attack_data)
                if attack["user_id"] == user_id:
                    await redis_client.delete(key)

       # Delete the network
        try:
            network = docker_client.networks.get(network_name)
            try:
                network.disconnect(traefik_container)
            except Exception as e:
                print(f"Failed to disconnect traefik from network: {str(e)}")
            network.reload()
            for container in network.containers:
                try:
                    network.disconnect(container)
                    print(f"Disconnected container {container.id} from network {network_name}")
                except Exception as e:
                    print(f"Failed to disconnect container {container.id}: {str(e)}")
            network.remove()
        except Exception as e:
            print(f"Failed to stop network: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to stop network: {str(e)}")
        print("delete network success")
        print("delete web container triggered")
        return True
    except Exception as e:
        print(f"Error during DDoS cleanup for user {user_id}: {str(e)}")
        # await redis_client.delete(f"user_containers:{user_id}")
        # await redis_client.delete(f"user_botnets:{user_id}")
        return False

def schedule_ddos_containers_deletion(user_id: str, delay: int):
    try:

        run_date = datetime.now() + timedelta(seconds=delay)
        job = scheduler.add_job(
            delete_ddos_container_jobs,
            'date',
            run_date=run_date,
            args=[user_id],
            id=f"delete_ddos_containers_{user_id}",
            replace_existing=True
        )
        return job.id
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Failed to schedule DDoS containers deletion: {str(e)}")


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def validate_date_of_birth(dob: str) -> str:
    if not dob:
        return None
    try:
        parsed = parse(dob)
        return parsed.date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date of birth format (YYYY-MM-DD)")

def validate_phone_number(phone: str) -> str:
    if not phone:
        return None
    if not re.match(r"^\+[1-9]\d{1,14}$", phone):
        raise HTTPException(status_code=400, detail="Invalid phone number (must be E.164 format, e.g., +84912345678)")
    return phone

def validate_timezone(tz: str) -> str:
    if not tz:
        return None
    if tz not in pytz.all_timezones:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    return tz

async def send_verification_email(email: str, token: str):
    smtp_server = SMTP_SERVER
    smtp_port = SMTP_PORT
    sender_email = SENDER_EMAIL
    sender_password = SENDER_PASSWORD

    verification_url = f"https://{DOMAIN}/verify/{token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "🔐 Email Verification Required"
    message["From"] = sender_email
    message["To"] = email

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #333;">👋 Welcome to the Platform!</h2>
                <p>Please click the button below to verify your email address:</p>
                <a href="{verification_url}" style="display: inline-block; margin: 20px 0; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">Verify Email</a>
                <p>If you did not create an account, you can safely ignore this email.</p>
                <p style="font-size: 12px; color: #888;">Thank you!<br/> C2 platform!!</p>
            </div>
        </body>
    </html>
    """

    part = MIMEText(html_content, "html")
    message.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

async def send_reset_password_email(email: str, token: str):
    smtp_server = SMTP_SERVER
    smtp_port = SMTP_PORT
    sender_email = SENDER_EMAIL
    sender_password = SENDER_PASSWORD

    reset_url = f"https://{DOMAIN}/reset-password/{token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "🔒 Password Reset Request"
    message["From"] = sender_email
    message["To"] = email

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f2f2f2; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #333;">🛠 Reset Your Password</h2>
                <p>We received a request to reset your password. Click the button below to choose a new one:</p>
                <a href="{reset_url}" style="display: inline-block; margin: 20px 0; padding: 10px 20px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a>
                <p>If you didn’t request this, please ignore this email. The link will expire in 30 minutes.</p>
                <p style="font-size: 12px; color: #888;">Thanks,<br/> C2 platform team</p>
            </div>
        </body>
    </html>
    """

    part = MIMEText(html_content, "html")
    message.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reset email: {str(e)}")
