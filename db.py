import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{{os.getenv('DB_DRIVER')}}};"
            f"SERVER={os.getenv('DB_SERVER')};"
            f"DATABASE={os.getenv('DB_NAME')};"
            f"UID={os.getenv('DB_USER')};"
            f"PWD={os.getenv('DB_PASSWORD')};"
        )
        return conn
    except pyodbc.Error as e:
        print(f"Error connecting to database: {e}")
        raise
