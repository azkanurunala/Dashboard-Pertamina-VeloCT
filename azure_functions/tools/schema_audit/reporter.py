"""
Reporter module for Database Schema Audit System.

This module provides reporting functionality for:
- Audit reports in Markdown format
- Fix reports documenting changes
- Schema documentation generation
- ERD diagrams in Mermaid format
- Scraper-table mapping documentation
- Changelog generation
- Summary statistics

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging

from .models import (
    Mismatch, Fix, FixReport, DatabaseSchema, TableSchema,
    TableOperation, Severity, MismatchType
)

logger = logging.getLogger(__name__)


class Reporter:
    """
    Generates comprehensive reports and documentation for schema audit system.
    
    This class provides reporting functionality for:
    - Audit reports showing schema mismatches
    - Fix reports documenting applied changes
    - Schema documentation in Markdown
    - ERD diagrams in Mermaid format
    - Scraper-table mapping tables
    - Changelogs
    - Summary statistics
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """
    
    def __init__(self):
        """Initialize the Reporter."""
        self.generated_reports: List[str] = []
    
    def generate_audit_report(self, mismatches: List[Mismatch]) -> str:
        """
        Generate audit report in Markdown format.
        
        This method creates a comprehensive audit report that documents all
        schema mismatches found during the audit process. The report is
        organized by severity and table, making it easy to prioritize fixes.
        
        Args:
            mismatches: List of schema mismatches to report
            
        Returns:
            Formatted audit report in Markdown
            
        Requirements: 7.1, 7.2 (Audit reporting)
        """
        logger.info(f"Generating audit report for {len(mismatches)} mismatches")
        
        if not mismatches:
            report = self._format_markdown(
                "# Schema Audit Report",
                "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "## Summary",
                "",
                "✓ No schema mismatches found. All schemas are consistent!",
                ""
            )
            self.generated_reports.append(report)
            return report
        
        # Categorize mismatches by severity
        critical = [m for m in mismatches if m.severity == Severity.CRITICAL]
        warnings = [m for m in mismatches if m.severity == Severity.WARNING]
        info = [m for m in mismatches if m.severity == Severity.INFO]
        
        # Group by table
        by_table: Dict[str, List[Mismatch]] = {}
        for mismatch in mismatches:
            if mismatch.table_name not in by_table:
                by_table[mismatch.table_name] = []
            by_table[mismatch.table_name].append(mismatch)
        
        # Build report sections
        sections = [
            "# Schema Audit Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Mismatches:** {len(mismatches)}",
            "",
            "## Summary",
            "",
            f"- 🔴 **Critical:** {len(critical)} (will cause runtime errors)",
            f"- 🟡 **Warning:** {len(warnings)} (potential issues)",
            f"- 🔵 **Info:** {len(info)} (informational)",
            "",
            f"**Tables Affected:** {len(by_table)}",
            "",
            "---",
            ""
        ]
        
        # Add critical mismatches section
        if critical:
            sections.extend(self._format_mismatch_section(
                "Critical Issues",
                critical,
                "🔴",
                "These issues will cause runtime errors and must be fixed immediately."
            ))
        
        # Add warning mismatches section
        if warnings:
            sections.extend(self._format_mismatch_section(
                "Warnings",
                warnings,
                "🟡",
                "These issues may cause problems and should be reviewed."
            ))
        
        # Add info mismatches section
        if info:
            sections.extend(self._format_mismatch_section(
                "Informational",
                info,
                "🔵",
                "These are informational notices about schema differences."
            ))
        
        # Add table-by-table breakdown
        sections.extend([
            "---",
            "",
            "## Mismatches by Table",
            ""
        ])
        
        for table_name in sorted(by_table.keys()):
            table_mismatches = by_table[table_name]
            sections.append(f"### Table: `{table_name}`")
            sections.append("")
            sections.append(f"**Issues:** {len(table_mismatches)}")
            sections.append("")
            
            for mismatch in table_mismatches:
                sections.extend(self._format_single_mismatch(mismatch))
            
            sections.append("")
        
        report = self._format_markdown(*sections)
        self.generated_reports.append(report)
        
        logger.info("Audit report generated successfully")
        return report
    
    def _format_mismatch_section(
        self,
        title: str,
        mismatches: List[Mismatch],
        icon: str,
        description: str
    ) -> List[str]:
        """
        Format a section of mismatches with consistent styling.
        
        Args:
            title: Section title
            mismatches: List of mismatches for this section
            icon: Icon/emoji for this severity level
            description: Description of this severity level
            
        Returns:
            List of formatted lines
        """
        lines = [
            f"## {icon} {title}",
            "",
            description,
            "",
            f"**Count:** {len(mismatches)}",
            ""
        ]
        
        for i, mismatch in enumerate(mismatches, 1):
            lines.append(f"### {i}. {mismatch.mismatch_type.value}")
            lines.append("")
            lines.append(f"- **Table:** `{mismatch.table_name}`")
            
            if mismatch.column_name:
                lines.append(f"- **Column:** `{mismatch.column_name}`")
            
            if mismatch.expected_value:
                lines.append(f"- **Expected:** `{mismatch.expected_value}`")
            
            if mismatch.actual_value:
                lines.append(f"- **Actual:** `{mismatch.actual_value}`")
            
            if mismatch.locations:
                lines.append(f"- **Locations:** {len(mismatch.locations)} occurrence(s)")
                for loc in mismatch.locations[:3]:  # Show first 3 locations
                    lines.append(f"  - `{loc.file_path}:{loc.line_number}`")
                if len(mismatch.locations) > 3:
                    lines.append(f"  - ... and {len(mismatch.locations) - 3} more")
            
            if mismatch.fix_suggestion:
                lines.append(f"- **Fix Suggestion:** {mismatch.fix_suggestion}")
            
            lines.append("")
        
        return lines
    
    def _format_single_mismatch(self, mismatch: Mismatch) -> List[str]:
        """
        Format a single mismatch for display.
        
        Args:
            mismatch: Mismatch to format
            
        Returns:
            List of formatted lines
        """
        severity_icons = {
            Severity.CRITICAL: "🔴",
            Severity.WARNING: "🟡",
            Severity.INFO: "🔵"
        }
        
        icon = severity_icons.get(mismatch.severity, "")
        
        lines = [
            f"**{icon} {mismatch.mismatch_type.value}** ({mismatch.severity.value})",
            ""
        ]
        
        if mismatch.column_name:
            lines.append(f"- Column: `{mismatch.column_name}`")
        
        if mismatch.expected_value and mismatch.actual_value:
            lines.append(f"- Expected: `{mismatch.expected_value}` | Actual: `{mismatch.actual_value}`")
        
        if mismatch.locations:
            lines.append(f"- Found in {len(mismatch.locations)} location(s)")
        
        if mismatch.fix_suggestion:
            lines.append(f"- Fix: {mismatch.fix_suggestion}")
        
        lines.append("")
        return lines

    def generate_fix_report(self, fix_report: FixReport) -> str:
        """
        Generate fix report documenting all changes made.
        
        This method creates a detailed report of all fixes that were applied,
        including before/after code snippets, success/failure status, and
        file locations.
        
        Args:
            fix_report: FixReport object containing fix details
            
        Returns:
            Formatted fix report in Markdown
            
        Requirements: 7.2 (Fix reporting)
        """
        logger.info(f"Generating fix report for {len(fix_report.fixes)} fixes")
        
        if not fix_report.fixes:
            report = self._format_markdown(
                "# Fix Report",
                "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "No fixes were applied.",
                ""
            )
            self.generated_reports.append(report)
            return report
        
        # Group fixes by file
        fixes_by_file: Dict[str, List[Fix]] = {}
        for fix in fix_report.fixes:
            if fix.file_path not in fixes_by_file:
                fixes_by_file[fix.file_path] = []
            fixes_by_file[fix.file_path].append(fix)
        
        # Build report
        sections = [
            "# Fix Report",
            "",
            f"**Generated:** {fix_report.timestamp.strftime('%Y-%m-%d %H:%M:%S') if fix_report.timestamp else 'N/A'}",
            f"**Total Fixes:** {len(fix_report.fixes)}",
            f"**Files Modified:** {fix_report.total_files_modified}",
            f"**Successful:** {fix_report.total_fixes_applied}",
            f"**Failed:** {fix_report.total_fixes_failed}",
            f"**Success Rate:** {fix_report.get_success_rate():.1f}%",
            ""
        ]
        
        if fix_report.backup_directory:
            sections.extend([
                f"**Backup Directory:** `{fix_report.backup_directory}`",
                ""
            ])
        
        sections.extend([
            "---",
            "",
            "## Summary by File",
            ""
        ])
        
        # Add file-by-file breakdown
        for file_path in sorted(fixes_by_file.keys()):
            file_fixes = fixes_by_file[file_path]
            successful = sum(1 for f in file_fixes if f.applied)
            failed = len(file_fixes) - successful
            
            sections.append(f"### `{file_path}`")
            sections.append("")
            sections.append(f"- **Total Changes:** {len(file_fixes)}")
            sections.append(f"- **Successful:** {successful}")
            sections.append(f"- **Failed:** {failed}")
            sections.append("")
            
            for i, fix in enumerate(file_fixes, 1):
                status = "✓" if fix.applied else "✗"
                sections.append(f"#### Change {i}: {status} {fix.mismatch.mismatch_type.value}")
                sections.append("")
                sections.append(f"- **Line:** {fix.line_number}")
                sections.append(f"- **Table:** `{fix.mismatch.table_name}`")
                
                if fix.mismatch.column_name:
                    sections.append(f"- **Column:** `{fix.mismatch.column_name}`")
                
                if fix.error:
                    sections.append(f"- **Error:** {fix.error}")
                
                sections.append("")
                sections.append("**Before:**")
                sections.append("```python")
                sections.append(fix.old_code)
                sections.append("```")
                sections.append("")
                sections.append("**After:**")
                sections.append("```python")
                sections.append(fix.new_code)
                sections.append("```")
                sections.append("")
        
        report = self._format_markdown(*sections)
        self.generated_reports.append(report)
        
        logger.info("Fix report generated successfully")
        return report
    
    def generate_schema_documentation(self, schema: DatabaseSchema) -> str:
        """
        Generate comprehensive schema documentation in Markdown.
        
        This method creates detailed documentation for the database schema,
        including all tables, columns, data types, constraints, and relationships.
        
        Args:
            schema: DatabaseSchema object to document
            
        Returns:
            Formatted schema documentation in Markdown
            
        Requirements: 7.1 (Schema documentation)
        """
        logger.info(f"Generating schema documentation for {len(schema.tables)} tables")
        
        sections = [
            "# Database Schema Documentation",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Schema Version:** {schema.version}",
            f"**Source:** {schema.source_file}",
            ""
        ]
        
        if schema.extracted_at:
            sections.append(f"**Extracted:** {schema.extracted_at.strftime('%Y-%m-%d %H:%M:%S')}")
            sections.append("")
        
        sections.extend([
            "## Overview",
            "",
            f"This database contains **{len(schema.tables)}** tables.",
            ""
        ])
        
        # Get structured data tables
        structured_tables = schema.get_structured_data_tables()
        if structured_tables:
            sections.extend([
                f"**Structured Data Tables:** {len(structured_tables)}",
                ""
            ])
        
        sections.extend([
            "---",
            "",
            "## Table of Contents",
            ""
        ])
        
        # Add table of contents
        for table_name in sorted(schema.tables.keys()):
            sections.append(f"- [{table_name}](#{table_name.lower().replace('_', '-')})")
        
        sections.extend([
            "",
            "---",
            ""
        ])
        
        # Document each table
        for table_name in sorted(schema.tables.keys()):
            table = schema.tables[table_name]
            sections.extend(self._format_table_documentation(table))
        
        report = self._format_markdown(*sections)
        self.generated_reports.append(report)
        
        logger.info("Schema documentation generated successfully")
        return report
    
    def _format_table_documentation(self, table: TableSchema) -> List[str]:
        """
        Format documentation for a single table.
        
        Args:
            table: TableSchema to document
            
        Returns:
            List of formatted lines
        """
        lines = [
            f"## {table.name}",
            "",
            f"**Columns:** {len(table.columns)}",
            ""
        ]
        
        if table.primary_key:
            lines.append(f"**Primary Key:** {', '.join(f'`{col}`' for col in table.primary_key)}")
            lines.append("")
        
        # Column table
        lines.extend([
            "### Columns",
            "",
            "| Column | Type | Nullable | Default | Notes |",
            "|--------|------|----------|---------|-------|"
        ])
        
        for column in table.columns:
            # Build type string
            type_str = column.data_type
            if column.max_length:
                type_str += f"({column.max_length})"
            elif column.precision and column.scale:
                type_str += f"({column.precision},{column.scale})"
            elif column.precision:
                type_str += f"({column.precision})"
            
            nullable = "Yes" if column.nullable else "No"
            default = column.default_value if column.default_value else "-"
            
            notes = []
            if column.is_identity:
                notes.append("Identity")
            
            notes_str = ", ".join(notes) if notes else "-"
            
            lines.append(f"| `{column.name}` | {type_str} | {nullable} | {default} | {notes_str} |")
        
        lines.append("")
        
        # Foreign keys
        if table.foreign_keys:
            lines.extend([
                "### Foreign Keys",
                "",
                "| Name | Column | References | On Delete | On Update |",
                "|------|--------|------------|-----------|-----------|"
            ])
            
            for fk in table.foreign_keys:
                on_delete = fk.on_delete if fk.on_delete else "-"
                on_update = fk.on_update if fk.on_update else "-"
                lines.append(
                    f"| `{fk.name}` | `{fk.column}` | "
                    f"`{fk.referenced_table}.{fk.referenced_column}` | "
                    f"{on_delete} | {on_update} |"
                )
            
            lines.append("")
        
        # Indexes
        if table.indexes:
            lines.extend([
                "### Indexes",
                "",
                "| Name | Columns | Unique | Clustered |",
                "|------|---------|--------|-----------|"
            ])
            
            for index in table.indexes:
                columns_str = ", ".join(f"`{col}`" for col in index.columns)
                unique = "Yes" if index.is_unique else "No"
                clustered = "Yes" if index.is_clustered else "No"
                lines.append(f"| `{index.name}` | {columns_str} | {unique} | {clustered} |")
            
            lines.append("")
        
        # Constraints
        if table.constraints:
            lines.extend([
                "### Constraints",
                ""
            ])
            
            for constraint in table.constraints:
                lines.append(f"- **{constraint.name}** ({constraint.constraint_type})")
                lines.append(f"  - Definition: `{constraint.definition}`")
                if constraint.columns:
                    lines.append(f"  - Columns: {', '.join(f'`{col}`' for col in constraint.columns)}")
            
            lines.append("")
        
        lines.extend([
            "---",
            ""
        ])
        
        return lines
    
    def generate_erd_diagram(self, schema: DatabaseSchema) -> str:
        """
        Generate Entity Relationship Diagram in Mermaid format.
        
        This method creates a Mermaid ERD diagram showing all tables,
        their columns, and relationships (foreign keys) in the database schema.
        
        Args:
            schema: DatabaseSchema object to visualize
            
        Returns:
            Mermaid ERD diagram as string
            
        Requirements: 7.3 (ERD diagram generation)
        """
        logger.info(f"Generating ERD diagram for {len(schema.tables)} tables")
        
        lines = [
            "```mermaid",
            "erDiagram"
        ]
        
        # Add table definitions with columns
        for table_name in sorted(schema.tables.keys()):
            table = schema.tables[table_name]
            
            # Start table definition
            lines.append(f"    {table_name} {{")
            
            # Add columns
            for column in table.columns:
                # Build type string
                type_str = column.data_type
                if column.max_length:
                    type_str += f"({column.max_length})"
                elif column.precision and column.scale:
                    type_str += f"({column.precision},{column.scale})"
                
                # Add column attributes
                attributes = []
                if column.is_identity:
                    attributes.append("PK")
                if not column.nullable:
                    attributes.append("NOT NULL")
                
                attr_str = f" {','.join(attributes)}" if attributes else ""
                
                lines.append(f"        {type_str} {column.name}{attr_str}")
            
            lines.append("    }")
        
        # Add relationships (foreign keys)
        for table_name in sorted(schema.tables.keys()):
            table = schema.tables[table_name]
            
            for fk in table.foreign_keys:
                # Determine relationship cardinality
                # For simplicity, we use ||--o{ (one-to-many) for all FKs
                # In a more sophisticated implementation, we could analyze
                # constraints to determine exact cardinality
                lines.append(
                    f"    {fk.referenced_table} ||--o{{ {table_name} : \"{fk.name}\""
                )
        
        lines.append("```")
        
        diagram = "\n".join(lines)
        self.generated_reports.append(diagram)
        
        logger.info("ERD diagram generated successfully")
        return diagram
    
    def generate_mapping_table(
        self,
        operations_map: Dict[str, List[TableOperation]]
    ) -> str:
        """
        Generate scraper-to-table mapping documentation.
        
        This method creates a table showing which scraper functions write
        to which database tables, making it easy to understand data flow.
        
        Args:
            operations_map: Dictionary mapping table names to operations
            
        Returns:
            Formatted mapping table in Markdown
            
        Requirements: 7.4 (Scraper-table mapping)
        """
        logger.info(f"Generating mapping table for {len(operations_map)} tables")
        
        # Build scraper to tables mapping
        scraper_to_tables: Dict[str, List[str]] = {}
        table_to_scrapers: Dict[str, List[str]] = {}
        
        for table_name, operations in operations_map.items():
            for operation in operations:
                # Extract scraper name from file path
                file_path = Path(operation.file_path)
                scraper_name = file_path.stem  # filename without extension
                
                # Add to scraper -> tables mapping
                if scraper_name not in scraper_to_tables:
                    scraper_to_tables[scraper_name] = []
                if table_name not in scraper_to_tables[scraper_name]:
                    scraper_to_tables[scraper_name].append(table_name)
                
                # Add to table -> scrapers mapping
                if table_name not in table_to_scrapers:
                    table_to_scrapers[table_name] = []
                if scraper_name not in table_to_scrapers[table_name]:
                    table_to_scrapers[table_name].append(scraper_name)
        
        sections = [
            "# Scraper-Table Mapping",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Tables:** {len(table_to_scrapers)}",
            f"**Total Scrapers:** {len(scraper_to_tables)}",
            "",
            "---",
            "",
            "## Scrapers by Table",
            "",
            "This section shows which scrapers write to each table.",
            "",
            "| Table | Scrapers | Operations |",
            "|-------|----------|------------|"
        ]
        
        # Add table -> scrapers mapping
        for table_name in sorted(table_to_scrapers.keys()):
            scrapers = table_to_scrapers[table_name]
            operations = operations_map.get(table_name, [])
            scrapers_str = ", ".join(f"`{s}`" for s in sorted(scrapers))
            sections.append(f"| `{table_name}` | {scrapers_str} | {len(operations)} |")
        
        sections.extend([
            "",
            "---",
            "",
            "## Tables by Scraper",
            "",
            "This section shows which tables each scraper writes to.",
            "",
            "| Scraper | Tables | Total Operations |",
            "|---------|--------|------------------|"
        ])
        
        # Add scraper -> tables mapping
        for scraper_name in sorted(scraper_to_tables.keys()):
            tables = scraper_to_tables[scraper_name]
            tables_str = ", ".join(f"`{t}`" for t in sorted(tables))
            
            # Count total operations for this scraper
            total_ops = sum(
                len([op for op in operations_map.get(table, [])
                     if Path(op.file_path).stem == scraper_name])
                for table in tables
            )
            
            sections.append(f"| `{scraper_name}` | {tables_str} | {total_ops} |")
        
        sections.extend([
            "",
            "---",
            "",
            "## Detailed Operations",
            ""
        ])
        
        # Add detailed breakdown by table
        for table_name in sorted(operations_map.keys()):
            operations = operations_map[table_name]
            sections.append(f"### Table: `{table_name}`")
            sections.append("")
            sections.append(f"**Total Operations:** {len(operations)}")
            sections.append("")
            
            # Group by operation type
            by_type: Dict[str, List[TableOperation]] = {}
            for op in operations:
                if op.operation_type not in by_type:
                    by_type[op.operation_type] = []
                by_type[op.operation_type].append(op)
            
            for op_type in sorted(by_type.keys()):
                ops = by_type[op_type]
                sections.append(f"**{op_type}:** {len(ops)} operation(s)")
                sections.append("")
                
                for op in ops[:5]:  # Show first 5 operations
                    sections.append(f"- `{op.file_path}:{op.line_number}`")
                    if op.columns:
                        sections.append(f"  - Columns: {', '.join(f'`{c}`' for c in op.columns)}")
                
                if len(ops) > 5:
                    sections.append(f"- ... and {len(ops) - 5} more")
                
                sections.append("")
        
        report = self._format_markdown(*sections)
        self.generated_reports.append(report)
        
        logger.info("Mapping table generated successfully")
        return report
    
    def generate_changelog(self, fixes: List[Fix]) -> str:
        """
        Generate changelog documenting all changes made.
        
        This method creates a changelog that documents all modifications
        made to the codebase, organized by file and change type.
        
        Args:
            fixes: List of Fix objects representing changes
            
        Returns:
            Formatted changelog in Markdown
            
        Requirements: 7.5 (Changelog generation)
        """
        logger.info(f"Generating changelog for {len(fixes)} fixes")
        
        if not fixes:
            report = self._format_markdown(
                "# Changelog",
                "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "No changes were made.",
                ""
            )
            self.generated_reports.append(report)
            return report
        
        # Group by file
        by_file: Dict[str, List[Fix]] = {}
        for fix in fixes:
            if fix.file_path not in by_file:
                by_file[fix.file_path] = []
            by_file[fix.file_path].append(fix)
        
        # Group by change type
        by_type: Dict[str, List[Fix]] = {}
        for fix in fixes:
            change_type = fix.mismatch.mismatch_type.value
            if change_type not in by_type:
                by_type[change_type] = []
            by_type[change_type].append(fix)
        
        sections = [
            "# Changelog",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Changes:** {len(fixes)}",
            f"**Files Modified:** {len(by_file)}",
            "",
            "## Summary",
            ""
        ]
        
        # Add summary by change type
        for change_type in sorted(by_type.keys()):
            changes = by_type[change_type]
            sections.append(f"- **{change_type}:** {len(changes)} change(s)")
        
        sections.extend([
            "",
            "---",
            "",
            "## Changes by File",
            ""
        ])
        
        # Add detailed changes by file
        for file_path in sorted(by_file.keys()):
            file_fixes = by_file[file_path]
            sections.append(f"### `{file_path}`")
            sections.append("")
            sections.append(f"**Changes:** {len(file_fixes)}")
            sections.append("")
            
            for i, fix in enumerate(file_fixes, 1):
                sections.append(f"#### Change {i}: {fix.mismatch.mismatch_type.value}")
                sections.append("")
                sections.append(f"- **Line:** {fix.line_number}")
                sections.append(f"- **Table:** `{fix.mismatch.table_name}`")
                
                if fix.mismatch.column_name:
                    sections.append(f"- **Column:** `{fix.mismatch.column_name}`")
                
                if fix.mismatch.expected_value and fix.mismatch.actual_value:
                    sections.append(
                        f"- **Change:** `{fix.mismatch.actual_value}` → "
                        f"`{fix.mismatch.expected_value}`"
                    )
                
                sections.append("")
                sections.append("**Before:**")
                sections.append("```python")
                sections.append(fix.old_code)
                sections.append("```")
                sections.append("")
                sections.append("**After:**")
                sections.append("```python")
                sections.append(fix.new_code)
                sections.append("```")
                sections.append("")
        
        report = self._format_markdown(*sections)
        self.generated_reports.append(report)
        
        logger.info("Changelog generated successfully")
        return report
    
    def generate_statistics(
        self,
        schema: Optional[DatabaseSchema] = None,
        mismatches: Optional[List[Mismatch]] = None,
        fixes: Optional[List[Fix]] = None,
        operations_map: Optional[Dict[str, List[TableOperation]]] = None
    ) -> str:
        """
        Generate summary statistics for the audit process.
        
        This method creates a comprehensive summary of statistics including
        table counts, mismatch counts, fix counts, and operation counts.
        
        Args:
            schema: Optional DatabaseSchema for table statistics
            mismatches: Optional list of mismatches for mismatch statistics
            fixes: Optional list of fixes for fix statistics
            operations_map: Optional operations map for operation statistics
            
        Returns:
            Formatted statistics report in Markdown
            
        Requirements: 7.6 (Summary statistics)
        """
        logger.info("Generating summary statistics")
        
        sections = [
            "# Summary Statistics",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]
        
        # Schema statistics
        if schema:
            structured_tables = schema.get_structured_data_tables()
            total_columns = sum(len(table.columns) for table in schema.tables.values())
            total_fks = sum(len(table.foreign_keys) for table in schema.tables.values())
            total_indexes = sum(len(table.indexes) for table in schema.tables.values())
            
            sections.extend([
                "## Schema Statistics",
                "",
                f"- **Total Tables:** {len(schema.tables)}",
                f"- **Structured Data Tables:** {len(structured_tables)}",
                f"- **Total Columns:** {total_columns}",
                f"- **Total Foreign Keys:** {total_fks}",
                f"- **Total Indexes:** {total_indexes}",
                f"- **Schema Version:** {schema.version}",
                ""
            ])
        
        # Mismatch statistics
        if mismatches:
            critical = sum(1 for m in mismatches if m.severity == Severity.CRITICAL)
            warnings = sum(1 for m in mismatches if m.severity == Severity.WARNING)
            info = sum(1 for m in mismatches if m.severity == Severity.INFO)
            
            # Count by type
            by_type: Dict[str, int] = {}
            for mismatch in mismatches:
                mtype = mismatch.mismatch_type.value
                by_type[mtype] = by_type.get(mtype, 0) + 1
            
            # Count affected tables
            affected_tables = len(set(m.table_name for m in mismatches))
            
            sections.extend([
                "## Mismatch Statistics",
                "",
                f"- **Total Mismatches:** {len(mismatches)}",
                f"- **Critical:** {critical}",
                f"- **Warnings:** {warnings}",
                f"- **Info:** {info}",
                f"- **Tables Affected:** {affected_tables}",
                "",
                "**By Type:**",
                ""
            ])
            
            for mtype in sorted(by_type.keys()):
                count = by_type[mtype]
                sections.append(f"- {mtype}: {count}")
            
            sections.append("")
        
        # Fix statistics
        if fixes:
            applied = sum(1 for f in fixes if f.applied)
            failed = len(fixes) - applied
            files_modified = len(set(f.file_path for f in fixes))
            
            # Count by type
            by_type: Dict[str, int] = {}
            for fix in fixes:
                ftype = fix.mismatch.mismatch_type.value
                by_type[ftype] = by_type.get(ftype, 0) + 1
            
            sections.extend([
                "## Fix Statistics",
                "",
                f"- **Total Fixes:** {len(fixes)}",
                f"- **Successfully Applied:** {applied}",
                f"- **Failed:** {failed}",
                f"- **Success Rate:** {(applied / len(fixes) * 100):.1f}%",
                f"- **Files Modified:** {files_modified}",
                "",
                "**By Type:**",
                ""
            ])
            
            for ftype in sorted(by_type.keys()):
                count = by_type[ftype]
                sections.append(f"- {ftype}: {count}")
            
            sections.append("")
        
        # Operations statistics
        if operations_map:
            total_operations = sum(len(ops) for ops in operations_map.values())
            
            # Count by operation type
            by_type: Dict[str, int] = {}
            for operations in operations_map.values():
                for op in operations:
                    by_type[op.operation_type] = by_type.get(op.operation_type, 0) + 1
            
            # Count scrapers
            scrapers = set()
            for operations in operations_map.values():
                for op in operations:
                    scrapers.add(Path(op.file_path).stem)
            
            sections.extend([
                "## Operations Statistics",
                "",
                f"- **Total Operations:** {total_operations}",
                f"- **Tables with Operations:** {len(operations_map)}",
                f"- **Unique Scrapers:** {len(scrapers)}",
                "",
                "**By Operation Type:**",
                ""
            ])
            
            for op_type in sorted(by_type.keys()):
                count = by_type[op_type]
                sections.append(f"- {op_type}: {count}")
            
            sections.append("")
        
        report = self._format_markdown(*sections)
        self.generated_reports.append(report)
        
        logger.info("Statistics generated successfully")
        return report
    
    def _format_markdown(self, *lines: str) -> str:
        """
        Format lines into a Markdown document.
        
        This is a helper method that joins lines with newlines to create
        a properly formatted Markdown document.
        
        Args:
            *lines: Variable number of lines to join
            
        Returns:
            Formatted Markdown string
            
        Requirements: 7.1, 7.2 (Markdown formatting)
        """
        return "\n".join(lines)
