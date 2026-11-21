"""
Chooses the storage backend at startup.

Settings come from db_config.json (copy db_config.example.json) and can be
overridden with environment variables:
    GYM_DB_BACKEND   auto | mysql | json   (default: auto)
    GYM_DB_HOST, GYM_DB_PORT, GYM_DB_USER, GYM_DB_PASSWORD, GYM_DB_NAME, GYM_DB_SOCKET

backend = "auto"  -> try MySQL, fall back to the JSON file if it is unreachable
backend = "mysql" -> MySQL only (startup fails with the connection error)
backend = "json"  -> JSON file only
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "db_config.json")

DEFAULTS = {
    "backend": "auto",
    "host": "localhost",
    "port": 3306,
    "user": "gym_app",
    "password": "gym_pass",
    "database": "gym_db",
    "unix_socket": None,
}

ENV_MAP = {
    "GYM_DB_BACKEND": "backend",
    "GYM_DB_HOST": "host",
    "GYM_DB_PORT": "port",
    "GYM_DB_USER": "user",
    "GYM_DB_PASSWORD": "password",
    "GYM_DB_NAME": "database",
    "GYM_DB_SOCKET": "unix_socket",
}


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    for env, key in ENV_MAP.items():
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    cfg["backend"] = str(cfg.get("backend", "auto")).lower()
    return cfg


def create_database():
    """Return (db, warning). warning is a message when MySQL was wanted but unavailable."""
    cfg = load_config()
    backend = cfg.pop("backend")

    if backend in ("auto", "mysql"):
        try:
            from mysql_database import MySQLGymDatabase
            return MySQLGymDatabase(**cfg), None
        except Exception as e:  # ImportError, connection errors, ...
            if backend == "mysql":
                raise
            warning = (
                f"Could not connect to MySQL ({type(e).__name__}: {e}).\n"
                f"Running on the local JSON file instead."
            )
            print(f"[IronPulse] {warning}")
            from database import GymDatabase
            return GymDatabase(), warning

    from database import GymDatabase
    return GymDatabase(), None
