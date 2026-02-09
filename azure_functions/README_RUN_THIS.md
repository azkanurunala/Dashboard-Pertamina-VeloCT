
# README - Azure Functions Fix & Test

## 🚀 One-Command Solution
To fix the function key issues and verify everything works, run:

```bash
python azure_functions/fix_and_test.py
```

## 📋 What this does:
1. **Syncs Keys**: Automatically updates all test files to use the consistent primary key.
2. **Tests DB**: Verifies the connection to SQL Server.
3. **Tests Functions**: Runs validation against a single Azure Function.
4. **Summary**: Provides clear feedback on current status.

## 📊 Recommended Test Scripts
If you want to run specific tests later:

- `azure_functions/test_all_functions.py`: The most comprehensive test + DB verify.
- `azure_functions/verify_database_data.py`: Quick check of today's scraped data.
- `azure_functions/test_single_function.py`: Quick verification of one endpoint.

## ⚠️ Troubleshooting
If you still get **HTTP 401 (Unauthorized)**:
1. Go to Azure Portal.
2. Navigate to `pei-dashboard` Function App.
3. Check `App keys` -> `Default`.
4. Update `PRIMARY_KEY` in `azure_functions/fix_and_test.py` if it changed.

---
*Created by Antigravity AI*
