-- =====================================================================
-- One-time server setup: creates the database and an application user.
-- Run as an administrator, e.g.:
--     sudo mariadb < sql/setup_mysql.sql
--     mysql -u root -p < sql/setup_mysql.sql
-- Change the password here AND in db_config.json if you use your own.
-- The tables and demo data are created by the application on first start
-- (or manually with schema.sql + seed.sql).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS gym_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'gym_app'@'localhost' IDENTIFIED BY 'gym_pass';
GRANT ALL PRIVILEGES ON gym_db.* TO 'gym_app'@'localhost';
FLUSH PRIVILEGES;
