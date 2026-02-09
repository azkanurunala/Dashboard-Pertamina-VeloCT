import os

orchestration_dir = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\orchestration"
timers = [
    "daily_afternoon_timer",
    "daily_morning_timer",
    "monthly_aggregation_timer",
    "weekly_summary_timer"
]

for timer in timers:
    src = os.path.join(orchestration_dir, timer)
    dst = os.path.join(orchestration_dir, "_" + timer)
    if os.path.exists(src):
        print(f"Renaming {src} to {dst}")
        try:
            if os.path.exists(dst):
                import shutil
                shutil.rmtree(dst)
            os.rename(src, dst)
            print(f"Successfully renamed {timer}")
        except Exception as e:
            print(f"Failed to rename {timer}: {e}")
    else:
        print(f"Source {src} not found.")
