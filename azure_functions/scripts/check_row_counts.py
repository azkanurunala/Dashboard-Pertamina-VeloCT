
import asyncio
import os
import sys

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), 'azure_functions', '.env'))
except ImportError:
    pass

# Ensure the DB handler can find the connection string
if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

async def check_rows():
    config_manager.reload()
    db_config = await config_manager.get_database_config()
    db_handler = DatabaseHandler(db_config)
    
    tables = [
        'data_biodiesel_hip', 'data_bioetanol_hip', 'data_cpo_prices',
        'data_oil_crackspreads', 'data_petrochemical_prices', 'data_fossil_prediction',
        'data_nuclear', 'data_oil_prices', 'data_market_indicators',
        'data_fossil', 'data_saf_uco_prices', 'data_volatility_index',
        'data_geopolitical_risk_index', 'data_eia_market', 'data_renewable_energy',
        'data_wte_waste'
    ]
    
    results = []
    results.append(f"{'Table Name':<30} | {'Row Count':<10}")
    results.append("-" * 45)
    for table in tables:
        try:
            query = f"SELECT COUNT(*) FROM {table}"
            result = await db_handler.execute_query(query)
            # Result is list of Row objects/dicts, e.g. [{'': 352}]
            if result:
                first_row = result[0]
                # If it's a dict/Row-like object, get the first value
                if hasattr(first_row, 'values'):
                    count = list(first_row.values())[0]
                else:
                    # Fallback for tuple/list
                    count = first_row[0]
            else:
                count = 0
            results.append(f"{table:<30} | {count:<10}")
        except Exception as e:
            results.append(f"{table:<30} | Error: {e}")
    
    with open('row_counts.txt', 'w') as f:
        f.write("\n".join(results))
    print("Results written to row_counts.txt")

if __name__ == "__main__":
    asyncio.run(check_rows())
