# IronPulse Fitness Club — Member & Subscription Management System

A desktop application (Python + CustomTkinter) backed by a **3NF MySQL / MariaDB database**, built for the
*Gym & Fitness Club Member & Subscription Management System* project proposal.

> 📘 **Want to understand the code?** Read [CODEBASE_GUIDE.md](CODEBASE_GUIDE.md) — architecture, how the
> database connection works, every table/view/trigger, and step-by-step walkthroughs of each feature.

---

## 🚀 Key Highlights

- **Real relational database**: a MySQL 8.0 / MariaDB schema (`sql/schema.sql`) with primary keys, foreign keys,
  UNIQUE, CHECK and ENUM constraints, B-Tree indexes and reporting views. Every query in `mysql_database.py`
  is parameterized (`%s` placeholders), so user input is never pasted into the SQL text.
- **Referential integrity enforced by InnoDB**:
  - `ON DELETE SET NULL`: deleting a trainer leaves their members unassigned.
  - `ON DELETE CASCADE`: deleting a member removes their subscription records.
  - `ON DELETE RESTRICT`: a package used by any subscription cannot be deleted.
- **Subscription lifecycle in SQL**: `end_date = DATE_ADD(start_date, INTERVAL duration_days DAY)`,
  remaining days via `DATEDIFF(end_date, CURDATE())`:
  - 🟢 **Active**: more than 7 days left
  - ⚠️ **Expiring Soon**: 0–7 days left (shown in the dashboard Action Center)
  - ❌ **Expired**: end date has passed
  - ➖ **No Plan**: member has never subscribed
- **Analytics**: total revenue, revenue by payment method, **monthly revenue for the last 6 months**,
  and trainer workload (active vs. total trainees).
- **Role-based access control** (Admin / Manager / Staff); see the table below.
- **Input validation**: phone format (7–15 digits), email format, dates, salary > 0, fee ≥ 0.
- **Emergency contacts** stored for each member.
- **Member profile & history**: double-click a member to see their status, lifetime spend, days purchased,
  contact / trainer / emergency details and full payment history, with shortcuts to edit or renew.
- **Audit log (database triggers)**: `sql/triggers.sql` records every payment, void, member change,
  price change and trainer removal in `audit_log`, including *which staff user* did it (the app sets the
  `@app_user` session variable before each write). Shown on the **Activity Log** page (Admin / Manager).
- **CSV export**: members, trainers, payments, the activity log and a full dashboard report export to
  `exports/` (Excel-friendly UTF-8; exports respect the current search and filters).
- **Offline fallback**: if MySQL is not reachable, the app runs on a local JSON file (`gym_data.json`)
  with the same rules imitated in Python, and shows which storage is in use in the sidebar.

---

## 🐳 Run with Docker (recommended)

Needs only Docker and an X11 desktop: no local Tk, Python packages or database setup.

```bash
./docker-run.sh            # builds the image, starts MariaDB + the app, opens the window
./docker-run.sh -d         # same, in the background
docker compose down        # stop (add -v to delete the database volume)
```

- `db`: MariaDB 11.4 with the `gym_db` database and `gym_app` user; data lives in the `gym_db_data` volume.
  It is reachable from the host on `127.0.0.1:3307` (`mysql -h 127.0.0.1 -P 3307 -u gym_app -pgym_pass gym_db`).
- `app`: the GUI, running as your own UID. `docker-run.sh` runs `xhost +SI:localuser:$USER` so
  only your user can draw on the display. It falls back to the system Docker daemon if
  Docker Desktop isn't running.

---

## 💻 Setup & Run (without Docker)

### 1. Install system packages (Arch Linux)

```bash
sudo pacman -S tk mariadb          # Tk is required by tkinter / CustomTkinter
```

(Ubuntu/Debian: `sudo apt install python3-tk python3-venv mariadb-server`)

### 2. Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Create the database and application user (one time)

```bash
sudo mariadb < sql/setup_mysql.sql        # or: mysql -u root -p < sql/setup_mysql.sql
```

This creates the database `gym_db` and the user `gym_app` / `gym_pass`. Tables, views and demo data are
created automatically the first time the app starts. To do it by hand instead:

```bash
mysql -u gym_app -p gym_db < sql/schema.sql
mysql -u gym_app -p gym_db < sql/triggers.sql
mysql -u gym_app -p gym_db < sql/seed.sql
```

### 4. Run

```bash
./run.sh            # uses .venv automatically if present
# or
.venv/bin/python main.py
```

### Configuration (optional)

Copy `db_config.example.json` to `db_config.json` to change the connection settings, or use environment variables:

| Setting | `db_config.json` key | Environment variable | Default |
| :--- | :--- | :--- | :--- |
| Backend | `backend` | `GYM_DB_BACKEND` | `auto` (MySQL, falls back to JSON) |
| Host / port | `host`, `port` | `GYM_DB_HOST`, `GYM_DB_PORT` | `localhost`, `3306` |
| User / password | `user`, `password` | `GYM_DB_USER`, `GYM_DB_PASSWORD` | `gym_app`, `gym_pass` |
| Database | `database` | `GYM_DB_NAME` | `gym_db` |
| Unix socket | `unix_socket` | `GYM_DB_SOCKET` | none |

Use `backend: "mysql"` to make startup fail loudly instead of falling back, or `"json"` to skip MySQL entirely.

---

## 🪟 Windows

| Method | Steps |
| :--- | :--- |
| **Python (simplest)** | Install [Python 3.12](https://www.python.org/downloads/) with *Add Python to PATH*, then double-click **`run.bat`** (first run installs the requirements into `.venv`). For MySQL, install MySQL 8 / MariaDB and run `mysql -u root -p < sql\setup_mysql.sql` once; otherwise the app uses `gym_data.json`. |
| **Docker Desktop** | Install [VcXsrv](https://sourceforge.net/projects/vcxsrv/), start *XLaunch* (Multiple windows → Start no client → tick **Disable access control**), then double-click **`docker-run.bat`**. Stop with `docker compose down`. |
| **WSL2 (Windows 11)** | In an Ubuntu WSL terminal inside the project folder run `./docker-run.sh -d` — WSLg shows the window like on Linux. |

Log timestamps in Docker use UTC on Windows unless you `set TZ=Asia/Dhaka` (any IANA zone) before `docker-run.bat`.

---

## 🔑 Login Credentials & Permissions

Passwords are stored as SHA-256 hashes (`SHA2(pwd, 256)` in the seed script). The login screen has
one-click demo buttons for each role.

| Role | Username | Password |
| :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` |
| **Manager** | `manager` | `manager123` |
| **Staff** | `staff` | `staff123` |

| Action | Admin | Manager | Staff |
| :--- | :---: | :---: | :---: |
| Register / edit members | ✅ | ✅ | ✅ |
| Record payments & renewals | ✅ | ✅ | ✅ |
| Delete members | ✅ | ✅ | ❌ |
| Add / edit / delete trainers & packages | ✅ | ✅ | ❌ |
| Void ledger transactions | ✅ | ✅ | ❌ |
| View member profiles | ✅ | ✅ | ✅ |
| Activity log & CSV export | ✅ | ✅ | ❌ |
| Reset demo data | ✅ | ❌ | ❌ |

Permissions are defined in one place: `ROLE_PERMISSIONS` in `common.py`.

---

## 🗄️ Database Schema (3NF)

| Table | PK | Main attributes | Key constraints |
| :--- | :--- | :--- | :--- |
| `users` | `user_id` | username, password_hash, role, full_name | username UNIQUE, role ENUM |
| `trainers` | `trainer_id` | full_name, phone, specialization, monthly_salary, hire_date | phone UNIQUE, salary > 0 |
| `packages` | `package_id` | package_name, duration_days, fee, description | name UNIQUE, duration > 0, fee ≥ 0 |
| `members` | `member_id` | full_name, phone, email, gender, join_date, emergency_contact_name, emergency_contact_phone, trainer_id | phone UNIQUE, gender ENUM, FK → trainers (SET NULL) |
| `audit_log` | `log_id` | event_time, app_user, action, table_name, record_id, details | no FKs on purpose (history survives deletes) |
| `subscriptions` | `sub_id` | member_id, package_id, payment_date, start_date, end_date, amount_paid, payment_method | FK → members (CASCADE), FK → packages (RESTRICT), amount ≥ 0, end > start, method ENUM |

**Views**
- `v_latest_subscription`: each member's most recent plan (`ROW_NUMBER() OVER (PARTITION BY member_id ...)`).
- `v_member_overview`: member + trainer + latest package with computed status (LEFT JOINs, `CASE`, `DATEDIFF`).

**Triggers** (`sql/triggers.sql`): `AFTER INSERT/DELETE ON subscriptions`, `AFTER INSERT/UPDATE/DELETE ON members`,
`AFTER UPDATE ON packages` (only when the fee changes, via `INSERT ... SELECT ... WHERE OLD.fee <> NEW.fee`),
`AFTER DELETE ON trainers`. Rows removed by `ON DELETE CASCADE` don't fire triggers in MySQL, so a member
deletion is logged once by the member trigger.

**Indexes**: `members.full_name`, `members.phone` (UNIQUE), `subscriptions.end_date`, `subscriptions.payment_date`.

### Where each DBMS concept is used

| Concept | Where |
| :--- | :--- |
| INNER / LEFT JOIN | `v_member_overview`, `get_all_subscriptions_detailed()`, `get_all_trainers()` |
| `DATE_ADD`, `DATE_SUB`, `DATEDIFF`, `CURDATE` | `add_subscription()`, views, `seed.sql` |
| `COUNT`, `SUM`, `GROUP BY`, `HAVING`, `GROUP_CONCAT` | `get_dashboard_metrics()`, `get_monthly_revenue()`, `get_all_trainers()`, `get_all_packages()` |
| `INSERT ... SELECT` | `add_subscription()` (end date calculated by the DB from the package duration) |
| `GREATEST` / `COALESCE` | `get_renewal_start_date()` (renewal continues from the current plan's end date) |
| Window function | `v_latest_subscription` |
| Triggers + session variables | `sql/triggers.sql`, `@app_user` set in `_execute()` |
| Constraint errors → friendly messages | `_friendly_error()` in `mysql_database.py` |

---

## 📂 Project Structure

```
Gym/
├── main.py                 # App window, sidebar navigation, theme, role checks
├── bootstrap.py            # Optional loader for user-space Tk libraries
├── run.sh                  # Launcher (uses .venv if present)
├── run.bat                 # Windows launcher (creates .venv on first run)
├── docker-run.bat          # Windows Docker launcher (needs VcXsrv)
├── requirements.txt
├── Dockerfile              # GUI app image (python:3.12-slim + Tk)
├── docker-compose.yml      # MariaDB + app services
├── docker-run.sh           # One-command Docker launcher (X11 access + compose up)
├── db_factory.py           # Picks MySQL or JSON backend from config/env
├── db_config.example.json  # Connection settings template
├── mysql_database.py       # MySQL/MariaDB data layer (parameterized SQL)
├── database.py             # JSON fallback data layer (same interface)
├── common.py               # Validation, status/date helpers, role permissions
├── gym_data.json           # JSON fallback data file
├── exports/                # CSV exports land here (mounted into the Docker container)
├── sql/
│   ├── setup_mysql.sql     # CREATE DATABASE + application user (run once as admin)
│   ├── schema.sql          # Tables, constraints, indexes, views
│   ├── triggers.sql        # Audit triggers -> audit_log
│   └── seed.sql            # Demo data (dates relative to CURDATE())
└── ui/
    ├── theme.py            # Colors and table styling
    ├── dialogs.py          # Member / Trainer / Package / Payment forms, confirm & message boxes
    └── views/
        ├── login_view.py
        ├── dashboard_view.py   # KPIs, expiring alerts, revenue by method & month, trainer workload
        ├── members_view.py     # Member CRUD, search, status/trainer filters
        ├── trainers_view.py    # Trainer CRUD, payroll, active/total trainees
        ├── packages_view.py    # Package CRUD (ON DELETE RESTRICT)
        ├── billing_view.py     # Payment ledger, renewals, void entries
        └── activity_view.py    # Audit log (trigger output), filters, export
```
