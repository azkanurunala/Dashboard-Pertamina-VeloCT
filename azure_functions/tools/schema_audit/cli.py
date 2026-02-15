"""
CLI Interface for Database Schema Audit System.

This module provides the command-line interface for the schema audit tool,
supporting multiple commands for auditing, fixing, validating, and reporting.

Commands:
- audit: Run audit-only mode to detect schema mismatches
- fix: Apply fixes to detected mismatches
- validate: Validate Python files and schema consistency
- report: Generate comprehensive reports

Requirements: Task 14.1, 14.2
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Import all the components
from .schema_extractor import SchemaExtractor
from .code_auditor import CodeAuditor
from .mismatch_detector import MismatchDetector, CodeSchemaMap
from .schema_fixer import SchemaFixer
from .validator import Validator
from .reporter import Reporter
from .model_updater import ModelUpdater
from .migration_auditor import MigrationAuditor
from .models import DatabaseSchema, FixReport

# Setup logging
logger = logging.getLogger(__name__)


class SchemaAuditCLI:
    """
    Command-line interface for the Database Schema Audit System.
    
    This class provides the main entry point and orchestrates all
    audit, fix, validation, and reporting workflows.
    """
    
    def __init__(self):
        """Initialize the CLI."""
        self.parser = self._create_parser()
        self.verbose = False
        self.dry_run = False
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create argument parser with all commands and flags.
        
        Returns:
            Configured ArgumentParser
        """
        parser = argparse.ArgumentParser(
            prog='schema-audit',
            description='Database Schema Audit and Fix Tool',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run audit only
  schema-audit audit --bacpac pei-dashboard.bacpac --code azure_functions/
  
  # Fix mismatches (dry-run first)
  schema-audit fix --bacpac pei-dashboard.bacpac --code azure_functions/ --dry-run
  schema-audit fix --bacpac pei-dashboard.bacpac --code azure_functions/
  
  # Validate files
  schema-audit validate --files azure_functions/**/*.py
  
  # Generate reports
  schema-audit report --bacpac pei-dashboard.bacpac --code azure_functions/ --output reports/
            """
        )
        
        # Global flags
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate operations without making changes'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Command to execute',
            required=True
        )
        
        # Audit command
        audit_parser = subparsers.add_parser(
            'audit',
            help='Run audit-only mode to detect schema mismatches'
        )
        self._add_audit_arguments(audit_parser)
        
        # Fix command
        fix_parser = subparsers.add_parser(
            'fix',
            help='Apply fixes to detected schema mismatches'
        )
        self._add_fix_arguments(fix_parser)
        
        # Validate command
        validate_parser = subparsers.add_parser(
            'validate',
            help='Validate Python files and schema consistency'
        )
        self._add_validate_arguments(validate_parser)
        
        # Report command
        report_parser = subparsers.add_parser(
            'report',
            help='Generate comprehensive reports'
        )
        self._add_report_arguments(report_parser)
        
        return parser
    
    def _add_audit_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for audit command."""
        parser.add_argument(
            '--bacpac',
            required=True,
            help='Path to BACPAC file containing reference schema'
        )
        parser.add_argument(
            '--code',
            required=True,
            help='Path to code directory to audit'
        )
        parser.add_argument(
            '--output',
            default='audit_report.md',
            help='Output file for audit report (default: audit_report.md)'
        )
        parser.add_argument(
            '--include-migrations',
            action='store_true',
            help='Include migration scripts in audit'
        )
    
    def _add_fix_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for fix command."""
        parser.add_argument(
            '--bacpac',
            required=True,
            help='Path to BACPAC file containing reference schema'
        )
        parser.add_argument(
            '--code',
            required=True,
            help='Path to code directory to fix'
        )
        parser.add_argument(
            '--output',
            default='fix_report.md',
            help='Output file for fix report (default: fix_report.md)'
        )
        parser.add_argument(
            '--backup-dir',
            default='backups',
            help='Directory for file backups (default: backups)'
        )
        parser.add_argument(
            '--severity',
            choices=['CRITICAL', 'WARNING', 'INFO'],
            default='CRITICAL',
            help='Minimum severity level to fix (default: CRITICAL)'
        )
    
    def _add_validate_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for validate command."""
        parser.add_argument(
            '--files',
            nargs='+',
            help='Python files to validate (supports glob patterns)'
        )
        parser.add_argument(
            '--directory',
            help='Directory to validate all Python files'
        )
        parser.add_argument(
            '--output',
            default='validation_report.md',
            help='Output file for validation report (default: validation_report.md)'
        )
    
    def _add_report_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for report command."""
        parser.add_argument(
            '--bacpac',
            required=True,
            help='Path to BACPAC file containing reference schema'
        )
        parser.add_argument(
            '--code',
            help='Path to code directory (optional, for mapping reports)'
        )
        parser.add_argument(
            '--output',
            default='reports',
            help='Output directory for reports (default: reports)'
        )
        parser.add_argument(
            '--types',
            nargs='+',
            choices=['audit', 'schema', 'erd', 'mapping', 'all'],
            default=['all'],
            help='Types of reports to generate (default: all)'
        )
    
    def run(self, args: Optional[list] = None) -> int:
        """
        Main entry point for CLI.
        
        Args:
            args: Command-line arguments (uses sys.argv if None)
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        # Parse arguments
        parsed_args = self.parser.parse_args(args)
        
        # Setup logging
        self._setup_logging(parsed_args.verbose)
        
        # Store global flags
        self.verbose = parsed_args.verbose
        self.dry_run = parsed_args.dry_run
        
        if self.dry_run:
            logger.info("=" * 80)
            logger.info("DRY-RUN MODE: No changes will be made to files")
            logger.info("=" * 80)
        
        # Execute command
        try:
            if parsed_args.command == 'audit':
                return self._execute_audit(parsed_args)
            elif parsed_args.command == 'fix':
                return self._execute_fix(parsed_args)
            elif parsed_args.command == 'validate':
                return self._execute_validate(parsed_args)
            elif parsed_args.command == 'report':
                return self._execute_report(parsed_args)
            else:
                logger.error(f"Unknown command: {parsed_args.command}")
                return 1
        
        except KeyboardInterrupt:
            logger.info("\nOperation cancelled by user")
            return 130
        
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}", exc_info=self.verbose)
            return 1
    
    def _setup_logging(self, verbose: bool) -> None:
        """
        Setup logging configuration.
        
        Args:
            verbose: Enable verbose logging
        """
        level = logging.DEBUG if verbose else logging.INFO
        
        # Configure root logger
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set level for our modules
        logging.getLogger('azure_functions.tools.schema_audit').setLevel(level)
    
    def _execute_audit(self, args: argparse.Namespace) -> int:
        """
        Execute audit command.
        
        Args:
            args: Parsed command-line arguments
        
        Returns:
            Exit code
        """
        logger.info("=" * 80)
        logger.info("SCHEMA AUDIT")
        logger.info("=" * 80)
        
        try:
            # Run audit workflow
            result = self.run_audit_workflow(
                bacpac_path=args.bacpac,
                code_directory=args.code,
                include_migrations=args.include_migrations,
                output_path=args.output
            )
            
            # Check results
            if result['success']:
                logger.info("=" * 80)
                logger.info(f"✓ Audit completed successfully")
                logger.info(f"  Report: {result['report_path']}")
                logger.info(f"  Mismatches: {result['total_mismatches']}")
                logger.info(f"  Critical: {result['critical_mismatches']}")
                logger.info("=" * 80)
                
                # Return non-zero if critical mismatches found
                return 0 if result['critical_mismatches'] == 0 else 2
            else:
                logger.error("✗ Audit failed")
                return 1
        
        except Exception as e:
            logger.error(f"Audit failed: {str(e)}", exc_info=self.verbose)
            return 1
    
    def _execute_fix(self, args: argparse.Namespace) -> int:
        """
        Execute fix command.
        
        Args:
            args: Parsed command-line arguments
        
        Returns:
            Exit code
        """
        logger.info("=" * 80)
        logger.info("SCHEMA FIX")
        logger.info("=" * 80)
        
        try:
            # Run fix workflow
            result = self.run_fix_workflow(
                bacpac_path=args.bacpac,
                code_directory=args.code,
                backup_directory=args.backup_dir,
                min_severity=args.severity,
                dry_run=self.dry_run,
                output_path=args.output
            )
            
            # Check results
            if result['success']:
                logger.info("=" * 80)
                logger.info(f"✓ Fix completed successfully")
                logger.info(f"  Report: {result['report_path']}")
                logger.info(f"  Fixes Applied: {result['fixes_applied']}")
                logger.info(f"  Fixes Failed: {result['fixes_failed']}")
                if result.get('backup_directory'):
                    logger.info(f"  Backups: {result['backup_directory']}")
                logger.info("=" * 80)
                return 0
            else:
                logger.error("✗ Fix failed")
                return 1
        
        except Exception as e:
            logger.error(f"Fix failed: {str(e)}", exc_info=self.verbose)
            return 1
    
    def _execute_validate(self, args: argparse.Namespace) -> int:
        """
        Execute validate command.
        
        Args:
            args: Parsed command-line arguments
        
        Returns:
            Exit code
        """
        logger.info("=" * 80)
        logger.info("VALIDATION")
        logger.info("=" * 80)
        
        try:
            # Collect files to validate
            files_to_validate = []
            
            if args.files:
                # Expand glob patterns
                for pattern in args.files:
                    files_to_validate.extend(Path('.').glob(pattern))
            
            if args.directory:
                # Find all Python files in directory
                dir_path = Path(args.directory)
                files_to_validate.extend(dir_path.rglob('*.py'))
            
            if not files_to_validate:
                logger.error("No files to validate")
                return 1
            
            # Convert to strings
            file_paths = [str(f) for f in files_to_validate]
            
            # Run validation workflow
            result = self.run_validation_workflow(
                file_paths=file_paths,
                dry_run=self.dry_run,
                output_path=args.output
            )
            
            # Check results
            if result['success']:
                logger.info("=" * 80)
                logger.info(f"✓ Validation completed")
                logger.info(f"  Files Validated: {result['total_files']}")
                logger.info(f"  Valid Files: {result['valid_files']}")
                logger.info(f"  Invalid Files: {result['invalid_files']}")
                logger.info("=" * 80)
                
                # Return non-zero if any files invalid
                return 0 if result['invalid_files'] == 0 else 2
            else:
                logger.error("✗ Validation failed")
                return 1
        
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}", exc_info=self.verbose)
            return 1
    
    def _execute_report(self, args: argparse.Namespace) -> int:
        """
        Execute report command.
        
        Args:
            args: Parsed command-line arguments
        
        Returns:
            Exit code
        """
        logger.info("=" * 80)
        logger.info("REPORT GENERATION")
        logger.info("=" * 80)
        
        try:
            # Determine which reports to generate
            report_types = args.types
            if 'all' in report_types:
                report_types = ['audit', 'schema', 'erd', 'mapping']
            
            # Create output directory
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate reports
            generated_reports = []
            
            for report_type in report_types:
                logger.info(f"Generating {report_type} report...")
                
                report_path = output_dir / f"{report_type}_report.md"
                
                if report_type == 'audit' and args.code:
                    # Generate audit report
                    result = self.run_audit_workflow(
                        bacpac_path=args.bacpac,
                        code_directory=args.code,
                        include_migrations=False,
                        output_path=str(report_path)
                    )
                    if result['success']:
                        generated_reports.append(str(report_path))
                
                elif report_type == 'schema':
                    # Generate schema documentation
                    extractor = SchemaExtractor()
                    schema = extractor.extract_from_bacpac(args.bacpac)
                    
                    reporter = Reporter()
                    doc = reporter.generate_schema_documentation(schema)
                    
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(doc)
                    
                    generated_reports.append(str(report_path))
                
                elif report_type == 'erd':
                    # Generate ERD diagram
                    extractor = SchemaExtractor()
                    schema = extractor.extract_from_bacpac(args.bacpac)
                    
                    reporter = Reporter()
                    erd = reporter.generate_erd_diagram(schema)
                    
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(erd)
                    
                    generated_reports.append(str(report_path))
                
                elif report_type == 'mapping' and args.code:
                    # Generate scraper-table mapping
                    auditor = CodeAuditor()
                    auditor.scan_directory(args.code)
                    operations_map = auditor.build_operation_map()
                    
                    reporter = Reporter()
                    mapping = reporter.generate_mapping_table(operations_map)
                    
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(mapping)
                    
                    generated_reports.append(str(report_path))
            
            # Summary
            logger.info("=" * 80)
            logger.info(f"✓ Generated {len(generated_reports)} reports")
            for report in generated_reports:
                logger.info(f"  - {report}")
            logger.info("=" * 80)
            
            return 0
        
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}", exc_info=self.verbose)
            return 1
    
    # Workflow methods (implemented in subtask 14.2)
    def run_audit_workflow(
        self,
        bacpac_path: str,
        code_directory: str,
        include_migrations: bool = False,
        output_path: str = 'audit_report.md'
    ) -> Dict[str, Any]:
        """
        Run full audit workflow.
        
        This method orchestrates the complete audit process:
        1. Extract reference schema from BACPAC
        2. Scan code for database operations
        3. Compare schemas and detect mismatches
        4. Generate audit report
        
        Args:
            bacpac_path: Path to BACPAC file
            code_directory: Path to code directory
            include_migrations: Include migration scripts in audit
            output_path: Path for output report
        
        Returns:
            Dictionary with audit results
        """
        logger.info("Starting audit workflow...")
        
        result = {
            'success': False,
            'report_path': output_path,
            'total_mismatches': 0,
            'critical_mismatches': 0,
            'warning_mismatches': 0,
            'info_mismatches': 0,
            'errors': []
        }
        
        try:
            # Step 1: Extract reference schema from BACPAC
            logger.info(f"Step 1/4: Extracting schema from BACPAC: {bacpac_path}")
            extractor = SchemaExtractor()
            reference_schema = extractor.extract_from_bacpac(bacpac_path)
            logger.info(f"  ✓ Extracted {len(reference_schema.tables)} tables")
            
            # Step 2: Scan code for database operations
            logger.info(f"Step 2/4: Scanning code directory: {code_directory}")
            auditor = CodeAuditor()
            auditor.scan_directory(code_directory)
            
            # Build operation map
            operations_map = auditor.build_operation_map()
            logger.info(f"  ✓ Found operations for {len(operations_map)} tables")
            
            # Create code schema map
            code_schema = CodeSchemaMap(table_operations=operations_map)
            
            # Include migration scripts if requested
            if include_migrations:
                logger.info("  Scanning migration scripts...")
                migration_auditor = MigrationAuditor(reference_schema)
                migration_auditor.scan_migration_scripts(code_directory)
                migration_ops = migration_auditor.audit_migration_operations()
                logger.info(f"  ✓ Found {len(migration_ops)} migration operations")
            
            # Step 3: Compare schemas and detect mismatches
            logger.info("Step 3/4: Detecting schema mismatches...")
            detector = MismatchDetector(reference_schema)
            mismatches = detector.compare_schemas(code_schema)
            
            # Categorize by severity
            categorized = detector.categorize_by_severity(mismatches)
            
            result['total_mismatches'] = len(mismatches)
            result['critical_mismatches'] = len(categorized['CRITICAL'])
            result['warning_mismatches'] = len(categorized['WARNING'])
            result['info_mismatches'] = len(categorized['INFO'])
            
            logger.info(f"  ✓ Found {len(mismatches)} mismatches")
            logger.info(f"    - Critical: {result['critical_mismatches']}")
            logger.info(f"    - Warning: {result['warning_mismatches']}")
            logger.info(f"    - Info: {result['info_mismatches']}")
            
            # Step 4: Generate audit report
            logger.info(f"Step 4/4: Generating audit report: {output_path}")
            reporter = Reporter()
            report = reporter.generate_audit_report(mismatches)
            
            # Write report to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"  ✓ Report saved to: {output_path}")
            
            result['success'] = True
            return result
        
        except Exception as e:
            error_msg = f"Audit workflow failed: {str(e)}"
            logger.error(error_msg, exc_info=self.verbose)
            result['errors'].append(error_msg)
            return result
    
    def run_fix_workflow(
        self,
        bacpac_path: str,
        code_directory: str,
        backup_directory: str = 'backups',
        min_severity: str = 'CRITICAL',
        dry_run: bool = False,
        output_path: str = 'fix_report.md'
    ) -> Dict[str, Any]:
        """
        Run full fix workflow.
        
        This method orchestrates the complete fix process:
        1. Run audit to detect mismatches
        2. Filter by severity
        3. Create backups
        4. Apply fixes
        5. Validate changes
        6. Generate fix report
        
        Args:
            bacpac_path: Path to BACPAC file
            code_directory: Path to code directory
            backup_directory: Directory for backups
            min_severity: Minimum severity to fix
            dry_run: Simulate without applying changes
            output_path: Path for output report
        
        Returns:
            Dictionary with fix results
        """
        logger.info("Starting fix workflow...")
        
        result = {
            'success': False,
            'report_path': output_path,
            'fixes_applied': 0,
            'fixes_failed': 0,
            'backup_directory': None,
            'errors': []
        }
        
        try:
            # Step 1: Run audit to detect mismatches
            logger.info("Step 1/6: Running audit to detect mismatches...")
            audit_result = self.run_audit_workflow(
                bacpac_path=bacpac_path,
                code_directory=code_directory,
                include_migrations=False,
                output_path='temp_audit.md'
            )
            
            if not audit_result['success']:
                result['errors'].append("Audit failed")
                return result
            
            # Re-extract schema and mismatches for fixing
            extractor = SchemaExtractor()
            reference_schema = extractor.extract_from_bacpac(bacpac_path)
            
            auditor = CodeAuditor()
            auditor.scan_directory(code_directory)
            operations_map = auditor.build_operation_map()
            code_schema = CodeSchemaMap(table_operations=operations_map)
            
            detector = MismatchDetector(reference_schema)
            all_mismatches = detector.compare_schemas(code_schema)
            
            # Step 2: Filter by severity
            logger.info(f"Step 2/6: Filtering mismatches by severity >= {min_severity}")
            
            from .models import Severity
            severity_order = {'INFO': 0, 'WARNING': 1, 'CRITICAL': 2}
            min_severity_level = severity_order.get(min_severity, 2)
            
            mismatches_to_fix = [
                m for m in all_mismatches
                if severity_order.get(m.severity.value, 0) >= min_severity_level
            ]
            
            logger.info(f"  ✓ Selected {len(mismatches_to_fix)} mismatches to fix")
            
            if not mismatches_to_fix:
                logger.info("No mismatches to fix")
                result['success'] = True
                return result
            
            # Step 3: Create backups (handled by SchemaFixer)
            logger.info(f"Step 3/6: Preparing to fix {len(mismatches_to_fix)} mismatches...")
            
            # Step 4: Apply fixes
            logger.info("Step 4/6: Applying fixes...")
            fixer = SchemaFixer(backup_root=backup_directory)
            fix_report = fixer.fix_mismatches(mismatches_to_fix, dry_run=dry_run)
            
            result['fixes_applied'] = fix_report.total_fixes_applied
            result['fixes_failed'] = fix_report.total_fixes_failed
            result['backup_directory'] = fix_report.backup_directory
            
            logger.info(f"  ✓ Applied: {result['fixes_applied']}")
            logger.info(f"  ✗ Failed: {result['fixes_failed']}")
            
            # Step 5: Validate changes
            if not dry_run and result['fixes_applied'] > 0:
                logger.info("Step 5/6: Validating changes...")
                
                # Get list of modified files
                modified_files = fix_report.get_modified_files()
                
                validator = Validator(dry_run=False)
                validation_results = validator.validate_files(modified_files)
                
                # Check for validation errors
                invalid_files = [
                    path for path, res in validation_results.items()
                    if not res.is_valid
                ]
                
                if invalid_files:
                    logger.warning(f"  ⚠ {len(invalid_files)} files have validation errors")
                    for file_path in invalid_files:
                        logger.warning(f"    - {file_path}")
                else:
                    logger.info(f"  ✓ All {len(modified_files)} modified files validated successfully")
            else:
                logger.info("Step 5/6: Skipping validation (dry-run or no fixes applied)")
            
            # Step 6: Generate fix report
            logger.info(f"Step 6/6: Generating fix report: {output_path}")
            reporter = Reporter()
            report = reporter.generate_fix_report(fix_report)
            
            # Write report to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"  ✓ Report saved to: {output_path}")
            
            result['success'] = True
            return result
        
        except Exception as e:
            error_msg = f"Fix workflow failed: {str(e)}"
            logger.error(error_msg, exc_info=self.verbose)
            result['errors'].append(error_msg)
            return result
    
    def run_validation_workflow(
        self,
        file_paths: list,
        dry_run: bool = False,
        output_path: str = 'validation_report.md'
    ) -> Dict[str, Any]:
        """
        Run validation workflow.
        
        This method validates Python files for:
        1. Syntax errors
        2. Import errors
        3. Schema consistency
        
        Args:
            file_paths: List of file paths to validate
            dry_run: Dry-run mode
            output_path: Path for output report
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Starting validation workflow...")
        
        result = {
            'success': False,
            'report_path': output_path,
            'total_files': len(file_paths),
            'valid_files': 0,
            'invalid_files': 0,
            'errors': []
        }
        
        try:
            # Step 1: Validate files
            logger.info(f"Step 1/2: Validating {len(file_paths)} files...")
            
            validator = Validator(dry_run=dry_run)
            validation_results = validator.validate_files(file_paths)
            
            # Count valid/invalid
            result['valid_files'] = sum(
                1 for res in validation_results.values() if res.is_valid
            )
            result['invalid_files'] = result['total_files'] - result['valid_files']
            
            logger.info(f"  ✓ Valid: {result['valid_files']}")
            logger.info(f"  ✗ Invalid: {result['invalid_files']}")
            
            # Step 2: Generate validation report
            logger.info(f"Step 2/2: Generating validation report: {output_path}")
            
            # Build report content
            report_lines = [
                "# Validation Report",
                "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Total Files:** {result['total_files']}",
                f"**Valid Files:** {result['valid_files']}",
                f"**Invalid Files:** {result['invalid_files']}",
                "",
                "---",
                ""
            ]
            
            if result['invalid_files'] > 0:
                report_lines.extend([
                    "## Invalid Files",
                    ""
                ])
                
                for file_path, val_result in validation_results.items():
                    if not val_result.is_valid:
                        report_lines.append(f"### `{file_path}`")
                        report_lines.append("")
                        
                        if val_result.errors:
                            report_lines.append("**Errors:**")
                            for error in val_result.errors:
                                report_lines.append(f"- {error}")
                            report_lines.append("")
                        
                        if val_result.warnings:
                            report_lines.append("**Warnings:**")
                            for warning in val_result.warnings:
                                report_lines.append(f"- {warning}")
                            report_lines.append("")
            else:
                report_lines.extend([
                    "## Summary",
                    "",
                    "✓ All files validated successfully!",
                    ""
                ])
            
            report = '\n'.join(report_lines)
            
            # Write report to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"  ✓ Report saved to: {output_path}")
            
            result['success'] = True
            return result
        
        except Exception as e:
            error_msg = f"Validation workflow failed: {str(e)}"
            logger.error(error_msg, exc_info=self.verbose)
            result['errors'].append(error_msg)
            return result


def main():
    """Main entry point for command-line execution."""
    cli = SchemaAuditCLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
