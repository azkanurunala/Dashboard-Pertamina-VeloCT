
import os
import csv
import json

def inspect():
    path = r'azure_functions\references\news'
    results = {}
    if not os.path.exists(path):
        print(f"Path not found: {path}")
        return
    
    for f in os.listdir(path):
        if f.endswith('.csv'):
            full_p = os.path.join(path, f)
            try:
                with open(full_p, 'r', encoding='utf-8-sig') as file:
                    reader = csv.reader(file)
                    header = next(reader)
                    first_row = next(reader, None)
                    results[f] = {
                        "header": header,
                        "sample": first_row
                    }
            except Exception as e:
                results[f] = {"error": str(e)}
    
    with open('news_headers.json', 'w') as out:
        json.dump(results, out, indent=2)
    print("Exported news_headers.json")

if __name__ == "__main__":
    inspect()
