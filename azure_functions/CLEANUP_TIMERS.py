import os
import shutil

parent_dir = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions"
orchestration_dir = os.path.join(parent_dir, 'orchestration')

timers = [
    "daily_afternoon_timer",
    "daily_morning_timer",
    "monthly_aggregation_timer",
    "weekly_summary_timer"
]

print("--- CLEANUP START ---")

# 1. Delete duplicates in orchestration folder
for timer in timers:
    path = os.path.join(orchestration_dir, timer)
    if os.path.exists(path):
        print(f"Deleting duplicate: {path}")
        try:
            shutil.rmtree(path)
            print(f"Successfully deleted {timer}")
        except Exception as e:
            print(f"Failed to delete {timer}: {e}")
    else:
        print(f"No duplicate found for {timer}")

# 2. Verify root timers
scheduler_path = os.path.join(orchestration_dir, 'scheduler_function.py')
print(f"Verifying scheduler exists: {scheduler_path} -> {os.path.exists(scheduler_path)}")

for timer in timers:
    timer_path = os.path.join(parent_dir, timer)
    func_json = os.path.join(timer_path, 'function.json')
    
    if os.path.exists(func_json):
        print(f"Verifying {timer}/function.json...")
        with open(func_json, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '"scriptFile": "../orchestration/scheduler_function.py"' in content:
            print(f"✅ {timer} path is CORRECT")
        else:
            print(f"❌ {timer} path is INCORRECT")
            # Correcting it just in case
            if '"scriptFile": "orchestration/scheduler_function.py"' in content:
                 content = content.replace('"scriptFile": "orchestration/scheduler_function.py"', '"scriptFile": "../orchestration/scheduler_function.py"')
                 with open(func_json, 'w', encoding='utf-8') as f:
                     f.write(content)
                 print(f"Fixed {timer} path.")
    else:
        print(f"❌ {timer} folder or function.json NOT FOUND in root")

print("--- CLEANUP DONE ---")
