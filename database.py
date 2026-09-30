"""
Database management module for Taiwan Weather Forecast
Handles SQLite database initialization, table creation, and queries.
Corresponds to Steps 8, 9, 10, and 12 in the course workflow.
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

DB_FILE = "data.db"

def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DB_FILE) -> None:
    """
    Step 8 & 9: Initialize SQLite database and create TemperatureForecasts table.
    Ensures idempotency with UNIQUE(regionName, dataDate) ON CONFLICT REPLACE (Step 20).
    Automatically migrates existing tables to add humidity, pop, rainfall, and pm25 columns.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL,
                dataDate TEXT NOT NULL,
                minT REAL NOT NULL,
                maxT REAL NOT NULL,
                weather TEXT DEFAULT '',
                humidity REAL DEFAULT 70.0,
                pop REAL DEFAULT 0.0,
                rainfall REAL DEFAULT 0.0,
                pm25 REAL DEFAULT 15.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(regionName, dataDate) ON CONFLICT REPLACE
            );
        """)
        
        # Schema migration check: Add new columns if table existed without them
        cursor.execute("PRAGMA table_info(TemperatureForecasts);")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        if "humidity" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN humidity REAL DEFAULT 70.0;")
        if "pop" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN pop REAL DEFAULT 0.0;")
        if "rainfall" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN rainfall REAL DEFAULT 0.0;")
        if "pm25" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN pm25 REAL DEFAULT 15.0;")

        conn.commit()

def save_forecasts(records: List[Dict[str, Any]], db_path: str = DB_FILE) -> int:
    """
    Step 8: Insert or replace forecast records into TemperatureForecasts table.
    Returns the number of records inserted/updated.
    """
    init_db(db_path)
    clean_records = []
    for r in records:
        clean_records.append({
            "regionName": r.get("regionName", ""),
            "dataDate": r.get("dataDate", ""),
            "minT": float(r.get("minT", 20.0)),
            "maxT": float(r.get("maxT", 28.0)),
            "weather": str(r.get("weather", "")),
            "humidity": float(r.get("humidity", 70.0)),
            "pop": float(r.get("pop", 0.0)),
            "rainfall": float(r.get("rainfall", 0.0)),
            "pm25": float(r.get("pm25", 15.0))
        })

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO TemperatureForecasts (regionName, dataDate, minT, maxT, weather, humidity, pop, rainfall, pm25)
            VALUES (:regionName, :dataDate, :minT, :maxT, :weather, :humidity, :pop, :rainfall, :pm25)
            ON CONFLICT(regionName, dataDate) DO UPDATE SET
                minT = excluded.minT,
                maxT = excluded.maxT,
                weather = excluded.weather,
                humidity = excluded.humidity,
                pop = excluded.pop,
                rainfall = excluded.rainfall,
                pm25 = excluded.pm25,
                created_at = CURRENT_TIMESTAMP;
        """, clean_records)
        conn.commit()
        return len(clean_records)

def query_distinct_regions(db_path: str = DB_FILE) -> List[str]:
    """
    Step 10: Query distinct regions using SQL.
    SELECT DISTINCT regionName FROM TemperatureForecasts;
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY id;")
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def query_cities_only(db_path: str = DB_FILE) -> List[str]:
    """Returns only the 22 cities and counties from the database."""
    all_locations = query_distinct_regions(db_path)
    return [loc for loc in all_locations if loc.endswith(("市", "縣"))]

def query_regional_divisions_only(db_path: str = DB_FILE) -> List[str]:
    """Returns only the 9 broad regional divisions from the database."""
    all_locations = query_distinct_regions(db_path)
    return [loc for loc in all_locations if loc.endswith("地區")]

def query_forecast_by_region(region_name: str, db_path: str = DB_FILE) -> pd.DataFrame:
    """
    Step 10 & 12: Query weather forecast for a specific region.
    SELECT * FROM TemperatureForecasts WHERE regionName = ?;
    """
    init_db(db_path)
    conn = get_connection(db_path)
    query = """
        SELECT dataDate, minT, maxT, weather, humidity, pop, rainfall, pm25 
        FROM TemperatureForecasts 
        WHERE regionName = ? 
        ORDER BY dataDate ASC
    """
    df = pd.read_sql_query(query, conn, params=(region_name,))
    conn.close()
    return df

def query_forecast_by_date(date_str: str, db_path: str = DB_FILE) -> pd.DataFrame:
    """
    Step 18: Query all regions forecast for a specific date.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    query = """
        SELECT regionName, dataDate, minT, maxT, weather, humidity, pop, rainfall, pm25 
        FROM TemperatureForecasts 
        WHERE dataDate = ?
        ORDER BY regionName ASC
    """
    df = pd.read_sql_query(query, conn, params=(date_str,))
    conn.close()
    return df

def query_all_forecasts(db_path: str = DB_FILE) -> pd.DataFrame:
    """
    Step 12: Read all forecasts into a Pandas DataFrame.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    query = "SELECT * FROM TemperatureForecasts ORDER BY regionName, dataDate ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_available_dates(db_path: str = DB_FILE) -> List[str]:
    """Retrieves unique forecast dates available in the database."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dataDate FROM TemperatureForecasts ORDER BY dataDate ASC;")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
