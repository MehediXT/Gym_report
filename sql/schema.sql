-- =====================================================================
-- IronPulse Fitness Club — Member & Subscription Management System
-- DDL script: 3NF schema, constraints, indexes and reporting views.
-- Target: MySQL 8.0+ / MariaDB 10.5+ (InnoDB).
--
-- Run inside the application database, e.g.:
--     mysql -u gym_app -p gym_db < sql/schema.sql
-- (The application also runs this automatically on first start.)
-- =====================================================================

-- ---------------------------------------------------------------------
-- users: staff accounts for authentication & role-based access control
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    username       VARCHAR(50)  NOT NULL,
    password_hash  CHAR(64)     NOT NULL,                 -- SHA-256 hex digest
    role           ENUM('Admin', 'Manager', 'Staff') NOT NULL DEFAULT 'Staff',
    full_name      VARCHAR(100) NOT NULL,
    CONSTRAINT uq_users_username UNIQUE (username)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- trainers
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trainers (
    trainer_id      INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100)  NOT NULL,
    phone           VARCHAR(20)   NOT NULL,
    specialization  VARCHAR(100)  NOT NULL,
    monthly_salary  DECIMAL(10,2) NOT NULL,
    hire_date       DATE          NOT NULL,
    CONSTRAINT uq_trainers_phone UNIQUE (phone),
    CONSTRAINT chk_trainers_salary CHECK (monthly_salary > 0)
) ENGINE = InnoDB AUTO_INCREMENT = 101;

-- ---------------------------------------------------------------------
-- packages: membership tiers
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS packages (
    package_id     INT AUTO_INCREMENT PRIMARY KEY,
    package_name   VARCHAR(100)  NOT NULL,
    duration_days  INT           NOT NULL,
    fee            DECIMAL(10,2) NOT NULL,
    description    TEXT,
    CONSTRAINT uq_packages_name UNIQUE (package_name),
    CONSTRAINT chk_packages_duration CHECK (duration_days > 0),
    CONSTRAINT chk_packages_fee CHECK (fee >= 0)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- members  (trainers 1 : N members, ON DELETE SET NULL)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS members (
    member_id                INT AUTO_INCREMENT PRIMARY KEY,
    full_name                VARCHAR(100) NOT NULL,
    phone                    VARCHAR(20)  NOT NULL,
    email                    VARCHAR(120) NOT NULL,
    gender                   ENUM('Male', 'Female', 'Other') NOT NULL DEFAULT 'Male',
    join_date                DATE         NOT NULL,
    emergency_contact_name   VARCHAR(100) NULL,
    emergency_contact_phone  VARCHAR(20)  NULL,
    trainer_id               INT          NULL,
    CONSTRAINT uq_members_phone UNIQUE (phone),
    INDEX idx_members_full_name (full_name),       -- B-Tree index for name search
    CONSTRAINT fk_members_trainer FOREIGN KEY (trainer_id)
        REFERENCES trainers (trainer_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE = InnoDB AUTO_INCREMENT = 1001;

-- ---------------------------------------------------------------------
-- subscriptions: payment ledger
--   members  1 : N subscriptions (ON DELETE CASCADE)
--   packages 1 : N subscriptions (ON DELETE RESTRICT)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscriptions (
    sub_id          INT AUTO_INCREMENT PRIMARY KEY,
    member_id       INT           NOT NULL,
    package_id      INT           NOT NULL,
    payment_date    DATE          NOT NULL,       -- when the money was received
    start_date      DATE          NOT NULL,
    end_date        DATE          NOT NULL,       -- DATE_ADD(start_date, INTERVAL duration_days DAY)
    amount_paid     DECIMAL(10,2) NOT NULL,
    payment_method  ENUM('Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 'UPI / Digital') NOT NULL,
    CONSTRAINT chk_subscriptions_amount CHECK (amount_paid >= 0),
    CONSTRAINT chk_subscriptions_dates CHECK (end_date > start_date),
    INDEX idx_subscriptions_end_date (end_date),
    INDEX idx_subscriptions_payment_date (payment_date),
    CONSTRAINT fk_subscriptions_member FOREIGN KEY (member_id)
        REFERENCES members (member_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_subscriptions_package FOREIGN KEY (package_id)
        REFERENCES packages (package_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE = InnoDB AUTO_INCREMENT = 5001;

-- ---------------------------------------------------------------------
-- audit_log: change history written by the triggers in sql/triggers.sql.
-- Deliberately has no foreign keys so entries survive deleted records.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    event_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    app_user    VARCHAR(50)  NOT NULL DEFAULT 'system',  -- staff user from @app_user session variable
    action      VARCHAR(40)  NOT NULL,
    table_name  VARCHAR(30)  NOT NULL,
    record_id   INT          NULL,
    details     VARCHAR(255) NULL,
    INDEX idx_audit_log_time (event_time),
    INDEX idx_audit_log_action (action)
) ENGINE = InnoDB;

-- =====================================================================
-- Reporting views
-- =====================================================================

-- Latest subscription per member (window function: newest end_date wins)
CREATE OR REPLACE VIEW v_latest_subscription AS
SELECT sub_id, member_id, package_id, payment_date, start_date, end_date,
       amount_paid, payment_method
FROM (
    SELECT s.*,
           ROW_NUMBER() OVER (PARTITION BY s.member_id
                              ORDER BY s.end_date DESC, s.sub_id DESC) AS rn
    FROM subscriptions s
) ranked
WHERE rn = 1;

-- Unified member profile: LEFT JOINs keep members without a trainer or plan.
-- Status is derived with CURDATE()/DATEDIFF() at query time.
CREATE OR REPLACE VIEW v_member_overview AS
SELECT m.member_id,
       m.full_name,
       m.phone,
       m.email,
       m.gender,
       m.join_date,
       m.emergency_contact_name,
       m.emergency_contact_phone,
       m.trainer_id,
       COALESCE(t.full_name, 'Unassigned')                 AS trainer_name,
       ls.sub_id                                           AS latest_sub_id,
       COALESCE(p.package_name, 'No Subscription')         AS package_name,
       ls.start_date                                       AS sub_start,
       ls.end_date                                         AS sub_end,
       COALESCE(ls.amount_paid, 0)                         AS amount_paid,
       ls.payment_method                                   AS payment_method,
       DATEDIFF(ls.end_date, CURDATE())                    AS days_left,
       CASE
           WHEN ls.sub_id IS NULL                       THEN 'No Subscription'
           WHEN DATEDIFF(ls.end_date, CURDATE()) > 7    THEN 'Active'
           WHEN DATEDIFF(ls.end_date, CURDATE()) >= 0   THEN 'Expiring Soon'
           ELSE 'Expired'
       END                                                 AS status
FROM members m
LEFT JOIN trainers t              ON t.trainer_id = m.trainer_id
LEFT JOIN v_latest_subscription ls ON ls.member_id = m.member_id
LEFT JOIN packages p              ON p.package_id = ls.package_id;
