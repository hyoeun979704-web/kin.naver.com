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

SCHEDULE_HOURS = [9, 14]  # 09:00, 14:00 KST


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

    # Loop: wait for next scheduled time
    while True:
        next_run = get_next_run_time()
        current = now_kst()
        wait_seconds = (next_run - current).total_seconds()

        next_str = next_run.strftime("%Y-%m-%d %H:%M")
        print(f"\n[Next run] {next_str} KST (in {wait_seconds/60:.0f} min)")
        print("Press Ctrl+C to stop.\n")

        try:
            time.sleep(wait_seconds)
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user.")
            sys.exit(0)

        run_monitor()


if __name__ == "__main__":
    main()
