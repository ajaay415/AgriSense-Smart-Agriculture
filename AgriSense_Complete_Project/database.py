"""Database Management Module for AgriSense.

Provides SQLite persistence for user authentication (PBKDF2-HMAC-SHA256)
and full sensor cycle telemetry logging with automated migrations.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = Path(__file__).resolve().with_name("agrisense.db")


def connect() -> sqlite3.Connection:
    """Establish connection to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema and apply incremental column migrations."""
    with connect() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                pw TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Cycles / Telemetry table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                soil_moisture REAL,
                temperature REAL,
                humidity REAL,
                tank_level REAL,
                pump_state INTEGER NOT NULL,
                message TEXT,
                input_mode TEXT,
                crop_type TEXT DEFAULT 'General Crop',
                water_used_liters REAL DEFAULT 0.0,
                adc_count INTEGER DEFAULT 0,
                voltage REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Safe column migrations if database already existed with older schema
        cursor.execute("PRAGMA table_info(cycles)")
        existing_cols = {col["name"] for col in cursor.fetchall()}

        optional_cols = {
            "crop_type": "TEXT DEFAULT 'General Crop'",
            "water_used_liters": "REAL DEFAULT 0.0",
            "adc_count": "INTEGER DEFAULT 0",
            "voltage": "REAL DEFAULT 0.0",
        }

        for col, col_type in optional_cols.items():
            if col not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE cycles ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass

        conn.commit()

    # Pre-seed a default demo user for convenience during evaluations/viva
    seed_demo_account()


def _hash_password(password: str, salt_hex: str) -> str:
    """Hash password using PBKDF2 with SHA-256 and 150,000 iterations."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        150000,
    ).hex()


def seed_demo_account() -> None:
    """Seed default demo accounts if not already present."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", ("demo",))
        if cursor.fetchone() is None:
            salt = secrets.token_hex(16)
            pw_hash = _hash_password("agrisense123", salt)
            cursor.execute(
                "INSERT INTO users (username, salt, pw) VALUES (?, ?, ?)",
                ("demo", salt, pw_hash),
            )
            conn.commit()


def create_user(username: str, password: str) -> Tuple[bool, str]:
    """Register a new user account."""
    clean_username = username.strip()
    if len(clean_username) < 3:
        return False, "Username must contain at least 3 characters."
    if len(password) < 6:
        return False, "Password must contain at least 6 characters."

    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)

    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO users (username, salt, pw) VALUES (?, ?, ?)",
                (clean_username, salt, pw_hash),
            )
            conn.commit()
        return True, "Account created successfully. You may now sign in."
    except sqlite3.IntegrityError:
        return False, "Username is already registered. Please choose another."


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user."""
    clean_username = username.strip()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (clean_username,),
        ).fetchone()

    if not row:
        return None

    computed = _hash_password(password, row["salt"])
    if not secrets.compare_digest(row["pw"], computed):
        return None

    return {"id": row["id"], "username": row["username"]}


def save_cycle(
    user_id: int,
    reading: Dict[str, Any],
    pump_on: bool,
    message: str,
    input_mode: str,
    crop_type: str = "General Crop",
    water_used_liters: float = 0.0,
) -> None:
    """Log an irrigation and sensor telemetry cycle."""
    soil = reading.get("soil_moisture")
    temp = reading.get("temperature")
    hum = reading.get("humidity")
    tank = reading.get("tank_level")
    adc = reading.get("adc_soil_count", 0)
    volts = reading.get("adc_soil_voltage", 0.0)

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cycles (
                user_id, soil_moisture, temperature, humidity, tank_level,
                pump_state, message, input_mode, crop_type, water_used_liters,
                adc_count, voltage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                soil,
                temp,
                hum,
                tank,
                int(pump_on),
                message,
                input_mode,
                crop_type,
                water_used_liters,
                adc,
                volts,
            ),
        )
        conn.commit()


def get_cycles(user_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
    """Retrieve logged cycles for a specific user, ordered from newest to oldest."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, soil_moisture, temperature, humidity, tank_level,
                   pump_state, message, input_mode, crop_type, water_used_liters,
                   adc_count, voltage
            FROM cycles
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_statistics(user_id: int) -> Dict[str, Any]:
    """Compute aggregate analytics for summary dashboards and reports."""
    with connect() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            """
            SELECT
                COUNT(*) as total_cycles,
                SUM(pump_state) as pump_on_cycles,
                AVG(soil_moisture) as avg_moisture,
                AVG(temperature) as avg_temp,
                AVG(humidity) as avg_humidity,
                AVG(tank_level) as avg_tank,
                SUM(water_used_liters) as total_water
            FROM cycles
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if not row or row["total_cycles"] == 0:
        return {
            "total_cycles": 0,
            "pump_on_cycles": 0,
            "avg_moisture": 0.0,
            "avg_temp": 0.0,
            "avg_humidity": 0.0,
            "avg_tank": 0.0,
            "total_water": 0.0,
            "irrigation_ratio": 0.0,
        }

    total = row["total_cycles"]
    pump_on = row["pump_on_cycles"] or 0
    ratio = (pump_on / total) * 100.0 if total > 0 else 0.0

    return {
        "total_cycles": total,
        "pump_on_cycles": pump_on,
        "avg_moisture": round(row["avg_moisture"] or 0.0, 1),
        "avg_temp": round(row["avg_temp"] or 0.0, 1),
        "avg_humidity": round(row["avg_humidity"] or 0.0, 1),
        "avg_tank": round(row["avg_tank"] or 0.0, 1),
        "total_water": round(row["total_water"] or 0.0, 1),
        "irrigation_ratio": round(ratio, 1),
    }


def clear_cycles(user_id: int) -> None:
    """Delete all logged cycles for the specified user."""
    with connect() as conn:
        conn.execute("DELETE FROM cycles WHERE user_id = ?", (user_id,))
        conn.commit()
