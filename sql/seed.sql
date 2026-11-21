-- =====================================================================
-- IronPulse Fitness Club — demo seed data
-- Dates are relative to CURDATE() so the demo always shows a mix of
-- Active, Expiring Soon and Expired subscriptions.
-- Used by the "Reset Demo Data" button and on first start.
-- =====================================================================

-- Child tables first because of the foreign keys
DELETE FROM subscriptions;
DELETE FROM members;
DELETE FROM packages;
DELETE FROM trainers;
DELETE FROM users;

-- ---------------------------------------------------------------------
-- Staff accounts (password = SHA2(plain, 256))
-- ---------------------------------------------------------------------
INSERT INTO users (user_id, username, password_hash, role, full_name) VALUES
(1, 'admin',   SHA2('admin123', 256),   'Admin',   'Marcus Vance (Administrator)'),
(2, 'staff',   SHA2('staff123', 256),   'Staff',   'Elena Rostova (Desk Staff)'),
(3, 'manager', SHA2('manager123', 256), 'Manager', 'David Sterling (Operations Mgr)');

-- ---------------------------------------------------------------------
-- Trainers
-- ---------------------------------------------------------------------
INSERT INTO trainers (trainer_id, full_name, phone, specialization, monthly_salary, hire_date) VALUES
(101, 'Alex ''Titan'' Rivera', '+1-555-0192', 'Strength & Bodybuilding',       4500.00, '2023-01-15'),
(102, 'Sarah Jenkins',         '+1-555-0144', 'HIIT & Cardio Conditioning',    4200.00, '2023-03-20'),
(103, 'Liam Chen',             '+1-555-0188', 'CrossFit & Mobility',           4400.00, '2023-06-10'),
(104, 'Priya Sharma',          '+1-555-0131', 'Yoga & Pilates',                3900.00, '2023-08-01'),
(105, 'Marcus Brody',          '+1-555-0177', 'Athletic Rehab & Powerlifting', 4800.00, '2022-11-05');

-- ---------------------------------------------------------------------
-- Packages
-- ---------------------------------------------------------------------
INSERT INTO packages (package_id, package_name, duration_days, fee, description) VALUES
(1, 'Monthly Starter',     30,  59.99,  'Standard 30-day gym floor access with basic cardio and weights.'),
(2, 'Quarterly Pro',       90,  159.99, '90-day all-access membership including locker room and steam bath.'),
(3, 'Semi-Annual Elite',   180, 289.99, '6 months full access with complimentary nutrition consultation.'),
(4, 'Annual VIP Champion', 365, 499.99, '365 days unlimited 24/7 access, VIP lounge, guest passes, and towel service.'),
(5, 'Student Flex 30',     30,  39.99,  'Discounted 30-day access for active students with valid ID.');

-- ---------------------------------------------------------------------
-- Members
-- ---------------------------------------------------------------------
INSERT INTO members (member_id, full_name, phone, email, gender, join_date,
                     emergency_contact_name, emergency_contact_phone, trainer_id) VALUES
(1001, 'Johnathan Miller', '+1-555-1101', 'j.miller@example.com', 'Male',   '2024-01-10', 'Laura Miller',     '+1-555-2101', 101),
(1002, 'Emily Watson',     '+1-555-1102', 'emily.w@example.com',  'Female', '2024-02-15', 'Mark Watson',      '+1-555-2102', 102),
(1003, 'Michael Chang',    '+1-555-1103', 'mchang@example.com',   'Male',   '2024-03-01', 'Grace Chang',      '+1-555-2103', 103),
(1004, 'Sophia Rodriguez', '+1-555-1104', 'sophia.r@example.com', 'Female', '2024-04-12', 'Carlos Rodriguez', '+1-555-2104', 104),
(1005, 'David Kim',        '+1-555-1105', 'dkim@example.com',     'Male',   '2024-05-20', 'Min-ji Kim',       '+1-555-2105', 101),
(1006, 'Chloe Bennett',    '+1-555-1106', 'chloe.b@example.com',  'Female', '2024-06-18', 'Oliver Bennett',   '+1-555-2106', 102),
(1007, 'Robert Downey',    '+1-555-1107', 'rdowney@example.com',  'Male',   '2024-07-04', NULL,               NULL,          NULL),
(1008, 'Amina Al-Mansoor', '+1-555-1108', 'amina.m@example.com',  'Female', '2024-08-11', 'Yusuf Al-Mansoor', '+1-555-2108', 104),
(1009, 'Lucas Silva',      '+1-555-1109', 'lucas.s@example.com',  'Male',   '2024-09-02', 'Ana Silva',        '+1-555-2109', 105),
(1010, 'Grace Hopper',     '+1-555-1110', 'grace.h@example.com',  'Female', '2024-09-25', NULL,               NULL,          NULL);

-- ---------------------------------------------------------------------
-- Subscriptions (payment ledger)
-- end_date is computed with DATE_ADD(start_date, INTERVAL duration DAY)
-- ---------------------------------------------------------------------
INSERT INTO subscriptions (sub_id, member_id, package_id, payment_date, start_date, end_date, amount_paid, payment_method) VALUES
-- Older, already-finished plans (give the monthly revenue report some history)
(5001, 1004, 1, DATE_SUB(CURDATE(), INTERVAL 135 DAY), DATE_SUB(CURDATE(), INTERVAL 135 DAY), DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 135 DAY), INTERVAL 30 DAY), 59.99, 'Cash'),
(5002, 1006, 2, DATE_SUB(CURDATE(), INTERVAL 160 DAY), DATE_SUB(CURDATE(), INTERVAL 160 DAY), DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 160 DAY), INTERVAL 90 DAY), 159.99, 'Credit Card'),
(5003, 1005, 1, DATE_SUB(CURDATE(), INTERVAL 100 DAY), DATE_SUB(CURDATE(), INTERVAL 100 DAY), DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 100 DAY), INTERVAL 30 DAY), 59.99, 'UPI / Digital'),
(5004, 1003, 1, DATE_SUB(CURDATE(), INTERVAL 118 DAY), DATE_SUB(CURDATE(), INTERVAL 118 DAY), DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 118 DAY), INTERVAL 30 DAY), 59.99, 'Debit Card'),
-- Current plans
(5005, 1001, 4, DATE_SUB(CURDATE(), INTERVAL 60 DAY),  DATE_SUB(CURDATE(), INTERVAL 60 DAY),  DATE_ADD(CURDATE(), INTERVAL 305 DAY), 499.99, 'Credit Card'),   -- Active
(5006, 1002, 1, DATE_SUB(CURDATE(), INTERVAL 26 DAY),  DATE_SUB(CURDATE(), INTERVAL 26 DAY),  DATE_ADD(CURDATE(), INTERVAL 4 DAY),   59.99,  'Debit Card'),    -- Expiring soon
(5007, 1003, 2, DATE_SUB(CURDATE(), INTERVAL 88 DAY),  DATE_SUB(CURDATE(), INTERVAL 88 DAY),  DATE_ADD(CURDATE(), INTERVAL 2 DAY),   159.99, 'Cash'),          -- Expiring soon
(5008, 1004, 2, DATE_SUB(CURDATE(), INTERVAL 45 DAY),  DATE_SUB(CURDATE(), INTERVAL 45 DAY),  DATE_ADD(CURDATE(), INTERVAL 45 DAY),  159.99, 'Bank Transfer'), -- Active
(5009, 1005, 1, DATE_SUB(CURDATE(), INTERVAL 40 DAY),  DATE_SUB(CURDATE(), INTERVAL 40 DAY),  DATE_SUB(CURDATE(), INTERVAL 10 DAY),  59.99,  'Cash'),          -- Expired
(5010, 1006, 3, DATE_SUB(CURDATE(), INTERVAL 70 DAY),  DATE_SUB(CURDATE(), INTERVAL 70 DAY),  DATE_ADD(CURDATE(), INTERVAL 110 DAY), 289.99, 'Credit Card'),   -- Active
(5011, 1007, 5, DATE_SUB(CURDATE(), INTERVAL 55 DAY),  DATE_SUB(CURDATE(), INTERVAL 55 DAY),  DATE_SUB(CURDATE(), INTERVAL 25 DAY),  39.99,  'Credit Card'),   -- Expired
(5012, 1008, 1, DATE_SUB(CURDATE(), INTERVAL 12 DAY),  DATE_SUB(CURDATE(), INTERVAL 12 DAY),  DATE_ADD(CURDATE(), INTERVAL 18 DAY),  59.99,  'UPI / Digital'), -- Active
(5013, 1009, 1, DATE_SUB(CURDATE(), INTERVAL 24 DAY),  DATE_SUB(CURDATE(), INTERVAL 24 DAY),  DATE_ADD(CURDATE(), INTERVAL 6 DAY),   59.99,  'Debit Card'),    -- Expiring soon
(5014, 1010, 4, DATE_SUB(CURDATE(), INTERVAL 115 DAY), DATE_SUB(CURDATE(), INTERVAL 115 DAY), DATE_ADD(CURDATE(), INTERVAL 250 DAY), 499.99, 'Bank Transfer'); -- Active

-- ---------------------------------------------------------------------
-- The inserts above fired the audit triggers; start the demo with a clean log
-- ---------------------------------------------------------------------
DELETE FROM audit_log;
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
VALUES ('system', 'DEMO_RESET', 'all', NULL, 'Demo data loaded');
