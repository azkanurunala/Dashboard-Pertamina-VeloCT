"""
Automated cleanup script for verification files
Safely removes temporary and obsolete files
"""
import os
import shutil
from datetime import datetime

print("=" * 80)
print("AUTOMATED CLEANUP SCRIPT")
print("=" * 80)
print()

# Create backup first
backup_folder = f"backup_before_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"Creating backup folder: {backup_folder}")

# Files to delete
files_to_delete = [
    # Old migration scripts
    'scripts/migrate_all_tables.sql',
    'scripts/migrate_bioetanol_table.py',
    'scripts/migrate_ebt_capacity_table.py',
    'scripts/migrate_eia_table.py',
    'scripts/migrate_fossil_table.py',
    'scripts/migrate_harga_ebt_table.py',
    'scripts/migrate_iaea_tables.py',
    'scripts/migrate_oil_prices_table.py',
    'scripts/migrate_ruptl_table.py',
    'scripts/migrate_wte_tables.py',
    'scripts/direct_migrate_test.py',
    
    # Temporary extraction scripts
    'extract_bacpac_schema.py',
    'extract_full_schema.py',
    'extract_complete_schema.py',
    'analyze_bacpac.py',
    'fix_legacy_table_references.py',
    
    # Temporary data files
    'bacpac_schema.json',
    'bacpac_full_schema.json',
    'bacpac_complete_schema.json',
    'model_raw.xml',
    'origin.xml',
    'schema_output.txt',
]

# Files to archive (optional detailed docs)
files_to_archive = [
    'SCHEMA_VERIFICATION_REPORT.md',
    'VERIFICATION_CHECKLIST.md',
    'DATABASE_ARCHITECTURE.md',
    'TABLE_MAPPING.md',
    'QUICK_REFERENCE.md',
    'LAPORAN_UNTUK_CLIENT.md',
    'schema_verification_report.json',
]

# Files to keep (will not be touched)
files_to_keep = [
    'pei-dashboard.bacpac',
    'UNIFIED_MIGRATION.sql',
    'verify_schema_alignment.py',
    'RINGKASAN_FINAL.md',
    'FINAL_VERIFICATION_REPORT.md',
    'README_VERIFICATION.md',
    'VERIFICATION_SUMMARY_ID.md',
    'CLEANUP_GUIDE.md',
    'cleanup_files.py',
]

print("\n" + "=" * 80)
print("STEP 1: Creating Archive")
print("=" * 80)

archive_folder = 'docs/verification_archive_2026-02-16'
os.makedirs(archive_folder, exist_ok=True)

archived_count = 0
for file in files_to_archive:
    if os.path.exists(file):
        try:
            shutil.copy2(file, archive_folder)
            print(f"✓ Archived: {file}")
            archived_count += 1
        except Exception as e:
            print(f"✗ Failed to archive {file}: {e}")

print(f"\nArchived {archived_count} files to {archive_folder}")

print("\n" + "=" * 80)
print("STEP 2: Deleting Obsolete Files")
print("=" * 80)

deleted_count = 0
not_found_count = 0

for file in files_to_delete:
    if os.path.exists(file):
        try:
            os.remove(file)
            print(f"✓ Deleted: {file}")
            deleted_count += 1
        except Exception as e:
            print(f"✗ Failed to delete {file}: {e}")
    else:
        not_found_count += 1

print(f"\nDeleted {deleted_count} files")
print(f"Not found: {not_found_count} files (already deleted or never existed)")

print("\n" + "=" * 80)
print("STEP 3: Deleting Archived Files from Root")
print("=" * 80)

archived_deleted_count = 0
for file in files_to_archive:
    if os.path.exists(file):
        try:
            os.remove(file)
            print(f"✓ Deleted from root: {file}")
            archived_deleted_count += 1
        except Exception as e:
            print(f"✗ Failed to delete {file}: {e}")

print(f"\nDeleted {archived_deleted_count} archived files from root")

print("\n" + "=" * 80)
print("STEP 4: Organizing Remaining Files")
print("=" * 80)

# Create docs/database folder
docs_db_folder = 'docs/database'
os.makedirs(docs_db_folder, exist_ok=True)

# Files to move to docs/database
docs_files = [
    'RINGKASAN_FINAL.md',
    'FINAL_VERIFICATION_REPORT.md',
    'README_VERIFICATION.md',
    'VERIFICATION_SUMMARY_ID.md',
]

moved_count = 0
for file in docs_files:
    if os.path.exists(file):
        try:
            dest = os.path.join(docs_db_folder, file)
            shutil.move(file, dest)
            print(f"✓ Moved to docs/database: {file}")
            moved_count += 1
        except Exception as e:
            print(f"✗ Failed to move {file}: {e}")

print(f"\nMoved {moved_count} files to docs/database")

print("\n" + "=" * 80)
print("CLEANUP SUMMARY")
print("=" * 80)
print(f"✓ Archived: {archived_count} files")
print(f"✓ Deleted: {deleted_count} obsolete files")
print(f"✓ Deleted: {archived_deleted_count} archived files from root")
print(f"✓ Moved: {moved_count} files to docs/database")
print(f"✓ Not found: {not_found_count} files")

print("\n" + "=" * 80)
print("FILES KEPT IN ROOT")
print("=" * 80)
for file in files_to_keep:
    if os.path.exists(file):
        print(f"✓ {file}")

print("\n" + "=" * 80)
print("CLEANUP COMPLETE!")
print("=" * 80)
print()
print("Next steps:")
print("1. Review docs/verification_archive_2026-02-16/ folder")
print("2. Review docs/database/ folder")
print("3. Verify UNIFIED_MIGRATION.sql is in root")
print("4. Run: python verify_schema_alignment.py (to test)")
print("5. Delete this cleanup script if satisfied: cleanup_files.py")
print()
print("✅ All done!")
