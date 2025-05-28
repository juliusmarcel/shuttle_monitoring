from db import get_connection
from datetime import datetime, time


def parse_checkin_time(checkin_time, record_date):
    """Helper function to parse various time formats"""
    if checkin_time is None:
        return time(0, 0)  # Default to midnight if no time
    
    try:
        if isinstance(checkin_time, str):
            # Remove any whitespace
            time_str = checkin_time.strip()
            
            # Handle cases where the string might contain both date and time
            if ' ' in time_str:
                # Split into date and time parts
                parts = time_str.split()
                if len(parts) >= 2:
                    # Take the last part as the time
                    time_str = parts[-1]
            
            # Now parse the time part
            time_parts = time_str.split(':')
            
            if len(time_parts) == 1:  # Just hour
                return time(int(time_parts[0]), 0)
            elif len(time_parts) == 2:  # Hour and minute
                return time(int(time_parts[0]), int(time_parts[1]))
            elif len(time_parts) == 3:  # Hour, minute, second
                return time(int(time_parts[0]), int(time_parts[1]), int(time_parts[2]))
        elif isinstance(checkin_time, time):
            return checkin_time
    except Exception as e:
        print(f"Error parsing time {checkin_time}: {e}")
    
    return time(0, 0)  # Fallback to midnight

def get_all_mapping():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT EmployeeNIP, Nama FROM V_Attendance_Log")
    rows = cursor.fetchall()
    conn.close()
    return [{"nip": row.EmployeeNIP, "nama": row.Nama} for row in rows]


def get_distinct_employees():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT 
            EmployeeNIP, 
            Nama,
            COUNT(*) as total_absensi
        FROM V_Attendance_Log
        GROUP BY EmployeeNIP, Nama
        ORDER BY Nama
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    employees = []
    for row in rows:
        employees.append({
            "nip": row.EmployeeNIP,
            "nama": row.Nama,
            "total_absensi": row.total_absensi
        })
    
    return employees

def get_all_logs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            Bus, 
            RecordDate, 
            CheckInTime, 
            EmployeeNIP, 
            Nama 
        FROM V_Attendance_Log 
        ORDER BY RecordDate DESC, CheckInTime DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    logs = []
    for row in rows:
        try:
            # Parse date and time separately
            date_part = row.RecordDate
            time_part = parse_checkin_time(row.CheckInTime, row.RecordDate)
            
            # Combine into datetime
            dt = datetime.combine(date_part, time_part)
            
            logs.append({
                "shuttle_id": row.Bus,
                "waktu_absen": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "dt_obj": dt,
                "date_only": dt.strftime("%A, %d %B %Y"),  # Tanggal saja
                "time_only": dt.strftime("%H:%M:%S"),       # Waktu saja
                "waktu_absen_formatted": dt.strftime("%A, %d %B %Y %H:%M:%S"),
                "nip": row.EmployeeNIP,
                "nama": row.Nama,
                "departemen": "N/A",
                "mapping_shuttle": row.Bus
            })
        except Exception as e:
            print(f"Error processing log (NIP: {row.EmployeeNIP}): {e}")
            continue
            
    return logs

def get_log_by_shuttle(shuttle_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            Bus, 
            RecordDate, 
            CheckInTime, 
            EmployeeNIP, 
            Nama 
        FROM V_Attendance_Log 
        WHERE Bus = ? 
        ORDER BY RecordDate DESC, CheckInTime DESC
    """, (shuttle_id,))
    rows = cursor.fetchall()
    conn.close()

    logs = []
    for row in rows:
        try:
            # Parse date and time separately
            date_part = row.RecordDate
            time_part = parse_checkin_time(row.CheckInTime, row.RecordDate)
            
            # Combine into datetime
            dt = datetime.combine(date_part, time_part)
            
            logs.append({
                "shuttle_id": row.Bus,
                "waktu_absen": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "dt_obj": dt,
                "waktu_absen_formatted": dt.strftime("%A, %d %B %Y %H:%M:%S"),
                "nip": row.EmployeeNIP,
                "nama": row.Nama,
                "departemen": "N/A",
                "mapping_shuttle": row.Bus
            })
        except Exception as e:
            print(f"Error processing log (NIP: {row.EmployeeNIP}): {e}")
            continue
            
    return logs


def get_bus_data(start_date=None, end_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if start_date and end_date:
        # Query with date range
        cursor.execute("""
            SELECT 
                Bus, 
                COUNT(DISTINCT EmployeeNIP) as total_tap
            FROM V_Attendance_Log
            WHERE RecordDate BETWEEN ? AND ?
            GROUP BY Bus
            ORDER BY Bus
        """, (start_date, end_date))
    else:
        # Query without date range
        cursor.execute("""
            SELECT 
                Bus, 
                COUNT(DISTINCT EmployeeNIP) as total_tap
            FROM V_Attendance_Log
            GROUP BY Bus
            ORDER BY Bus
        """)
    
    rows = cursor.fetchall()
    conn.close()
    
    buses = []
    for row in rows:
        buses.append({
            "bus_id": row.Bus,
            "total_tap": row.total_tap
        })
    
    return buses

def get_first_checkins(start_date=None, end_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    base_query = """
        SELECT 
            val.Bus,
            val.EmployeeNIP,
            val.Nama,
            val.RecordDate,
            MIN(val.CheckInTime) as FirstCheckInTime
        FROM V_Attendance_Log val
    """
    
    where_clause = ""
    params = ()
    
    if start_date and end_date:
        where_clause = " WHERE val.RecordDate BETWEEN ? AND ?"
        params = (start_date, end_date)
    
    query = base_query + where_clause + """
        GROUP BY 
            val.EmployeeNIP,
            val.Nama,
            val.RecordDate,
            val.Bus
        ORDER BY 
            val.RecordDate DESC, 
            FirstCheckInTime ASC
    """
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    logs = []
    for row in rows:
        try:
            date_part = row.RecordDate
            time_part = parse_checkin_time(row.FirstCheckInTime, row.RecordDate)
            dt = datetime.combine(date_part, time_part)
            
            logs.append({
                "shuttle_id": row.Bus,
                "waktu_absen": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "dt_obj": dt,
                "date_only": dt.strftime("%A, %d %B %Y"),
                "time_only": dt.strftime("%H:%M:%S"),
                "waktu_absen_formatted": dt.strftime("%A, %d %B %Y %H:%M:%S"),
                "nip": row.EmployeeNIP,
                "nama": row.Nama,
                "departemen": "N/A"
            })
        except Exception as e:
            print(f"Error processing first check-in (NIP: {row.EmployeeNIP}): {e}")
            continue
            
    return logs


def get_bus_activity():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT distinct Hostname,
            CASE
                WHEN DATEPART(MINUTE, LastSync) >= 0 AND DATEPART(MINUTE, LastSync) < 15 THEN
                    DATEADD(MINUTE, 0, DATEADD(HOUR, DATEDIFF(HOUR, 0, LastSync), 0))
                WHEN DATEPART(MINUTE, LastSync) >= 15 AND DATEPART(MINUTE, LastSync) < 30 THEN
                    DATEADD(MINUTE, 15, DATEADD(HOUR, DATEDIFF(HOUR, 0, LastSync), 0))
                WHEN DATEPART(MINUTE, LastSync) >= 30 AND DATEPART(MINUTE, LastSync) < 45 THEN
                    DATEADD(MINUTE, 30, DATEADD(HOUR, DATEDIFF(HOUR, 0, LastSync), 0))
                WHEN DATEPART(MINUTE, LastSync) >= 45 AND DATEPART(MINUTE, LastSync) <= 59 THEN
                    DATEADD(MINUTE, 45, DATEADD(HOUR, DATEDIFF(HOUR, 0, LastSync), 0))
                ELSE LastSync
            END AS IsSync
        FROM Log_Device
        ORDER BY Hostname, IsSync DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    # Format data untuk ditampilkan
    bus_activities = []
    for row in rows:
        bus_activities.append({
            "hostname": row.Hostname,
            "last_sync": row.IsSync.strftime("%Y-%m-%d %H:%M:%S") if row.IsSync else "Never",
            "status": "Active" if is_recent(row.IsSync) else "Inactive"
        })
    
    return bus_activities

def is_recent(last_sync, threshold_minutes=30):
    """Check if last sync is within threshold minutes"""
    if not last_sync:
        return False
        
    now = datetime.now()
    delta = now - last_sync
    return delta.total_seconds() / 60 <= threshold_minutes

def get_bus_activity_matrix(date_filter=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Query yang diperbaiki
    query = """
        WITH TimeIntervals AS (
            SELECT 
                DATEADD(MINUTE, (DATEDIFF(MINUTE, '2000-01-01', LastSync)/15)*15, '2000-01-01') AS TimeInterval,
                Hostname
            FROM Log_Device
            {date_condition}
        )
        SELECT 
            Distinct Hostname,
            CONVERT(VARCHAR, TimeInterval, 120) AS TimeInterval,
            COUNT(*) AS SyncCount
        FROM TimeIntervals
        GROUP BY Hostname, TimeInterval
        ORDER BY Hostname, TimeInterval
    """
    
    date_condition = ""
    params = ()
    if date_filter:
        date_condition = "WHERE CONVERT(DATE, LastSync) = ?"
        params = (date_filter,)
    
    # Replace the placeholder with actual condition
    final_query = query.format(date_condition=date_condition)
    
    cursor.execute(final_query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return rows


def check_login(username, password):
    return username == "admin" and password == "admin123"