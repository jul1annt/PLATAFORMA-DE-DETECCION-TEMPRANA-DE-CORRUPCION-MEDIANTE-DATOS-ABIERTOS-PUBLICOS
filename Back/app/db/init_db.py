import os
from sqlalchemy import text
from app.db.session import engine

def init_db():
    """Executes the init.sql script to ensure the schema is correct."""
    init_sql_path = os.path.join(os.path.dirname(__file__), "init.sql")
    
    if not os.path.exists(init_sql_path):
        print(f"Warning: init.sql not found at {init_sql_path}")
        return

    with open(init_sql_path, "r", encoding="utf-8") as file:
        sql_script = file.read()

    try:
        with engine.begin() as conn:
            # text() wrapper is used for executing raw SQL queries in sqlalchemy 2.0
            conn.execute(text(sql_script))
        print("Database initialized successfully from init.sql")
    except Exception as e:
        print(f"Error initializing database: {e}")
