# import the library to run Postgres instance
import asyncpg
from config import DB_NAME, DB_USER, DB_PASSWD, DB_HOST, DB_PORT, REDIS_HOST, REDIS_PORT
import redis.asyncio as redis
from tenacity import retry, wait_fixed, stop_after_attempt

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
connection_pool = None


@retry(wait=wait_fixed(2), stop=stop_after_attempt(10))
# establish a new connection
async def create_db_pool():
    global connection_pool
    print("Creating DB pool...")
    connection_pool = await asyncpg.create_pool(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWD,
        host=DB_HOST,
        port=DB_PORT,
        min_size=1,
        max_size=100
    )
    print("DB pool created.")

# close connection pool
async def close_db_pool():
    global connection_pool
    if connection_pool:
        await connection_pool.close()
        print("DB pool closed.")
    else:
        print("DB pool was not initialized.")

# get connection pool (for other modules)
async def get_connection_pool():
    if connection_pool is None:
        await create_db_pool()  # Nếu pool chưa được tạo, khởi tạo nó
    return connection_pool

async def init_db():
    if not connection_pool:
        raise Exception("DB connection pool is not initialized.")
    async with connection_pool.acquire() as conn:
        try: 
            # await conn.execute("""
            # ALTER TABLE commands
            # DROP CONSTRAINT fk_commands_bot_id;
            # """)

            # await conn.execute("""
            # ALTER TABLE logs
            # DROP CONSTRAINT fk_logs_bot_id;
            # """)

            # await conn.execute("""
            # ALTER TABLE logs
            # DROP CONSTRAINT fk_logs_command_id;
            # """)

            # await conn.execute("""
            # ALTER TABLE bot_info
            # DROP CONSTRAINT fk_bot_info_bots_id;
            # """)
            # await conn.execute("DROP TABLE IF EXISTS c2_users;")
            # await conn.execute("DROP TABLE IF EXISTS bots;")
            # await conn.execute("DROP TABLE IF EXISTS bot_info;")
            # await conn.execute("DROP TABLE IF EXISTS commands;")
            # await conn.execute("DROP TABLE IF EXISTS logs;")

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS c2_users (
                id SERIAL PRIMARY KEY,
                fullname VARCHAR(100),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                hashed_passwd VARCHAR(255) NOT NULL,
                role VARCHAR(10) NOT NULL DEFAULT 'admin'
            )
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS c2_user_info (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                date_of_birth DATE,
                country VARCHAR(100),
                timezone VARCHAR(50),
                phone_number VARCHAR(20),
                website VARCHAR(255),
                avatar_url TEXT
            )
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_users (
                id SERIAL PRIMARY KEY,
                fullname VARCHAR(100),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                hashed_passwd VARCHAR(255) NOT NULL,
                role VARCHAR(10) NOT NULL DEFAULT 'user',
                verification_token VARCHAR(100) NOT NULL,
                token_expiry TIMESTAMP NOT NULL
            )
            """)

            await conn.execute("""
            CREATE TABLE password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL,
                expiry TIMESTAMP NOT NULL
            )
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id SERIAL PRIMARY KEY,
                token VARCHAR(50) UNIQUE,
                status VARCHAR(10) NOT NULL DEFAULT 'offline'
            )
            """)

            # ip???
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_info(
                id SERIAL PRIMARY KEY,
                bot_id INTEGER NOT NULL,
                username VARCHAR(256),
                hostname VARCHAR(256),
                ip VARCHAR(50),
                os VARCHAR(256),
                cpu VARCHAR(256),
                gpu VARCHAR(256),
                ram VARCHAR(256),
                disk VARCHAR(256),
                current_directory TEXT 
            )    
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS commands(
                id SERIAL PRIMARY KEY,
                bot_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                directory TEXT NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS logs(
                id SERIAL PRIMARY KEY,
                bot_id INTEGER NOT NULL,
                command_id INTEGER NOT NULL,
                result TEXT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await conn.execute("""
            CREATE TABLE web_topics (
                topic_id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                short_description TEXT,
                type VARCHAR(20) NOT NULL CHECK (type IN ('server-side', 'client-side', 'advanced')),
                slug VARCHAR(255) UNIQUE,
                icon VARCHAR(50), -- Lưu tên class của Bootstrap Icon (ví dụ: bi-database)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await conn.execute("""
            CREATE TABLE web_challenges (
                challenge_id SERIAL PRIMARY KEY,
                topic_id INT,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                level VARCHAR(20) NOT NULL CHECK (level IN ('APPRENTICE', 'PRACTITIONER', 'EXPERT')),
                status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
                lecture_link VARCHAR(255),
                source_code_link VARCHAR(255),
                solution TEXT,
                slug VARCHAR(255) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await conn.execute("""
            CREATE TABLE challenge_flags (
                flag_id SERIAL PRIMARY KEY,
                challenge_id INT,
                correct_flag VARCHAR(100) NOT NULL,
                UNIQUE (challenge_id)
            )
            """)

            await conn.execute("""
            CREATE TABLE user_challenge_status (
                user_id INT NOT NULL,
                challenge_id INT NOT NULL,
                is_solved BOOLEAN DEFAULT FALSE,
                solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, challenge_id)
            )
            """)

            await conn.execute("""
            CREATE TABLE docker_images (
                image_id SERIAL PRIMARY KEY,
                challenge_id INT,
                image_name VARCHAR(255) NOT NULL,
                ports VARCHAR(50),
                run_parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (challenge_id)
            )
            """)

            await conn.execute("""
            ALTER TABLE c2_user_info
            ADD CONSTRAINT fk_c2_user_info_user_id
            FOREIGN KEY (user_id) REFERENCES c2_users(id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE password_reset_tokens
            ADD CONSTRAINT fk_password_reset_tokens_user_id
            FOREIGN KEY (user_id) REFERENCES c2_users(id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE web_challenges
            ADD CONSTRAINT fk_web_challenges_topic_id
            FOREIGN KEY (topic_id) REFERENCES web_topics(topic_id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE challenge_flags
            ADD CONSTRAINT fk_challenge_flags_challenge_id
            FOREIGN KEY (challenge_id) REFERENCES web_challenges(challenge_id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE user_challenge_status
            ADD CONSTRAINT fk_user_challenge_status_user_id
            FOREIGN KEY (user_id) REFERENCES c2_users(id) ON DELETE CASCADE;
            """)
            
            await conn.execute("""
            ALTER TABLE user_challenge_status
            ADD CONSTRAINT fk_user_challenge_status_challenge_id
            FOREIGN KEY (challenge_id) REFERENCES web_challenges(challenge_id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE docker_images
            ADD CONSTRAINT fk_docker_images_challenge_id
            FOREIGN KEY (challenge_id) REFERENCES web_challenges(challenge_id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE commands
            ADD CONSTRAINT fk_commands_bot_id
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE logs
            ADD CONSTRAINT fk_logs_bot_id
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE;
            """)

            await conn.execute("""
            ALTER TABLE logs
            ADD CONSTRAINT fk_logs_command_id
            FOREIGN KEY (command_id) REFERENCES commands(id);
            """)

            await conn.execute("""
            ALTER TABLE bot_info
            ADD CONSTRAINT fk_bot_info_bots_id
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE;
            """)

            ###############################################

            await conn.execute("""
            INSERT INTO web_topics (title, description, short_description, type, slug, icon) 
            VALUES 
            -- Server-Side Topics
            ('SQL Injection', 'SQL injection is a critical security vulnerability that allows attackers to interfere with the queries an application makes to its database. By exploiting this flaw, malicious actors can extract sensitive data such as user credentials, manipulate database contents, or even gain unauthorized access to the underlying server. In these hands-on labs, you’ll learn how to identify and exploit SQL injection vulnerabilities, and experience common techniques to retrieve hidden data, bypass authentication, and manipulate database structures. Each lab is designed to emulate real-world scenarios, helping you build practical skills to secure applications against such attacks.', 'Exploit vulnerable SQL queries to extract or modify data.', 'server-side', 'sql-injection', 'bi-database'),
            ('Authentication', 'Understand and exploit flaws in login or session management to gain unauthorized access. These labs will teach you how to bypass authentication mechanisms, manipulate sessions, and escalate privileges using real-world scenarios.', 'Understand and exploit flaws in login or session management.', 'server-side', 'authentication', 'bi-lock'),
            ('Path Traversal', 'Bypass controls to read sensitive files on the server by exploiting path traversal vulnerabilities. Learn how to manipulate file paths to access restricted directories and files in a web application.', 'Bypass controls to read sensitive files on the server.', 'server-side', 'path-traversal', 'bi-folder'),
            ('Command Injection', 'Inject system commands to execute on the server by exploiting command injection vulnerabilities. These labs will guide you through techniques to execute arbitrary commands and gain control over the server.', 'Inject system commands to execute on the server.', 'server-side', 'command-injection', 'bi-terminal'),
            ('Access Control', 'Bypass restrictions to access unauthorized functionality or data by exploiting broken access control vulnerabilities. Learn how to manipulate user roles and permissions to escalate privileges.', 'Bypass restrictions to access unauthorized functionality or data.', 'server-side', 'access-control', 'bi-lock-fill'),
            ('File Upload Vulnerabilities', 'Bypass filters to upload malicious files like web shells by exploiting file upload vulnerabilities. These labs will teach you how to exploit weak file validation to gain remote code execution.', 'Bypass filters to upload malicious files like web shells.', 'server-side', 'file-upload-vulnerabilities', 'bi-upload'),
            ('Race Conditions', 'Exploit timing issues in applications to gain unauthorized access by leveraging race condition vulnerabilities. Learn how to manipulate concurrent processes to bypass security controls.', 'Exploit timing issues in applications to gain unauthorized access.', 'server-side', 'race-conditions', 'bi-clock'),
            ('Server-Side Request Forgery (SSRF)', 'Exploit server-side applications to make requests on behalf of the server by leveraging SSRF vulnerabilities. These labs will teach you how to access internal systems and services.', 'Exploit server-side applications to make requests on behalf of the server.', 'server-side', 'ssrf', 'bi-server'),
            ('XXE Injection', 'Exploit XML parsers to read arbitrary files or make network requests by leveraging XXE vulnerabilities. Learn how to craft malicious XML inputs to bypass security controls.', 'Exploit XML parsers to read arbitrary files or make network requests.', 'server-side', 'xxe-injection', 'bi-file-code'),
            ('NoSQL Injection', 'Exploit NoSQL databases by injecting malicious queries to manipulate data. These labs will guide you through techniques to bypass NoSQL query validation and extract sensitive information.', 'Exploit NoSQL databases by injecting malicious queries.', 'server-side', 'nosql-injection', 'bi-database-fill'),
            -- Client-Side Topics
            ('Cross-Site Scripting (XSS)', 'Inject malicious scripts into web pages viewed by other users by exploiting XSS vulnerabilities. Learn how to execute client-side code to steal user data or perform unauthorized actions.', 'Inject malicious scripts into web pages viewed by other users.', 'client-side', 'xss', 'bi-code-slash'),
            ('Cross-Site Request Forgery (CSRF)', 'Exploit authenticated users to perform unintended actions by leveraging CSRF vulnerabilities. These labs will teach you how to craft malicious requests to manipulate user sessions.', 'Exploit authenticated users to perform unintended actions.', 'client-side', 'csrf', 'bi-shield-lock'),
            ('Cross-Origin Resource Sharing (CORS)', 'Misconfigurations that allow unauthorized access to resources by exploiting CORS vulnerabilities. Learn how to bypass CORS policies to access sensitive data from other origins.', 'Misconfigurations that allow unauthorized access to resources.', 'client-side', 'cors', 'bi-globe'),
            ('Clickjacking', 'Trick users into clicking on something different from what they intend by exploiting clickjacking vulnerabilities. These labs will teach you how to overlay malicious UI elements.', 'Trick users into clicking on something different from what they intend.', 'client-side', 'clickjacking', 'bi-cursor'),
            ('DOM-Based Vulnerabilities', 'Manipulate client-side code to access and modify user data by exploiting DOM-based vulnerabilities. Learn how to exploit JavaScript code to execute malicious scripts.', 'Manipulate client-side code to access and modify user data.', 'client-side', 'dom-based-vulnerabilities', 'bi-window'),
            -- Advanced Topics
            ('Insecure Deserialization', 'Exploit deserialization vulnerabilities to execute arbitrary code by manipulating serialized data. These labs will guide you through techniques to bypass deserialization security controls.', 'Exploit deserialization vulnerabilities to execute arbitrary code.', 'advanced', 'insecure-deserialization', 'bi-code'),
            ('Server-Side Template Injection (SSTI)', 'Inject malicious template code into the server-side rendering engine by exploiting SSTI vulnerabilities. Learn how to execute arbitrary code within template engines.', 'Inject malicious template code into the server-side rendering engine.', 'advanced', 'ssti', 'bi-file-earmark-code'),
            ('OAuth Authentication', 'Bypass OAuth authentication to gain unauthorized access by exploiting misconfigurations in OAuth flows. These labs will teach you how to manipulate OAuth tokens and scopes.', 'Bypass OAuth authentication to gain unauthorized access.', 'advanced', 'oauth-authentication', 'bi-person-check'),
            ('JWT (JSON Web Tokens)', 'Exploit weaknesses in JWT handling for unauthorized access by manipulating JSON Web Tokens. Learn how to bypass JWT validation and forge tokens to escalate privileges.', 'Exploit weaknesses in JWT handling for unauthorized access.', 'advanced', 'jwt', 'bi-key');
            """)

            await conn.execute("""
            INSERT INTO web_challenges (
                topic_id, title, description, level, status, lecture_link, source_code_link, solution, slug
            ) VALUES 
            -- SQL Injection (topic_id = 1)
            (1, 'SQL injection vulnerability in WHERE clause allowing retrieval of hidden data', 'This lab contains a SQL injection vulnerability in the product category filter. When the user selects a category, the application carries out a SQL query like the following: SELECT * FROM products WHERE category = ''Gifts'' AND released = 1. To solve the lab, perform a SQL injection attack that causes the application to display one or more unreleased products.', 'APPRENTICE', 'active', 'https://yourserver.com/docs/sql_injection_where_clause.pdf', 'https://github.com/yourrepo/sql_injection_where_clause', '<ol class="solution-list"><li data-step="1">Use Burp Suite to intercept and modify the request that sets the category filter.</li><li data-step="2">Modify the category parameter, giving it the value ''+ OR 1=1 --.</li><li data-step="3">Submit the request, and verify the response now contains one or more unreleased products.</li></ol>', 'sql-injection-vulnerability-in-where-clause-allowing-retrieval-of-hidden-data'),
            (1, 'SQL injection vulnerability allowing login bypass', 'This lab contains a SQL injection vulnerability in the login form. To solve the lab, perform a SQL injection attack that logs you in as the administrator user.', 'APPRENTICE', 'active', 'https://yourserver.com/docs/sql_injection_login_bypass.pdf', 'https://github.com/yourrepo/sql_injection_login_bypass', '<ol class="solution-list"><li data-step="1">Enter a malicious input in the username field.</li><li data-step="2">Use a payload like ''administrator'' OR 1=1 --.</li><li data-step="3">Log in as admin.</li></ol>', 'sql-injection-vulnerability-allowing-login-bypass'),
            (1, 'SQL injection attack, querying the database type and version on Oracle', 'This lab requires you to query the Oracle database version. To solve the lab, perform a SQL injection attack that determines the database type and version.', 'PRACTITIONER', 'active', 'https://yourserver.com/docs/sql_injection_oracle_version.pdf', 'https://github.com/yourrepo/sql_injection_oracle_version', '<ol class="solution-list"><li data-step="1">Inject a payload to query the version.</li><li data-step="2">Use SELECT banner FROM v$version.</li></ol>', 'sql-injection-attack-querying-the-database-type-and-version-on-oracle'),
            (1, 'SQL injection attack, querying the database type and version on MySQL and Microsoft', 'This lab requires you to query the MySQL or Microsoft SQL Server version. To solve the lab, perform a SQL injection attack that determines the database type and version.', 'PRACTITIONER', 'active', 'https://yourserver.com/docs/sql_injection_mysql_version.pdf', 'https://github.com/yourrepo/sql_injection_mysql_version', '<ol class="solution-list"><li data-step="1">Inject a payload to query the version.</li><li data-step="2">Use SELECT @@version.</li></ol>', 'sql-injection-attack-querying-the-database-type-and-version-on-mysql-and-microsoft'),
            (1, 'SQL injection attack, listing the database contents on non-Oracle databases', 'This lab requires you to list the database contents on a non-Oracle database. To solve the lab, perform a SQL injection attack that lists the tables in the database.', 'PRACTITIONER', 'active', 'https://yourserver.com/docs/sql_injection_non_oracle_contents.pdf', 'https://github.com/yourrepo/sql_injection_non_oracle_contents', '<ol class="solution-list"><li data-step="1">Inject a payload to list tables.</li><li data-step="2">Use SELECT * FROM information_schema.tables.</li></ol>', 'sql-injection-attack-listing-the-database-contents-on-non-oracle-databases'),
            (1, 'SQL injection attack, listing the database contents on Oracle', 'This lab requires you to list the database contents on an Oracle database. To solve the lab, perform a SQL injection attack that lists the tables in the database.', 'PRACTITIONER', 'active', 'https://yourserver.com/docs/sql_injection_oracle_contents.pdf', 'https://github.com/yourrepo/sql_injection_oracle_contents', '<ol class="solution-list"><li data-step="1">Inject a payload to list tables.</li><li data-step="2">Use SELECT * FROM all_tables.</li></ol>', 'sql-injection-attack-listing-the-database-contents-on-oracle'),
            (1, 'SQL injection UNION attack, determining the number of columns returned by the query', 'This lab requires you to determine the number of columns in a UNION attack. To solve the lab, perform a SQL injection UNION attack that determines the number of columns returned by the query.', 'PRACTITIONER', 'active', 'https://yourserver.com/docs/sql_injection_union_columns.pdf', 'https://github.com/yourrepo/sql_injection_union_columns', '<ol class="solution-list"><li data-step="1">Inject a UNION SELECT payload.</li><li data-step="2">Use ORDER BY to find the number of columns.</li></ol>', 'sql-injection-union-attack-determining-the-number-of-columns-returned-by-the-query'),
            (1, 'SQL injection UNION attack, finding a column containing text', 'This lab requires you to find a text column in a UNION attack. To solve the lab, perform a SQL injection UNION attack that identifies a column containing text.', 'PRACTITIONER', 'active', 'https://yourserver.com/docs/sql_injection_union_text.pdf', 'https://github.com/yourrepo/sql_injection_union_text', '<ol class="solution-list"><li data-step="1">Inject a UNION SELECT payload.</li><li data-step="2">Test each column with a string value.</li></ol>', 'sql-injection-union-attack-finding-a-column-containing-text'),
            (1, 'SQL injection UNION attack, retrieving data from other tables', 'This lab requires you to retrieve data from other tables using a UNION attack. To solve the lab, perform a SQL injection UNION attack that retrieves sensitive data.', 'EXPERT', 'active', 'https://yourserver.com/docs/sql_injection_union_data.pdf', 'https://github.com/yourrepo/sql_injection_union_data', '<ol class="solution-list"><li data-step="1">Inject a UNION SELECT payload.</li><li data-step="2">Retrieve data from another table.</li></ol>', 'sql-injection-union-attack-retrieving-data-from-other-tables'),
            (1, 'SQL injection UNION attack, retrieving multiple values in a single column', 'This lab requires you to retrieve multiple values in a single column using a UNION attack. To solve the lab, perform a SQL injection UNION attack that retrieves multiple values.', 'EXPERT', 'active', 'https://yourserver.com/docs/sql_injection_union_multiple.pdf', 'https://github.com/yourrepo/sql_injection_union_multiple', '<ol class="solution-list"><li data-step="1">Inject a UNION SELECT payload.</li><li data-step="2">Concatenate multiple values.</li></ol>', 'sql-injection-union-attack-retrieving-multiple-values-in-a-single-column');
            """)

            await conn.execute("""
            INSERT INTO challenge_flags (challenge_id, correct_flag) 
            VALUES 
            (1, 'C2{example_flag}'),
            (2, 'C2{example_flag}'),
            (3, 'C2{example_flag}'),
            (4, 'C2{example_flag}'),
            (5, 'C2{example_flag}'),
            (6, 'C2{example_flag}'),
            (7, 'C2{example_flag}'),
            (8, 'C2{example_flag}'),
            (9, 'C2{example_flag}'),
            (10, 'C2{example_flag}')
            """)

            await conn.execute("""
            INSERT INTO docker_images(challenge_id, image_name, ports, run_parameters)
            VALUES (1, 'sqli-lab-1:latest', 80, '{"cpu_quota": 30000, "cpu_period": 100000, "mem_limit": "100m"}')
            """)
        except Exception as e:
            raise Exception(f"error initializing database: {str(e)}")
    