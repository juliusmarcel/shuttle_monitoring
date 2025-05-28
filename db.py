import pyodbc

def get_connection():
    try:
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=104.215.195.38;'  # IP kamu nanti diisi
            'DATABASE=ShuttleBus;'
            'UID=minipc;'       # ganti
            'PWD=minipc2025;'       # ganti
            
        )
        return conn
    except pyodbc.Error as e:
        print(f"Error connecting to database: {e}")
        raise