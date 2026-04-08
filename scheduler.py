"""
Naver Kin Monitor - Scheduler
First run: execute immediately
Then auto-run at 09:00 and 14:00 KST every day
"""

import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))

SCHEDULE_HOURS = [9, 12, 15, 17]  # 09:00, 12:00, 15:00, 17:00 KST


def now_kst():
    return datetime.now(KST)


def run_monitor():
    """Run naver_kin_monitor.py as a subprocess."""
    current_time = now_kst().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 50}")
    print(f"  [{current_time} KST] Starting monitor...")
    print(f"{'=' * 50}\n")

    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "naver_kin_monitor.py")],
        cwd=str(BASE_DIR),
    )

    current_time = now_kst().strftime("%Y-%m-%d %H:%M:%S")
    if result.returncode == 0:
        print(f"\n[{current_time}] Monitor finished successfully.")
    else:
        print(f"\n[{current_time}] Monitor exited with code {result.returncode}.")


def get_next_run_time():
    """Calculate the next scheduled run time."""
    current = now_kst()
    today_schedules = [
        current.replace(hour=h, minute=0, second=0, microsecond=0)
        for h in SCHEDULE_HOURS
    ]

    # Find the next future schedule
    for t in today_schedules:
        if t > current:
            return t

    # All today's schedules have passed, use tomorrow's first schedule
    tomorrow = current + timedelta(days=1)
    return tomorrow.replace(
        hour=SCHEDULE_HOURS[0], minute=0, second=0, microsecond=0
    )


def main():
    print("=" * 50)
    print("  Naver Kin Monitor - Scheduler")
    print(f"  Schedule: {', '.join(f'{h:02d}:00' for h in SCHEDULE_HOURS)} KST")
    print("=" * 50)

    # First run: execute immediately
    print("\n[First run] Executing immediately...")
    run_monitor()

    # Track which schedule we already ran to avoid duplicates
    last_ran = None

    # Loop: check every 60 seconds if it's time to run
    while True:
        next_run = get_next_run_time()
        next_str = next_run.strftime("%Y-%m-%d %H:%M")
        current = now_kst()
        wait_min = (next_run - current).total_seconds() / 60
        print(f"\r[Next run] {next_str} KST (in {wait_min:.0f} min)  ", end="", flush=True)

        try:
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user.")
            sys.exit(0)

        # Check if current time matches any schedule
        current = now_kst()
        current_hour = current.hour
        current_date = current.date()
        run_key = (current_date, current_hour)

        if current_hour in SCHEDULE_HOURS and run_key != last_ran:
            last_ran = run_key
            run_monitor()


if __name__ == "__main__":
    main()
