class BaseAttack:
    def __init__(self, bot_id, attack_id, target, duration, intensity, **kwargs):
        """Khởi tạo đối tượng tấn công với các tham số cơ bản."""
        self.bot_id = bot_id
        self.attack_id = attack_id
        self.target = target
        self.duration = duration  # Thời gian tấn công (giây)
        self.intensity = intensity  # Cường độ tấn công (số request mỗi giây)
        self.kwargs = kwargs  # Các tham số bổ sung (spoof_headers, custom_headers, v.v.)

    async def execute(self):
        """Phương thức trừu tượng để thực thi tấn công."""
        raise NotImplementedError("error")