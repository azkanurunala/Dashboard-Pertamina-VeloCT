import os
import shutil

orchestration_dir = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\orchestration"
timers = [
    "daily_afternoon_timer",
    "daily_morning_timer",
    "monthly_aggregation_timer",
    "weekly_summary_timer"
]

for timer in timers:
    path = os.path.join(orchestration_dir, timer)
    if os.path.exists(path):
        print(f"Aggressively deleting: {path}")
        try:
            # Try deleting contents first
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(path)
            print(f"Deleted {timer}")
        except Exception as e:
            print(f"Error: {e}")
            try:
                shutil.rmtree(path)
                print(f"shutil deleted {timer}")
            except:
                print("shutil also failed")
