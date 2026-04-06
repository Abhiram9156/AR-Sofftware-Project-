import sqlite3
import os

# Absolute path for PythonAnywhere compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'vguard.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Let us access columns by name
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Technicians Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    # Create Components Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stock_quantity INTEGER DEFAULT 0
        )
    ''')

    # Create Transactions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sr_number TEXT NOT NULL,
            technician_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            status TEXT NOT NULL, -- 'Issued', 'Used', 'Returned'
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (technician_id) REFERENCES technicians (id),
            FOREIGN KEY (component_id) REFERENCES components (id)
        )
    ''')

    # Seed data if empty
    
    # Upgrade Schema: Add quantity if it doesn't exist
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN quantity INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
