#!/usr/bin/env python3
"""
Azure Functions Diagnostic Tool

Command-line tool for debugging Azure Functions scraper errors.

Usage:
    python diagnostic_tool.py check-access          # Check Azure CLI access
    python diagnostic_tool.py tail-logs [seconds]   # Tail logs in real-time
    python diagnostic_tool.py get-errors [minutes]  # Get recent errors
    python diagnostic_tool.py analyze-function <name> [minutes]  # Analyze specific function
    python diagnostic_tool.py classify-error <log_file>  # Classify errors from log file
    python diagnostic_tool.py start-session <session_id>  # Start diagnostic session
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from diagnostics import (
    AzureLogAccess,
    ErrorClassifier,
    LogParser,
    DiagnosticSession,
    ErrorType
)


def check_access(args):
    """Check Azure CLI access and print instructions."""
    log_access = AzureLogAccess()
    log_access.print_access_instructions()


def tail_logs(args):
    """Tail function app logs in real-time."""
    timeout = args.timeout or 30
    
    print(f"Tailing logs for {timeout} seconds...")
    print("=" * 60)
    
    log_access = AzureLogAccess()
    entries = log_access.tail_logs(timeout_seconds=timeout)
    
    if not entries:
        print("No log entries captured.")
        print("\nTroubleshooting:")
        print("1. Ensure Azure CLI is installed and you're logged in")
        print("2. Verify function app name and resource group are correct")
        print("3. Try accessing logs via Azure Portal")
        return
    
    print(f"\nCaptured {len(entries)} log entries:\n")
    
    for entry in entries:
        level_color = {
            "ERROR": "\033[91m",  # Red
            "WARNING": "\033[93m",  # Yellow
            "INFO": "\033[92m",  # Green
            "DEBUG": "\033[94m"  # Blue
        }.get(entry.level.upper(), "")
        reset_color = "\033[0m"
        
        print(f"{level_color}[{entry.timestamp.strftime('%H:%M:%S')}] {entry.level}: {entry.message}{reset_color}")
        
        if entry.exception:
            print(f"  Exception: {entry.exception[:200]}...")
    
    # Show error summary
    error_entries = [e for e in entries if e.is_error()]
    if error_entries:
        print(f"\n⚠️  Found {len(error_entries)} errors")
        print("\nRun with --classify to classify these errors")


def get_errors(args):
    """Get recent errors from Application Insights."""
    minutes = args.minutes or 30
    
    print(f"Fetching errors from last {minutes} minutes...")
    print("=" * 60)
    
    log_access = AzureLogAccess()
    entries = log_access.get_recent_errors(minutes=minutes)
    
    if not entries:
        print("✅ No errors found in the specified time range")
        return
    
    print(f"\n❌ Found {len(entries)} error entries:\n")
    
    # Classify errors if requested
    if args.classify:
        classifier = ErrorClassifier()
        
        for i, entry in enumerate(entries, 1):
            error_type = classifier.classify_error(
                entry.message,
                entry.exception or ""
            )
            
            print(f"{i}. [{error_type.value.upper()}] {entry.function_name or 'Unknown'}")
            print(f"   Time: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Message: {entry.message[:100]}...")
            
            # Get suggested fix
            error_report = classifier.create_error_report(
                function_name=entry.function_name or "unknown",
                error_message=entry.message,
                stack_trace=entry.exception or "",
                timestamp=entry.timestamp
            )
            suggested_fix = classifier.get_suggested_fix(error_report)
            print(f"   💡 Suggested fix: {suggested_fix}")
            print()
    else:
        for i, entry in enumerate(entries, 1):
            print(f"{i}. {entry.function_name or 'Unknown'}")
            print(f"   Time: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Message: {entry.message[:100]}...")
            print()


def analyze_function(args):
    """Analyze logs for a specific function."""
    function_name = args.function_name
    minutes = args.minutes or 30
    
    print(f"Analyzing {function_name} logs from last {minutes} minutes...")
    print("=" * 60)
    
    log_access = AzureLogAccess()
    entries = log_access.get_function_logs(function_name, minutes=minutes)
    
    if not entries:
        print(f"No log entries found for {function_name}")
        return
    
    print(f"\nFound {len(entries)} log entries\n")
    
    # Get summary
    parser = LogParser()
    summary = parser.get_error_summary(entries)
    
    print("Summary:")
    print(f"  Total entries: {summary['total_entries']}")
    print(f"  Total errors: {summary['total_errors']}")
    print(f"  Error rate: {summary['error_rate']:.1%}")
    print()
    
    # Show errors by level
    if summary['by_level']:
        print("Errors by level:")
        for level, count in summary['by_level'].items():
            print(f"  {level}: {count}")
        print()
    
    # Classify errors
    error_entries = parser.filter_errors(entries)
    if error_entries:
        print(f"Classifying {len(error_entries)} errors...\n")
        
        classifier = ErrorClassifier()
        error_types = {}
        
        for entry in error_entries:
            error_type = classifier.classify_error(
                entry.message,
                entry.exception or ""
            )
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        print("Errors by type:")
        for error_type, count in error_types.items():
            print(f"  {error_type.value}: {count}")
        print()
        
        # Show first few errors with details
        print("Recent errors (showing first 3):\n")
        for i, entry in enumerate(error_entries[:3], 1):
            error_report = classifier.create_error_report(
                function_name=function_name,
                error_message=entry.message,
                stack_trace=entry.exception or "",
                timestamp=entry.timestamp
            )
            
            print(f"{i}. [{error_report.error_type.value.upper()}]")
            print(f"   Time: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Message: {entry.message[:150]}...")
            
            suggested_fix = classifier.get_suggested_fix(error_report)
            print(f"   💡 Suggested fix: {suggested_fix}")
            print()


def classify_error_file(args):
    """Classify errors from a log file."""
    log_file = args.log_file
    
    print(f"Classifying errors from {log_file}...")
    print("=" * 60)
    
    try:
        with open(log_file, 'r') as f:
            log_text = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {log_file}")
        return
    
    parser = LogParser()
    entries = parser.parse_log_stream(log_text)
    
    if not entries:
        print("No log entries found in file")
        return
    
    print(f"Parsed {len(entries)} log entries\n")
    
    error_entries = parser.filter_errors(entries)
    if not error_entries:
        print("No errors found in log file")
        return
    
    print(f"Found {len(error_entries)} errors\n")
    
    classifier = ErrorClassifier()
    
    for i, entry in enumerate(error_entries, 1):
        error_report = classifier.create_error_report(
            function_name=entry.function_name or "unknown",
            error_message=entry.message,
            stack_trace=entry.exception or "",
            timestamp=entry.timestamp
        )
        
        print(f"{i}. {error_report.get_summary()}")
        print()
        
        suggested_fix = classifier.get_suggested_fix(error_report)
        print(f"   💡 Suggested fix: {suggested_fix}")
        print()


def start_session(args):
    """Start a new diagnostic session."""
    session_id = args.session_id
    
    print(f"Starting diagnostic session: {session_id}")
    print("=" * 60)
    
    session = DiagnosticSession(
        session_id=session_id,
        start_time=datetime.utcnow()
    )
    
    # Save session
    output_dir = Path("diagnostic_sessions")
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / f"{session_id}.json"
    session.export_to_json(str(json_file))
    
    print(f"✅ Session created: {json_file}")
    print()
    print("Next steps:")
    print("1. Run: python diagnostic_tool.py get-errors --classify")
    print("2. Identify error types and apply fixes")
    print("3. Test functions and record results")
    print("4. Complete session with summary report")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Azure Functions Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # check-access command
    subparsers.add_parser(
        'check-access',
        help='Check Azure CLI access and print instructions'
    )
    
    # tail-logs command
    tail_parser = subparsers.add_parser(
        'tail-logs',
        help='Tail function app logs in real-time'
    )
    tail_parser.add_argument(
        'timeout',
        type=int,
        nargs='?',
        default=30,
        help='Timeout in seconds (default: 30)'
    )
    
    # get-errors command
    errors_parser = subparsers.add_parser(
        'get-errors',
        help='Get recent errors from Application Insights'
    )
    errors_parser.add_argument(
        'minutes',
        type=int,
        nargs='?',
        default=30,
        help='Minutes to look back (default: 30)'
    )
    errors_parser.add_argument(
        '--classify',
        action='store_true',
        help='Classify errors and suggest fixes'
    )
    
    # analyze-function command
    analyze_parser = subparsers.add_parser(
        'analyze-function',
        help='Analyze logs for a specific function'
    )
    analyze_parser.add_argument(
        'function_name',
        help='Name of the function to analyze'
    )
    analyze_parser.add_argument(
        'minutes',
        type=int,
        nargs='?',
        default=30,
        help='Minutes to look back (default: 30)'
    )
    
    # classify-error command
    classify_parser = subparsers.add_parser(
        'classify-error',
        help='Classify errors from a log file'
    )
    classify_parser.add_argument(
        'log_file',
        help='Path to log file'
    )
    
    # start-session command
    session_parser = subparsers.add_parser(
        'start-session',
        help='Start a new diagnostic session'
    )
    session_parser.add_argument(
        'session_id',
        help='Unique session identifier'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    commands = {
        'check-access': check_access,
        'tail-logs': tail_logs,
        'get-errors': get_errors,
        'analyze-function': analyze_function,
        'classify-error': classify_error_file,
        'start-session': start_session
    }
    
    command_func = commands.get(args.command)
    if command_func:
        command_func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
