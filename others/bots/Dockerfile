FROM python:3.9-slim

RUN apt-get update && apt-get install -y apache2-utils hping3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]