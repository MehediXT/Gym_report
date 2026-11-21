-- =====================================================================
-- IronPulse — audit triggers
-- Every change to payments, members, prices and trainers is written to
-- audit_log automatically by the database. The application sets the
-- session variable @app_user to the signed-in staff username before each
-- write, so the log records who made the change.
--
-- Note: rows removed by ON DELETE CASCADE (a member's payments) or changed
-- by ON DELETE SET NULL do not fire triggers in MySQL/MariaDB; the
-- MEMBER_DELETED / TRAINER_DELETED entries cover those cases.
--
-- Run after schema.sql:  mysql -u gym_app -p gym_db < sql/triggers.sql
-- =====================================================================

-- Payment recorded
DROP TRIGGER IF EXISTS trg_subscriptions_after_insert;
CREATE TRIGGER trg_subscriptions_after_insert
AFTER INSERT ON subscriptions
FOR EACH ROW
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
VALUES (
    COALESCE(@app_user, 'system'), 'PAYMENT_RECORDED', 'subscriptions', NEW.sub_id,
    CONCAT(COALESCE((SELECT full_name FROM members WHERE member_id = NEW.member_id), CONCAT('Member #', NEW.member_id)),
           ' paid $', NEW.amount_paid, ' (', NEW.payment_method, ') for ',
           COALESCE((SELECT package_name FROM packages WHERE package_id = NEW.package_id), CONCAT('plan #', NEW.package_id)),
           ', valid ', NEW.start_date, ' to ', NEW.end_date)
);

-- Payment voided
DROP TRIGGER IF EXISTS trg_subscriptions_after_delete;
CREATE TRIGGER trg_subscriptions_after_delete
AFTER DELETE ON subscriptions
FOR EACH ROW
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
VALUES (
    COALESCE(@app_user, 'system'), 'PAYMENT_VOIDED', 'subscriptions', OLD.sub_id,
    CONCAT('Voided $', OLD.amount_paid, ' payment of ',
           COALESCE((SELECT full_name FROM members WHERE member_id = OLD.member_id), CONCAT('member #', OLD.member_id)),
           ' (', OLD.start_date, ' to ', OLD.end_date, ')')
);

-- Member registered
DROP TRIGGER IF EXISTS trg_members_after_insert;
CREATE TRIGGER trg_members_after_insert
AFTER INSERT ON members
FOR EACH ROW
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
VALUES (COALESCE(@app_user, 'system'), 'MEMBER_ADDED', 'members', NEW.member_id,
        CONCAT('Registered ', NEW.full_name, ' (', NEW.phone, ')'));

-- Member profile changed
DROP TRIGGER IF EXISTS trg_members_after_update;
CREATE TRIGGER trg_members_after_update
AFTER UPDATE ON members
FOR EACH ROW
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
VALUES (COALESCE(@app_user, 'system'), 'MEMBER_UPDATED', 'members', NEW.member_id,
        CONCAT('Updated ', NEW.full_name,
               IF(NOT (OLD.trainer_id <=> NEW.trainer_id), ' (trainer changed)', ''),
               IF(OLD.phone <> NEW.phone, CONCAT(' (phone ', OLD.phone, ' -> ', NEW.phone, ')'), '')));

-- Member deleted (their payments are removed by ON DELETE CASCADE)
DROP TRIGGER IF EXISTS trg_members_after_delete;
CREATE TRIGGER trg_members_after_delete
AFTER DELETE ON members
FOR EACH ROW
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
VALUES (COALESCE(@app_user, 'system'), 'MEMBER_DELETED', 'members', OLD.member_id,
        CONCAT('Deleted ', OLD.full_name, ' (', OLD.phone, ') and their payment history'));

-- Plan price changed (only logged when the fee actually changes)
DROP TRIGGER IF EXISTS trg_packages_after_update;
CREATE TRIGGER trg_packages_after_update
AFTER UPDATE ON packages
FOR EACH ROW
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
SELECT COALESCE(@app_user, 'system'), 'PRICE_CHANGED', 'packages', NEW.package_id,
       CONCAT(NEW.package_name, ' fee $', OLD.fee, ' -> $', NEW.fee)
FROM DUAL
WHERE OLD.fee <> NEW.fee;

-- Trainer removed (members become unassigned via ON DELETE SET NULL)
DROP TRIGGER IF EXISTS trg_trainers_after_delete;
CREATE TRIGGER trg_trainers_after_delete
AFTER DELETE ON trainers
FOR EACH ROW
INSERT INTO audit_log (app_user, action, table_name, record_id, details)
VALUES (COALESCE(@app_user, 'system'), 'TRAINER_DELETED', 'trainers', OLD.trainer_id,
        CONCAT('Removed trainer ', OLD.full_name, ' (', OLD.specialization, ')'));
