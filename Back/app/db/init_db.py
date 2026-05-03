import os
from sqlalchemy import text
from app.db.session import engine

def init_db():
    """Executes the initialization scripts to ensure the schema is correct."""
    init_sql_path = os.path.join(os.path.dirname(__file__), "init.sql")
    epic2_sql_path = os.path.join(os.path.dirname(__file__), "epic2_init.sql")
    
    scripts_to_run = []
    
    if os.path.exists(init_sql_path):
        with open(init_sql_path, "r", encoding="utf-8") as file:
            scripts_to_run.append(file.read())
    else:
        print(f"Warning: init.sql not found at {init_sql_path}")
        
    if os.path.exists(epic2_sql_path):
        with open(epic2_sql_path, "r", encoding="utf-8") as file:
            scripts_to_run.append(file.read())
    else:
        print(f"Warning: epic2_init.sql not found at {epic2_sql_path}")

    try:
        with engine.begin() as conn:
            for sql_script in scripts_to_run:
                conn.execute(text(sql_script))
        print("Database initialized successfully from scripts.")
    except Exception as e:
        print(f"Error initializing database: {e}")
