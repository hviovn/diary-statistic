import sqlite3
import math
import os
from datetime import datetime, date, timedelta

def generate_tuptime_heatmaps():
    db_path = 'scripts/tuptime/tuptime_fixed.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Ensure we use btime + uptime for offbtime if it's null
    cursor.execute("SELECT btime, COALESCE(offbtime, btime + uptime) FROM tuptime ORDER BY btime ASC")
    rows = cursor.fetchall()
    conn.close()

    daily_running_seconds = {} # date -> seconds

    for btime, etime in rows:
        curr_time = btime
        while curr_time < etime:
            curr_date = datetime.fromtimestamp(curr_time).date()
            next_midnight = datetime.combine(curr_date + timedelta(days=1), datetime.min.time()).timestamp()

            end_of_day = min(etime, next_midnight)
            duration = end_of_day - curr_time

            daily_running_seconds[curr_date] = daily_running_seconds.get(curr_date, 0) + duration
            curr_time = end_of_day

    # Filter for 2026
    data_2026 = {d: s for d, s in daily_running_seconds.items() if d.year == 2026}

    if not data_2026:
        print("No data found for 2026")
        return

    # Generate SVGs
    generate_svg(2026, data_2026, "docs/tuptime/tuptime.svg", mode="intensity")
    generate_svg(2026, data_2026, "docs/tuptime/tuptime2.svg", mode="binary")

def generate_svg(year, data, filename, mode="intensity"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    first_sunday = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    square_size = 10
    square_margin = 2
    width = 53 * (square_size + square_margin) + 40
    height = 7 * (square_size + square_margin) + 35

    svg_parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">']

    title = f"Uptime {year}" if mode == "intensity" else f"Uptime status {year}"
    svg_parts.append(f'<text x="5" y="15" font-family="sans-serif" font-size="14" font-weight="bold" fill="#24292e">{title}</text>')

    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    grid_offset_y = 35
    for i, label in enumerate(day_labels):
        if i in [1, 3, 5]:
            y = i * (square_size + square_margin) + grid_offset_y + 9
            svg_parts.append(f'<text x="5" y="{y}" font-family="sans-serif" font-size="8" fill="#767676">{label}</text>')

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last_month = -1
    curr = first_sunday

    green_shades = ['#9be9a8', '#40c463', '#30a14e', '#216e39']

    for week in range(53):
        if curr.year == year and curr.month != last_month:
            x = week * (square_size + square_margin) + 30
            svg_parts.append(f'<text x="{x}" y="30" font-family="sans-serif" font-size="8" fill="#767676">{months[curr.month-1]}</text>')
            last_month = curr.month

        for day in range(7):
            if curr > end_date: break
            if curr >= start_date:
                seconds = data.get(curr, 0)
                percentage = seconds / 86400.0

                color = "#ebedf0" # pale/white for 0%

                if mode == "intensity":
                    if seconds > 0:
                        level = min(3, math.floor(percentage * 4))
                        color = green_shades[level]
                else: # mode == "binary"
                    if seconds >= 86399: # Allow 1s margin for floating point/rounding
                        color = green_shades[2] # A nice green
                    elif seconds > 0:
                        color = "#ef5350" # Red for partial uptime
                    else:
                        color = "#ef5350" # User said "second gets downtime in red".
                                          # Usually 0% is downtime.
                                          # Let's clarify: "everything below 100% for a day get's a different color... second gets downtime in red"
                                          # So 0% and <100% should be red.

                x = week * (square_size + square_margin) + 30
                y = day * (square_size + square_margin) + grid_offset_y

                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                tooltip = f"{curr}: {hours}h {minutes}m running ({percentage:.1%})"

                svg_parts.append(f'<rect x="{x}" y="{y}" width="{square_size}" height="{square_size}" fill="{color}" rx="2" ry="2"><title>{tooltip}</title></rect>')

            curr += timedelta(days=1)
        if curr > end_date: break

    svg_parts.append('</svg>')

    with open(filename, "w") as f:
        f.write("\n".join(svg_parts))
    print(f"Generated {filename}")

if __name__ == "__main__":
    generate_tuptime_heatmaps()
