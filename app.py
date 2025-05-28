from flask import Flask, render_template, request, redirect, url_for, session
from auth import check_login, get_all_mapping, get_all_logs, get_log_by_shuttle, get_distinct_employees, get_bus_data, get_first_checkins, get_bus_activity, get_bus_activity_matrix
import os
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if check_login(username, password):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/log")
def all_log_karyawan():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    filter_type = request.args.get("filter_type", "all")
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    logs = get_all_logs()
    filtered_logs = []
    today = date.today()

    for log in logs:
        dt = datetime.strptime(log["waktu_absen"], "%Y-%m-%d %H:%M:%S")
        log["dt_obj"] = dt
        log["waktu_absen_formatted"] = dt.strftime("%A, %d %B %Y %H:%M:%S")

    if filter_type == "today":
        filtered_logs = [log for log in logs if log["dt_obj"].date() == today]
    elif filter_type == "this_week":
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        filtered_logs = [log for log in logs if start_of_week <= log["dt_obj"].date() <= end_of_week]
    elif filter_type == "this_month":
        filtered_logs = [log for log in logs if log["dt_obj"].year == today.year and log["dt_obj"].month == today.month]
    elif filter_type == "this_year":
        filtered_logs = [log for log in logs if log["dt_obj"].year == today.year]
    elif filter_type == "date_range" and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            filtered_logs = [log for log in logs if start_date <= log["dt_obj"].date() <= end_date]
        except Exception:
            filtered_logs = logs
    else:
        filtered_logs = logs

    total_absen = len(filtered_logs)

    return render_template("log_karyawan.html",
        logs=filtered_logs,
        filter_type=filter_type,
        start_date=start_date_str,
        end_date=end_date_str,
        total_absen=total_absen
    )



@app.route('/dashboard')
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    filter_type = request.args.get("filter_type", "all")
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    time_range = request.args.get("time_range", "all")
    search_query = request.args.get("search", "").lower()
    first_checkin = request.args.get("first_checkin", "false").lower() == "true"

    try:
        # Gunakan fungsi yang berbeda berdasarkan first_checkin
        if first_checkin:
            logs = get_first_checkins()
        else:
            logs = get_all_logs()

        filtered_logs = []
        today = date.today()

        # Apply date filters
        if filter_type == "today":
            filtered_logs = [log for log in logs if log["dt_obj"].date() == today]
        elif filter_type == "this_week":
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            filtered_logs = [log for log in logs if start_of_week <= log["dt_obj"].date() <= end_of_week]
        elif filter_type == "this_month":
            filtered_logs = [log for log in logs if log["dt_obj"].year == today.year and log["dt_obj"].month == today.month]
        elif filter_type == "this_year":
            filtered_logs = [log for log in logs if log["dt_obj"].year == today.year]
        elif filter_type == "date_range" and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                filtered_logs = [log for log in logs if start_date <= log["dt_obj"].date() <= end_date]
            except ValueError:
                filtered_logs = logs
        else:
            filtered_logs = logs

        # Apply time filter
        if time_range != "all":
            hour_ranges = {
                "morning": (6, 12),
                "afternoon": (12, 18),
                "evening": (18, 24),
                "night": (0, 6)
            }
            if time_range in hour_ranges:
                start_hour, end_hour = hour_ranges[time_range]
                filtered_logs = [
                    log for log in filtered_logs 
                    if start_hour <= log["dt_obj"].hour < end_hour
                ]

        # Apply search if query exists
        if search_query:
            filtered_logs = [
                log for log in filtered_logs
                if (search_query in log["nip"].lower() or
                    search_query in log["nama"].lower() or
                    search_query in log["shuttle_id"].lower() or
                    search_query in log["date_only"].lower() or
                    search_query in log["time_only"].lower())
            ]

        total_absen = len(filtered_logs)

        # =============================================
        # Kode statistik tambahan dimulai dari sini
        # =============================================
        
        # Hitung statistik tambahan
        unique_employees = len({log['nip'] for log in filtered_logs})
        active_shuttles = len({log['shuttle_id'] for log in filtered_logs})

        # Data untuk chart waktu
        time_data = {
            'morning': len([log for log in filtered_logs if 6 <= log['dt_obj'].hour < 12]),
            'afternoon': len([log for log in filtered_logs if 12 <= log['dt_obj'].hour < 18]),
            'evening': len([log for log in filtered_logs if 18 <= log['dt_obj'].hour < 24]),
            'night': len([log for log in filtered_logs if 0 <= log['dt_obj'].hour < 6])
        }

        # Data untuk chart shuttle
        shuttle_counts = {}
        for log in filtered_logs:
            shuttle_counts[log['shuttle_id']] = shuttle_counts.get(log['shuttle_id'], 0) + 1
        
        # Ambil top 5 shuttle
        sorted_shuttles = sorted(shuttle_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        shuttle_names = [s[0] for s in sorted_shuttles]
        shuttle_values = [s[1] for s in sorted_shuttles]

        # Data untuk chart harian
        daily_counts = {}
        for log in filtered_logs:
            date_str = log['dt_obj'].strftime('%Y-%m-%d')
            daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
        
        daily_labels = sorted(daily_counts.keys())
        daily_values = [daily_counts[d] for d in daily_labels]

        # Data untuk chart departemen (pastikan log memiliki field 'departemen')
        dept_data = {
            'IT': len([log for log in filtered_logs if log.get('departemen', '').startswith('IT')]),
            'HR': len([log for log in filtered_logs if log.get('departemen', '').startswith('HR')]),
            'Finance': len([log for log in filtered_logs if log.get('departemen', '').startswith('Finance')]),
            'Operations': len([log for log in filtered_logs if log.get('departemen', '').startswith('Operations')]),
            'Other': len([log for log in filtered_logs if not log.get('departemen', '').startswith(('IT', 'HR', 'Finance', 'Operations'))])
        }
        dept_labels = list(dept_data.keys())
        dept_values = list(dept_data.values())

        unique_employees_last_5_days = []
        dates_last_5_days = []
        for i in range(5):
            day = today - timedelta(days=(4-i))  # Mulai dari 4 hari lalu sampai hari ini
            dates_last_5_days.append(day.strftime('%d/%m'))  # Format tanggal menjadi DD/MM
            day_logs = [log for log in filtered_logs if log['dt_obj'].date() == day]
            unique_employees_last_5_days.append(len({log['nip'] for log in day_logs}))


        return render_template("dashboard.html",
            logs=filtered_logs,
            filter_type=filter_type,
            time_range=time_range,
            start_date=start_date_str,
            end_date=end_date_str,
            search_query=search_query,
            total_absen=total_absen,
            first_checkin=first_checkin,
            # Data statistik tambahan
            unique_employees=unique_employees,
            active_shuttles=active_shuttles,
            time_data=time_data,
            shuttle_names=shuttle_names,
            shuttle_values=shuttle_values,
            daily_labels=daily_labels,
            daily_values=daily_values,
            dept_labels=dept_labels,
            dept_values=dept_values,
            unique_employees_last_5_days=unique_employees_last_5_days,
            dates_last_5_days=dates_last_5_days
        )

    except Exception as e:
        print(f"Error in dashboard route: {e}")
        return render_template("dashboard.html",
            logs=[],
            filter_type=filter_type,
            time_range=time_range,
            start_date=start_date_str,
            end_date=end_date_str,
            search_query=search_query,
            total_absen=0,
            error=str(e),
            first_checkin=first_checkin,
            # Default values untuk statistik saat error
            unique_employees=0,
            active_shuttles=0,
            time_data={},
            shuttle_names=[],
            shuttle_values=[],
            daily_labels=[],
            daily_values=[],
            dept_labels=[],
            dept_values=[]
        )

@app.route("/mapping")
def mapping_karyawan():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    employees = get_distinct_employees()
    total_employees = len(employees)

    return render_template("mapping_karyawan.html",
        employees=employees,
        total_employees=total_employees
    )

@app.route("/data_bus")
def data_bus():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    # Parse dates if provided
    start_date = None
    end_date = None
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except Exception as e:
            print(f"Error parsing dates: {e}")

    # Get bus data with optional date filtering
    buses = get_bus_data(start_date, end_date)
    total_buses = len(buses)

    return render_template("data_bus.html",
        buses=buses,
        total_buses=total_buses,
        start_date=start_date_str if start_date_str else "",
        end_date=end_date_str if end_date_str else ""
    )

@app.route("/shuttle/<shuttle_id>/log")
def shuttle_log_karyawan(shuttle_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    filter_type = request.args.get("filter_type", "all")
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    try:
        logs = get_log_by_shuttle(shuttle_id)
        filtered_logs = []
        today = date.today()

        # Apply filters
        if filter_type == "today":
            filtered_logs = [log for log in logs if log["dt_obj"].date() == today]
        elif filter_type == "this_week":
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            filtered_logs = [log for log in logs if start_of_week <= log["dt_obj"].date() <= end_of_week]
        elif filter_type == "this_month":
            filtered_logs = [log for log in logs if log["dt_obj"].year == today.year and log["dt_obj"].month == today.month]
        elif filter_type == "date_range" and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                filtered_logs = [log for log in logs if start_date <= log["dt_obj"].date() <= end_date]
            except ValueError:
                filtered_logs = logs
        else:
            filtered_logs = logs

        total_absen = len(filtered_logs)

        return render_template(
            "log_karyawan.html",
            logs=filtered_logs,
            shuttle_id=shuttle_id,
            filter_type=filter_type,
            start_date=start_date_str,
            end_date=end_date_str,
            total_absen=total_absen
        )

    except Exception as e:
        print(f"Error in shuttle log route: {e}")
        return render_template(
            "log_karyawan.html",
            logs=[],
            shuttle_id=shuttle_id,
            filter_type=filter_type,
            start_date=start_date_str,
            end_date=end_date_str,
            total_absen=0,
            error=str(e)
        )

@app.route("/bus_monitoring")
def bus_monitoring():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    bus_activities = get_bus_activity()
    
    # Hitung status bus
    active_buses = sum(1 for bus in bus_activities if bus['status'] == 'Active')
    inactive_buses = len(bus_activities) - active_buses
    
    return render_template("bus_monitoring.html",
        bus_activities=bus_activities,
        active_buses=active_buses,
        inactive_buses=inactive_buses,
        total_buses=len(bus_activities),
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

@app.route("/bus_matrix")
def bus_matrix():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Ambil parameter filter
    date_filter = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    bus_search = request.args.get("bus_search", "").lower()
    
    # Dapatkan data matrix
    matrix_data = get_bus_activity_matrix(date_filter)
    
    # Proses data untuk matrix
    all_bus_names = sorted(list(set(row.Hostname for row in matrix_data)))
    all_time_intervals = sorted(list(set(row.TimeInterval for row in matrix_data)))
    
    # Filter bus berdasarkan search (jika ada)
    if bus_search:
        bus_names = [bus for bus in all_bus_names if bus_search in bus.lower()]
    else:
        bus_names = all_bus_names
    
    # Buat matrix dictionary
    matrix = {}
    for bus in all_bus_names:
        matrix[bus] = {}
        for interval in all_time_intervals:
            matrix[bus][interval] = 0
    
    # Isi matrix dengan data
    for row in matrix_data:
        matrix[row.Hostname][row.TimeInterval] = row.SyncCount
    
    return render_template("bus_matrix.html",
        bus_names=bus_names,
        all_bus_names=all_bus_names,  # Untuk keperluan UI
        time_intervals=all_time_intervals,
        matrix=matrix,
        current_date=date_filter,
        bus_search=bus_search,
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)