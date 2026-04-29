import sqlite3
import os

def clean_tuptime():
    db_path = 'scripts/tuptime/tuptime.db'
    fixed_db_path = 'scripts/tuptime/tuptime_fixed.db'

    if os.path.exists(fixed_db_path):
        os.remove(fixed_db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT bootid, btime, uptime, rntime, slptime, offbtime, endst, downtime, kernel FROM tuptime ORDER BY btime ASC")
    rows = [list(row) for row in cursor.fetchall()]
    conn.close()

    # Cleaning logic: Prefer the more recent one.
    # We iterate from newest to oldest to easily truncate previous entries.
    for i in range(len(rows) - 1, 0, -1):
        current_btime = rows[i][1]
        previous_offbtime = rows[i-1][5]

        if previous_offbtime > current_btime:
            print(f"Overlapping found: Entry {i-1} ends at {previous_offbtime}, but Entry {i} starts at {current_btime}")
            # Truncate previous entry
            new_offbtime = current_btime
            rows[i-1][5] = new_offbtime
            # Adjust uptime (assuming rntime=uptime as slptime is 0)
            new_uptime = new_offbtime - rows[i-1][1]
            if new_uptime < 0:
                print(f"Warning: Entry {i-1} would have negative uptime after truncation. Setting to 0.")
                new_uptime = 0
            rows[i-1][2] = new_uptime
            rows[i-1][3] = new_uptime

    # Save to new database
    fixed_conn = sqlite3.connect(fixed_db_path)
    fixed_cursor = fixed_conn.cursor()
    fixed_cursor.execute("CREATE TABLE tuptime (bootid text, btime integer, uptime integer, rntime integer, slptime integer, offbtime integer, endst integer, downtime integer, kernel text)")
    fixed_cursor.executemany("INSERT INTO tuptime VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    fixed_conn.commit()
    fixed_conn.close()
    print(f"Cleaned database saved to {fixed_db_path}")

if __name__ == "__main__":
    clean_tuptime()
