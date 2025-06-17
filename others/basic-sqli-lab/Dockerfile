FROM php:8.2-apache

# Cài các gói cần thiết để build pdo_sqlite
RUN apt-get update && \
    apt-get install -y libsqlite3-dev && \
    docker-php-ext-install pdo pdo_sqlite

# Tạo thư mục làm việc
WORKDIR /var/www/html

# Copy file web và flag
COPY index.php flag.txt ./

# Copy sẵn SQLite DB đã khởi tạo
COPY db.sqlite .

# Mở cổng
EXPOSE 80
