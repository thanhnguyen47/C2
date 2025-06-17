# CTOACADEMY - Online Cybersecurity Attack Practice Platform

> Live demo: [ctoacademy.io.vn](https://ctoacademy.io.vn)

## About

This platform provides a web-based interface to launch and interact with isolated vulnerable environments (labs) where users can perform offensive security techniques safely and legally. It supports common attack vectors like DDoS attacks, Malware, and Web-based vulnerabilities such as SQL Injection, Cross-Site Scripting (XSS), Command Injection, and more.

## Features 

+ Web-based user interface for interaction
+ Admin dashboard for topic/lab management, user management.
+ Docker-based isolated environments
+ PostgreSQL database for persistent data storage
+ DDoS attacks simulation, malware attack simulation
+ Web exploitation labs

## Tech Stack
+ Backend: FastAPI (async web framework)
+ Server: Uvicorn (asgi - Asynchronous Server Gateway Interface, server for fastapi)
+ Driver: psycopg2 (connect between python and database)
+ Frontend: HTML/Javascript + Bootstrap, Jinja2
+ Database: PostgreSQL
+ Containerization: Docker, Docker Compose
+ Security: JWT, HTTPS
+ Others: Traefik, Redis

## Setup Instruction 

First, prepare a VPS then clone this repo on it, download docker and docker-compose.

Change directory to `C2`, then do the follow:

```bash
mv docker-compose.yml ..
mv traefik.yml ..

# build ddos-bot and ddos-target images
cd others/bots
docker build -t ddos-bot .
cd ../targets
docker build -t ddos-target .

# run docker-compose
cd ~
docker-compose down && docker-compose up --build
```

Configurate Cloudflare Nameservers to support dynamic routing.

## Project Structure

. \
├── C2/ \
│   ├── main.py \
│   ├── middlewares.py \
│   ├── config.py \
│   ├── .env \
│   ├── .gitignore \
│   ├── database/ \
│   ├── routes/ \
│   ├── templates/ \
│   ├── static/ \
│   ├── utils/ \
│   ├── uploads/ \
│   ├── others/ \
│   ├── requirements.txt \
│   ├── README.md \
│   └── Dockerfile \
├── docker-compose.yml \
└── traefik.yml \


## Contributing

Contributions are welcome! Please open an issue first to discuss what you would like to change.

## Contact

Mail: thanhnguyent472003@gmail.com