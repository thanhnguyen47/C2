# C2

## tech stack
+ framework: fastapi (async web framework)
+ websocket: in fastapi
+ server: uvicorn (asgi server for fastapi)
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
psycopg2
```

+ we need to install these packages
```bash
pip install -r requirements.txt
```

