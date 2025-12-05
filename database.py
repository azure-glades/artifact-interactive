import sqlite3
import json
from sqlite3 import Connection, Error

DATABASE_FILE = 'labels.db'

def get_db_connection() -> Connection:
    """Creates and returns a connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row # Allows fetching rows as dictionaries
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def init_db(app):
    """Initializes the database and creates the necessary table."""
    with app.app_context():
        conn = get_db_connection()
        if conn:
            try:
                # Create the 'labels' table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS labels (
                        id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
                print(f"Database initialized: {DATABASE_FILE}")
            except Error as e:
                print(f"Error initializing table: {e}")
            finally:
                conn.close()

def store_label_data(label_id: str, data: dict):
    """Stores the label ID and the JSON data (as a string) into the database."""
    conn = get_db_connection()
    if conn:
        try:
            # Serialize the Python dictionary into a JSON string
            json_data = json.dumps(data)
            
            conn.execute(
                "INSERT INTO labels (id, data) VALUES (?, ?)",
                (label_id, json_data)
            )
            conn.commit()
        except Error as e:
            print(f"Error storing data for ID {label_id}: {e}")
        finally:
            conn.close()

def get_label_data(label_id: str) -> dict or None:
    """Retrieves and deserializes the JSON data based on the label ID."""
    conn = get_db_connection()
    if conn:
        try:
            row = conn.execute(
                "SELECT data FROM labels WHERE id = ?", (label_id,)
            ).fetchone()
            
            if row:
                # Deserialize the JSON string back into a Python dictionary
                return json.loads(row['data'])
            return None
        except Error as e:
            print(f"Error retrieving data for ID {label_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for ID {label_id}: {e}")
            return None
        finally:
            conn.close()

# Example usage (uncomment if testing locally):
# if __name__ == '__main__':
#     # Note: This requires a Flask app context for init_db, 
#     # so it's best run via app.py
#     pass