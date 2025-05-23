# C2

## tech stack
+ framework: fastapi (async web framework)
+ websocket: in fastapi
+ server: uvicorn (asgi - Asynchronous Server Gateway Interface, server for fastapi)
+ database: portgresql (chat history, data of victims, ...)
+ driver: psycopg2 (connect between python and database)
+ frontend: html/javascript + bootstrap

## project structure
```text
C2/
|- main.py 
|- database/
    |- auth.py
    |- dbmain.py
    |- get_bot_record.py
    |- update_bot_record.py
|- static/
    |- js/
        |- index.js
    |- styles/
        |- index.css
|- templates/
    |- index.html
|- uploads
|- .env
```
## setup

```bash
# update system
sudo apt update && sudo apt upgrade -y

# install python3
sudo apt install python3 python3-pip python3-venv -y

# check version
python3 --version
pip3 --version

# install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# start postgreSQL service on linux
sudo systemctl start postgresql
sudo systemctl enable postgresql
# https://www.digitalocean.com/community/tutorials/how-to-install-postgresql-on-ubuntu-20-04-quickstart

# access as postgre user. initially, postgres has no password, we will just access it in local. Then after all, we just exit the session to back.
sudo -i -u postgres
psql
```

Now, after install all the things we need, we're gonna create database

```sql
CREATE USER c2_user WITH PASSWORD 'your_password';
CREATE DATABASE c2_db OWNER c2_user;
GRANT ALL PRIVILEGES ON DATABASE c2_db TO c2_user;

-- example
-- postgres=# CREATE USER c2_user WITH PASSWORD 'thanh';
-- postgres-# CREATE DATABASE c2_db OWNER c2_user;
-- postgres-# GRANT ALL PRIVILEGES ON DATABASE c2_db TO c2_user;

-- check:
-- postgres=# \du

```

oke, let's check the connect
```bash
psql -h localhost -U c2_user -d c2_db
# then enter the password
```

if it's oke, we go to the next step

+ in requirements.txt, we have:
```text
fastapi
uvicorn
asyncpg # connect postgresql, using async query
bcrypt # hash
secrets # generate secure random string
python-dotenv # read .env variables
jinja2 # render html
python-multipart
pyjwt
```

+ using virtual environment to isolate the packages we will install for this project. Make sure that we choose .venv python interpreter (ctrl + shift + p)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

+ we need to install these packages for this project
```bash
pip install -r requirements.txt
```

## Work flow: 

```text
request --> middleware1 (check access_token) --> routes + database (handle request) --> middleware2 (add secure headers to response) --> response
```

![alt text](image.png)