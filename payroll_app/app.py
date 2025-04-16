import os
from flask import Flask, render_template, request
import pandas as pd
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

HOURLY_RATE = 76.25
BREAK_DURATION = 1
REGULAR_HOURS_CAP = 9

def parse_time(row, col_date, col_time):
    try:
        date_str = str(row[col_date]).strip()
        time_str = str(row[col_time]).strip()
        if pd.isna(date_str) or pd.isna(time_str):
            return None

        for fmt in ["%m/%d/%Y %I:%M %p", "%Y-%m-%d %I:%M %p"]:
            try:
                return datetime.strptime(f"{date_str} {time_str}", fmt)
            except ValueError:
                continue
        return None
    except:
        return None

def compute_hours(start, end):
    if not start or not end:
        return 0
    duration = (end - start).total_seconds() / 3600
    return max(0, duration)

def compute_pay(records):
    payroll_data = defaultdict(lambda: defaultdict(list))
    total_pay = 0
    employee_totals = defaultdict(float)
    parsed_rows = 0
    skipped_rows = 0

    for _, row in records.iterrows():
        name = str(row['Staff']).strip()
        time_in = parse_time(row, 'In Date', 'In Time')
        time_out = parse_time(row, 'Out Date', 'Out time')
        break_in = parse_time(row, 'Break In Date', 'Break In Time')
        break_out = parse_time(row, 'Break Out Date', 'Break Out time')

        if not time_in or not time_out:
            skipped_rows += 1
            continue

        total_hrs = compute_hours(time_in, time_out)
        break_hrs = compute_hours(break_in, break_out)

        if total_hrs >= 5:
            break_hrs = max(break_hrs, BREAK_DURATION)

        worked_hrs = max(0, total_hrs - break_hrs)
        reg_hrs = min(int(worked_hrs), REGULAR_HOURS_CAP)
        ot_hrs = max(int(worked_hrs) - REGULAR_HOURS_CAP, 0)

        reg_pay = reg_hrs * HOURLY_RATE
        ot_pay = ot_hrs * HOURLY_RATE
        pay = reg_pay + ot_pay
        total_pay += pay
        employee_totals[name] += pay

        parsed_rows += 1

        date_key = time_in.strftime('%Y-%m-%d')

        payroll_data[name][date_key].append({
            'Date': date_key,
            'Time In': time_in.strftime('%I:%M %p'),
            'Time Out': time_out.strftime('%I:%M %p'),
            'Reg Hrs': reg_hrs,
            'OT Hours': ot_hrs,
            'Reg Pay (PHP)': f"₱{reg_pay:.2f}",
            'OT Pay (PHP)': f"₱{ot_pay:.2f}",
            'Total Pay (PHP)': f"₱{pay:.2f}"
        })

    stats = f"{parsed_rows} valid entries parsed. {skipped_rows} rows skipped due to invalid or missing time entries."
    total_pay_str = f"Total Payroll: ₱{total_pay:,.2f}"
    summary_lines = [f"{emp}: ₱{pay:,.2f}" for emp, pay in employee_totals.items()]
    summary = "Summary of Total Pay per Employee:<br>" + "<br>".join(summary_lines)

    return payroll_data, total_pay_str, stats, summary

@app.route('/', methods=['GET', 'POST'])
def index():
    grouped = None
    stats = None
    total_pay = None
    summary = None

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)

            df = pd.read_csv(filepath)
            grouped, total_pay, stats, summary = compute_pay(df)

    return render_template('index.html', grouped=grouped, stats=stats, total_pay=total_pay, summary=summary)

if __name__ == '__main__':
    app.run(debug=True)
