import os
import shutil

# Path setup
parent_dir = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions"
orchestration_dir = os.path.join(parent_dir, 'orchestration')

timers = [
    "daily_afternoon_timer",
    "daily_morning_timer",
    "monthly_aggregation_timer",
    "weekly_summary_timer"
]

for timer in timers:
    src = os.path.join(orchestration_dir, timer)
    dst = os.path.join(parent_dir, timer)
    if os.path.exists(src):
        print(f"Moving {timer} to root...")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.move(src, dst)
        
        # Update function.json
        func_json_path = os.path.join(dst, 'function.json')
        if os.path.exists(func_json_path):
            with open(func_json_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace('"scriptFile": "../scheduler_function.py"', '"scriptFile": "orchestration/scheduler_function.py"')
            with open(func_json_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated function.json for {timer}")
    else:
        print(f"Source {src} not found.")

print("Done.")
