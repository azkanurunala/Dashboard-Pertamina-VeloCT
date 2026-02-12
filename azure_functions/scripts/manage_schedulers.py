import json
import os
from typing import Dict, Any

def load_json(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r') as f:
        return json.load(f)

def save_json(filepath: str, data: Dict[str, Any]):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_paths():
    """Get absolute paths for settings files relative to this script."""
    # Script is in /scripts, so we need to go up one level to /azure_functions
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    return {
        'settings': os.path.join(base_dir, 'local.settings.json'),
        'env': os.path.join(base_dir, '.env')
    }

def update_local_settings(mode: str):
    paths = get_paths()
    settings_path = paths['settings']
    
    if not os.path.exists(settings_path):
        print(f"Error: {settings_path} not found.")
        return

    settings = load_json(settings_path)
    values = settings.get('Values', {})

    if mode == 'test':
        print(f"Switching to TESTING schedules (every 5 mins) in {settings_path}...")
        values['MORNING_TIMER_SCHEDULE'] = "0 */5 * * * *"
        values['AFTERNOON_TIMER_SCHEDULE'] = "0 */5 * * * *"
        values['WEEKLY_TIMER_SCHEDULE'] = "0 */5 * * * *"
        values['MONTHLY_TIMER_SCHEDULE'] = "0 */5 * * * *"
    elif mode == 'prod':
        print(f"Switching to PRODUCTION schedules in {settings_path}...")
        values['MORNING_TIMER_SCHEDULE'] = "0 0 6 * * *"       # 6:00 AM Daily
        values['AFTERNOON_TIMER_SCHEDULE'] = "0 0 16 * * *"      # 4:00 PM Daily
        values['WEEKLY_TIMER_SCHEDULE'] = "0 0 7 * * 1"              # 7:00 AM Monday
        values['MONTHLY_TIMER_SCHEDULE'] = "0 0 7 1 * *"             # 7:00 AM 1st of Month
    elif mode == 'demo':
        print(f"Switching to DEMO staggered schedules in {settings_path}...")
        # Specific times requested by user: 06:10, 06:15, 06:20, 06:25 (Local WIB)
        values['MORNING_TIMER_SCHEDULE'] = "0 10 6 * * *"       # 06:10 AM
        values['AFTERNOON_TIMER_SCHEDULE'] = "0 15 6 * * *"     # 06:15 AM
        values['WEEKLY_TIMER_SCHEDULE'] = "0 20 6 * * *"        # 06:20 AM
        values['MONTHLY_TIMER_SCHEDULE'] = "0 25 6 * * *"       # 06:25 AM
    else:
        print("Invalid mode. Use 'test', 'prod', or 'demo'.")
        return

    settings['Values'] = values
    save_json(settings_path, settings)
    print(f"Updated {settings_path} successfully.")

def update_env_file(mode: str):
    paths = get_paths()
    env_path = paths['env']
    
    if not os.path.exists(env_path):
        print(f"Error: {env_path} not found.")
        # Create it if missing? No, better to warn.
        return

    with open(env_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    # Note: These values must match the logic above
    test_schedule = "0 */5 * * * *"
    
    prod_schedules = {
        'MORNING_TIMER_SCHEDULE': "0 0 6 * * *",
        'AFTERNOON_TIMER_SCHEDULE': "0 0 16 * * *",
        'WEEKLY_TIMER_SCHEDULE': "0 0 7 * * 1",
        'MONTHLY_TIMER_SCHEDULE': "0 0 7 1 * *"
    }
    
    demo_schedules = {
        'MORNING_TIMER_SCHEDULE': "0 10 6 * * *",
        'AFTERNOON_TIMER_SCHEDULE': "0 15 6 * * *",
        'WEEKLY_TIMER_SCHEDULE': "0 20 6 * * *",
        'MONTHLY_TIMER_SCHEDULE': "0 25 6 * * *"
    }

    processed_keys = set()
    
    target_schedules = prod_schedules
    if mode == 'test':
        target_schedules = {k: test_schedule for k in prod_schedules}
    elif mode == 'demo':
        target_schedules = demo_schedules

    for line in lines:
        parts = line.split('=')
        if len(parts) >= 2:
            key = parts[0].strip()
            if key in target_schedules:
                val = target_schedules[key]
                new_lines.append(f"{key}={val}\n")
                processed_keys.add(key)
                continue
        new_lines.append(line)
    
    # If keys were missing in .env, append them (optional, but good for robustness)
    # matching update_local_settings logic
    
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    print(f"Updated {env_path} successfully.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python manage_schedulers.py [test|prod]")
    else:
        mode = sys.argv[1]
        update_local_settings(mode)
        update_env_file(mode)
