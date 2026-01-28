#!/usr/bin/env python3
"""
Analyze captured logs and classify errors.

This script uses the ErrorClassifier to analyze captured logs from Azure Functions
and generate a detailed error report with classification and suggested fixes.

Usage:
    python analyze_logs.py <log_file_or_directory>
    python analyze_logs.py diagnostic_logs/
    python analyze_logs.py diagnostic_logs/portal_logs_cnbc.txt
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path to import error_classifier
sys.path.insert(0, str(Path(__file__).parent))

from error_classifier import ErrorClassifier, ErrorReport, ErrorType


class LogAnalyzer:
    """Analyzes captured logs and generates error reports."""
    
    def __init__(self):
        self.classifier = ErrorClassifier()
        self.reports: List[ErrorReport] = []
    
    def analyze_log_file(self, log_file_path: str) -> List[ErrorReport]:
        """
        Analyze a single log file.
        
        Args:
            log_file_path: Path to the log file
            
        Returns:
            List of ErrorReport objects
        """
        print(f"\n📄 Analyzing: {log_file_path}")
        
        if not os.path.exists(log_file_path):
            print(f"❌ File not found: {log_file_path}")
            return []
        
        # Read log file
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            print(f"⚠️  File is empty: {log_file_path}")
            return []
        
        # Try to parse as JSON first (for structured logs)
        try:
            data = json.loads(content)
            return self._analyze_json_logs(data, log_file_path)
        except json.JSONDecodeError:
            # Not JSON, treat as plain text logs
            return self._analyze_text_logs(content, log_file_path)
    
    def _analyze_json_logs(self, data: Dict[str, Any], source_file: str) -> List[ErrorReport]:
        """Analyze JSON-formatted logs."""
        reports = []
        
        # Check for Application Insights format
        if 'errors' in data or 'exceptions' in data or 'failed_requests' in data:
            print("📊 Detected Application Insights format")
            
            # Analyze errors
            for error in data.get('errors', []):
                report = self._create_report_from_appinsights_error(error, source_file)
                if report:
                    reports.append(report)
            
            # Analyze exceptions
            for exception in data.get('exceptions', []):
                report = self._create_report_from_appinsights_exception(exception, source_file)
                if report:
                    reports.append(report)
            
            # Analyze failed requests
            for request in data.get('failed_requests', []):
                report = self._create_report_from_appinsights_request(request, source_file)
                if report:
                    reports.append(report)
            
            if not reports:
                print("⚠️  No errors found in Application Insights data")
        
        # Check for HTTP response format
        elif 'status_code' in data:
            print("📊 Detected HTTP response format")
            report = self._create_report_from_http_response(data, source_file)
            if report:
                reports.append(report)
        
        return reports
    
    def _analyze_text_logs(self, content: str, source_file: str) -> List[ErrorReport]:
        """Analyze plain text logs."""
        reports = []
        
        print("📊 Analyzing plain text logs")
        
        # Look for error patterns in text
        lines = content.split('\n')
        
        # Extract function name from filename or content
        function_name = self._extract_function_name(source_file, content)
        
        # Look for error indicators
        error_lines = []
        stack_trace_lines = []
        in_stack_trace = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Check for error indicators
            if any(indicator in line_lower for indicator in ['[error]', 'error:', 'exception:', 'failed', 'traceback']):
                error_lines.append(line)
                in_stack_trace = True
            elif in_stack_trace:
                # Continue collecting stack trace
                if line.strip().startswith('at ') or line.strip().startswith('File ') or '  ' in line[:10]:
                    stack_trace_lines.append(line)
                elif line.strip():
                    # End of stack trace
                    in_stack_trace = False
        
        # If we found errors, create a report
        if error_lines:
            error_message = '\n'.join(error_lines)
            stack_trace = '\n'.join(stack_trace_lines) if stack_trace_lines else error_message
            
            report = self.classifier.create_error_report(
                function_name=function_name,
                error_message=error_message,
                stack_trace=stack_trace,
                http_status_code=500,
                request_id=None,
                timestamp=datetime.utcnow()
            )
            reports.append(report)
            print(f"✅ Found error: {report.error_type.value}")
        else:
            print("⚠️  No error patterns found in text logs")
        
        return reports
    
    def _create_report_from_appinsights_error(self, error: Dict[str, Any], source_file: str) -> Optional[ErrorReport]:
        """Create error report from Application Insights error entry."""
        function_name = error.get('cloud_RoleName', 'unknown_function')
        error_message = error.get('message', 'No error message')
        stack_trace = error.get('details', error_message)
        timestamp_str = error.get('timestamp', datetime.utcnow().isoformat())
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            timestamp = datetime.utcnow()
        
        return self.classifier.create_error_report(
            function_name=function_name,
            error_message=error_message,
            stack_trace=stack_trace,
            http_status_code=500,
            request_id=error.get('operation_Id'),
            timestamp=timestamp
        )
    
    def _create_report_from_appinsights_exception(self, exception: Dict[str, Any], source_file: str) -> Optional[ErrorReport]:
        """Create error report from Application Insights exception entry."""
        function_name = exception.get('cloud_RoleName', 'unknown_function')
        error_message = exception.get('outerMessage', exception.get('innermostMessage', 'No error message'))
        stack_trace = exception.get('details', error_message)
        timestamp_str = exception.get('timestamp', datetime.utcnow().isoformat())
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            timestamp = datetime.utcnow()
        
        return self.classifier.create_error_report(
            function_name=function_name,
            error_message=error_message,
            stack_trace=stack_trace,
            http_status_code=500,
            request_id=exception.get('operation_Id'),
            timestamp=timestamp
        )
    
    def _create_report_from_appinsights_request(self, request: Dict[str, Any], source_file: str) -> Optional[ErrorReport]:
        """Create error report from Application Insights failed request entry."""
        function_name = request.get('name', 'unknown_function')
        result_code = request.get('resultCode', 500)
        error_message = f"Request failed with status code {result_code}"
        url = request.get('url', 'unknown')
        timestamp_str = request.get('timestamp', datetime.utcnow().isoformat())
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            timestamp = datetime.utcnow()
        
        return self.classifier.create_error_report(
            function_name=function_name,
            error_message=error_message,
            stack_trace=f"URL: {url}\nStatus: {result_code}",
            http_status_code=int(result_code),
            request_id=request.get('operation_Id'),
            timestamp=timestamp
        )
    
    def _create_report_from_http_response(self, data: Dict[str, Any], source_file: str) -> Optional[ErrorReport]:
        """Create error report from HTTP response data."""
        status_code = data.get('status_code', 500)
        
        # Only create report for error status codes
        if status_code < 400:
            return None
        
        function_name = self._extract_function_name(source_file, str(data))
        error_message = data.get('body', 'Empty response body')
        
        if not error_message or error_message == '':
            error_message = f"HTTP {status_code} with empty response body"
        
        # Extract additional context
        url = data.get('url', 'unknown')
        execution_time = data.get('execution_time_seconds', 0)
        
        stack_trace = f"URL: {url}\nStatus: {status_code}\nExecution time: {execution_time}s"
        
        timestamp_str = data.get('captured_at', datetime.utcnow().isoformat())
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except:
            timestamp = datetime.utcnow()
        
        return self.classifier.create_error_report(
            function_name=function_name,
            error_message=error_message,
            stack_trace=stack_trace,
            http_status_code=status_code,
            request_id=None,
            timestamp=timestamp
        )
    
    def _extract_function_name(self, filename: str, content: str) -> str:
        """Extract function name from filename or content."""
        # Try to extract from filename
        filename_lower = filename.lower()
        for scraper in ['cnbc', 'cnn', 'reuters', 'guardian', 'oilprice', 
                       'bisnis', 'kompas', 'kontan', 'tempo']:
            if scraper in filename_lower:
                return f"{scraper}_scraper_function"
        
        # Try to extract from content
        content_lower = content.lower()
        for scraper in ['cnbc', 'cnn', 'reuters', 'guardian', 'oilprice',
                       'bisnis', 'kompas', 'kontan', 'tempo']:
            if f"{scraper}_scraper" in content_lower:
                return f"{scraper}_scraper_function"
        
        return "unknown_function"
    
    def analyze_directory(self, directory_path: str) -> List[ErrorReport]:
        """
        Analyze all log files in a directory.
        
        Args:
            directory_path: Path to directory containing log files
            
        Returns:
            List of all ErrorReport objects
        """
        print(f"\n📁 Analyzing directory: {directory_path}")
        
        if not os.path.isdir(directory_path):
            print(f"❌ Not a directory: {directory_path}")
            return []
        
        all_reports = []
        
        # Find all log files
        log_files = []
        for ext in ['.txt', '.log', '.json']:
            log_files.extend(Path(directory_path).glob(f'*{ext}'))
        
        if not log_files:
            print(f"⚠️  No log files found in {directory_path}")
            return []
        
        print(f"Found {len(log_files)} log file(s)")
        
        # Analyze each file
        for log_file in log_files:
            reports = self.analyze_log_file(str(log_file))
            all_reports.extend(reports)
        
        return all_reports
    
    def generate_report(self, reports: List[ErrorReport], output_file: Optional[str] = None) -> str:
        """
        Generate a comprehensive error analysis report.
        
        Args:
            reports: List of ErrorReport objects
            output_file: Optional path to save report
            
        Returns:
            Report content as string
        """
        if not reports:
            report_content = "# Error Analysis Report\n\n**No errors found in analyzed logs.**\n"
            print("\n✅ No errors found")
            return report_content
        
        # Generate report
        report_lines = [
            "# Error Analysis Report",
            "",
            f"**Generated**: {datetime.utcnow().isoformat()}Z",
            f"**Total Errors**: {len(reports)}",
            "",
            "---",
            ""
        ]
        
        # Group by error type
        errors_by_type: Dict[ErrorType, List[ErrorReport]] = {}
        for report in reports:
            if report.error_type not in errors_by_type:
                errors_by_type[report.error_type] = []
            errors_by_type[report.error_type].append(report)
        
        # Summary section
        report_lines.extend([
            "## Summary",
            "",
            "### Error Distribution",
            ""
        ])
        
        for error_type, error_reports in sorted(errors_by_type.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(error_reports)
            percentage = (count / len(reports)) * 100
            report_lines.append(f"- **{error_type.value}**: {count} ({percentage:.1f}%)")
        
        report_lines.extend(["", "---", ""])
        
        # Detailed analysis for each error
        report_lines.extend([
            "## Detailed Error Analysis",
            ""
        ])
        
        for i, report in enumerate(reports, 1):
            report_lines.extend([
                f"### Error {i}: {report.function_name}",
                "",
                f"**Type**: {report.error_type.value}",
                f"**Status Code**: HTTP {report.http_status_code}",
                f"**Timestamp**: {report.timestamp.isoformat()}Z",
                ""
            ])
            
            if report.request_id:
                report_lines.append(f"**Request ID**: {report.request_id}")
                report_lines.append("")
            
            # Error message
            report_lines.extend([
                "#### Error Message",
                "",
                "```",
                report.error_message[:500] + ("..." if len(report.error_message) > 500 else ""),
                "```",
                ""
            ])
            
            # Stack trace (truncated)
            if report.stack_trace and report.stack_trace != report.error_message:
                report_lines.extend([
                    "#### Stack Trace",
                    "",
                    "```",
                    report.stack_trace[:500] + ("..." if len(report.stack_trace) > 500 else ""),
                    "```",
                    ""
                ])
            
            # Classification details
            report_lines.extend([
                "#### Classification Details",
                ""
            ])
            
            # Extract specific details based on error type
            if report.error_type == ErrorType.IMPORT_ERROR or report.error_type == ErrorType.DEPENDENCY_ERROR:
                missing_package = self.classifier.extract_missing_package(report.error_message, report.stack_trace)
                if missing_package:
                    report_lines.append(f"**Missing Package**: `{missing_package}`")
            
            if report.error_type == ErrorType.CONFIGURATION_ERROR:
                missing_config = self.classifier.extract_missing_configuration(report.error_message, report.stack_trace)
                if missing_config:
                    report_lines.append(f"**Missing Configuration**: `{missing_config}`")
            
            if report.error_type == ErrorType.NETWORK_ERROR:
                status_code = self.classifier.extract_http_status_code(report.error_message, report.stack_trace)
                if status_code:
                    report_lines.append(f"**HTTP Status Code**: {status_code}")
            
            if report.error_type == ErrorType.DATABASE_ERROR:
                is_connection = self.classifier.is_connection_error(report.error_message, report.stack_trace)
                error_subtype = "Connection Error" if is_connection else "Query Error"
                report_lines.append(f"**Database Error Type**: {error_subtype}")
            
            # Suggested fix
            suggested_fix = self.classifier.get_suggested_fix(report)
            report_lines.extend([
                "",
                "#### Suggested Fix",
                "",
                f"```",
                suggested_fix,
                "```",
                "",
                "---",
                ""
            ])
        
        # Recommendations section
        report_lines.extend([
            "## Recommendations",
            "",
            "### Priority Actions",
            ""
        ])
        
        # Prioritize by error type
        priority_order = [
            ErrorType.IMPORT_ERROR,
            ErrorType.DEPENDENCY_ERROR,
            ErrorType.CONFIGURATION_ERROR,
            ErrorType.DATABASE_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.RUNTIME_ERROR
        ]
        
        for error_type in priority_order:
            if error_type in errors_by_type:
                count = len(errors_by_type[error_type])
                report_lines.append(f"**{count} {error_type.value}(s)**:")
                
                # Get unique suggested fixes
                fixes = set()
                for report in errors_by_type[error_type]:
                    fixes.add(self.classifier.get_suggested_fix(report))
                
                for fix in fixes:
                    report_lines.append(f"- {fix}")
                
                report_lines.append("")
        
        report_lines.extend([
            "### Next Steps",
            "",
            "1. **Review each error** in the detailed analysis section",
            "2. **Apply suggested fixes** based on error classification",
            "3. **Test locally** if possible before deploying",
            "4. **Redeploy functions** with fixes applied",
            "5. **Verify fixes** by testing each function",
            "6. **Monitor logs** to ensure errors are resolved",
            "",
            "---",
            "",
            f"**Report generated by**: Error Classification System",
            f"**Analysis completed**: {datetime.utcnow().isoformat()}Z"
        ])
        
        report_content = '\n'.join(report_lines)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"\n✅ Report saved to: {output_file}")
        
        return report_content


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <log_file_or_directory>")
        print("\nExamples:")
        print("  python analyze_logs.py diagnostic_logs/")
        print("  python analyze_logs.py diagnostic_logs/portal_logs_cnbc.txt")
        print("  python analyze_logs.py diagnostic_logs/cnbc_response_20260128_155514.json")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    print("=" * 80)
    print("ERROR LOG ANALYZER")
    print("=" * 80)
    
    analyzer = LogAnalyzer()
    
    # Analyze input
    if os.path.isdir(input_path):
        reports = analyzer.analyze_directory(input_path)
    elif os.path.isfile(input_path):
        reports = analyzer.analyze_log_file(input_path)
    else:
        print(f"❌ Path not found: {input_path}")
        sys.exit(1)
    
    # Generate report
    output_file = os.path.join(
        os.path.dirname(input_path) if os.path.isfile(input_path) else input_path,
        f"ERROR_CLASSIFICATION_REPORT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    )
    
    report_content = analyzer.generate_report(reports, output_file)
    
    # Print summary
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\n📊 Total errors analyzed: {len(reports)}")
    
    if reports:
        # Count by type
        type_counts = {}
        for report in reports:
            type_counts[report.error_type] = type_counts.get(report.error_type, 0) + 1
        
        print("\n📈 Error distribution:")
        for error_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {error_type.value}: {count}")
        
        print(f"\n📄 Full report: {output_file}")
    else:
        print("\n✅ No errors found in analyzed logs")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
