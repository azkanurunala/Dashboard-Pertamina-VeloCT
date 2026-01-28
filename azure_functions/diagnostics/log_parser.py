"""
Log parsing utilities for Azure Functions.

Parses log entries from various sources:
- Azure Portal log stream
- Application Insights queries
- Local function execution logs
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import re
import json


@dataclass
class LogEntry:
    """Represents a single log entry."""
    
    timestamp: datetime
    level: str
    message: str
    function_name: Optional[str] = None
    execution_id: Optional[str] = None
    correlation_id: Optional[str] = None
    exception: Optional[str] = None
    raw_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "function_name": self.function_name,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "exception": self.exception,
            "raw_text": self.raw_text
        }
    
    def is_error(self) -> bool:
        """Check if this is an error log entry."""
        return self.level.upper() in ["ERROR", "CRITICAL", "EXCEPTION"]
    
    def is_warning(self) -> bool:
        """Check if this is a warning log entry."""
        return self.level.upper() == "WARNING"


class LogParser:
    """
    Parses Azure Function logs from various sources.
    
    Validates: Requirements 1.2, 1.4
    """
    
    def parse_log_stream(self, log_text: str) -> List[LogEntry]:
        """
        Parse logs from Azure Portal log stream.
        
        Args:
            log_text: Raw log text from log stream
            
        Returns:
            List of parsed log entries
        """
        entries = []
        lines = log_text.split('\n')
        
        current_entry = None
        current_exception_lines = []
        
        for line in lines:
            # Try to parse as new log entry
            entry = self._parse_log_line(line)
            
            if entry:
                # Save previous entry if exists
                if current_entry:
                    if current_exception_lines:
                        current_entry.exception = '\n'.join(current_exception_lines)
                    entries.append(current_entry)
                
                current_entry = entry
                current_exception_lines = []
            
            elif current_entry and line.strip():
                # This is a continuation line (likely stack trace)
                current_exception_lines.append(line)
        
        # Add last entry
        if current_entry:
            if current_exception_lines:
                current_entry.exception = '\n'.join(current_exception_lines)
            entries.append(current_entry)
        
        return entries
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """
        Parse a single log line.
        
        Supports multiple formats:
        - ISO timestamp format: 2024-01-28T10:30:00.123Z [INFO] message
        - Azure format: [2024-01-28 10:30:00] INFO: message
        - Simple format: INFO: message
        """
        if not line.strip():
            return None
        
        # Try ISO timestamp format
        match = re.match(
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+\[?(\w+)\]?\s+(.*)',
            line
        )
        if match:
            timestamp_str, level, message = match.groups()
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message.strip(),
                raw_text=line
            )
        
        # Try Azure format
        match = re.match(
            r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\w+):\s+(.*)',
            line
        )
        if match:
            timestamp_str, level, message = match.groups()
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except:
                timestamp = datetime.utcnow()
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message.strip(),
                raw_text=line
            )
        
        # Try simple format
        match = re.match(r'(\w+):\s+(.*)', line)
        if match:
            level, message = match.groups()
            if level.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                return LogEntry(
                    timestamp=datetime.utcnow(),
                    level=level,
                    message=message.strip(),
                    raw_text=line
                )
        
        return None
    
    def parse_application_insights_json(self, json_data: str) -> List[LogEntry]:
        """
        Parse logs from Application Insights JSON query results.
        
        Args:
            json_data: JSON string from Application Insights query
            
        Returns:
            List of parsed log entries
        """
        try:
            data = json.loads(json_data)
            entries = []
            
            # Handle different JSON structures
            if isinstance(data, dict):
                if 'tables' in data:
                    # Kusto query result format
                    for table in data['tables']:
                        entries.extend(self._parse_kusto_table(table))
                elif 'value' in data:
                    # REST API format
                    for item in data['value']:
                        entry = self._parse_appinsights_item(item)
                        if entry:
                            entries.append(entry)
            elif isinstance(data, list):
                # Direct array of log items
                for item in data:
                    entry = self._parse_appinsights_item(item)
                    if entry:
                        entries.append(entry)
            
            return entries
        
        except json.JSONDecodeError as e:
            # Return empty list if JSON is invalid
            return []
    
    def _parse_kusto_table(self, table: Dict[str, Any]) -> List[LogEntry]:
        """Parse a Kusto query result table."""
        entries = []
        
        if 'columns' not in table or 'rows' not in table:
            return entries
        
        columns = [col['name'] for col in table['columns']]
        
        for row in table['rows']:
            row_dict = dict(zip(columns, row))
            
            timestamp_str = row_dict.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
            
            entry = LogEntry(
                timestamp=timestamp,
                level=row_dict.get('severityLevel', 'INFO'),
                message=row_dict.get('message', ''),
                function_name=row_dict.get('operation_Name'),
                execution_id=row_dict.get('operation_Id'),
                correlation_id=row_dict.get('operation_ParentId')
            )
            entries.append(entry)
        
        return entries
    
    def _parse_appinsights_item(self, item: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a single Application Insights log item."""
        try:
            timestamp_str = item.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
            
            return LogEntry(
                timestamp=timestamp,
                level=item.get('severityLevel', 'INFO'),
                message=item.get('message', ''),
                function_name=item.get('cloud_RoleName'),
                execution_id=item.get('operation_Id'),
                correlation_id=item.get('operation_ParentId')
            )
        except Exception:
            return None
    
    def filter_errors(self, entries: List[LogEntry]) -> List[LogEntry]:
        """
        Filter log entries to only errors and exceptions.
        
        Args:
            entries: List of log entries
            
        Returns:
            List of error entries only
        """
        return [entry for entry in entries if entry.is_error()]
    
    def filter_by_function(self, entries: List[LogEntry], function_name: str) -> List[LogEntry]:
        """
        Filter log entries by function name.
        
        Args:
            entries: List of log entries
            function_name: Function name to filter by
            
        Returns:
            List of entries for the specified function
        """
        return [
            entry for entry in entries
            if entry.function_name and function_name.lower() in entry.function_name.lower()
        ]
    
    def filter_by_time_range(
        self,
        entries: List[LogEntry],
        start_time: datetime,
        end_time: datetime
    ) -> List[LogEntry]:
        """
        Filter log entries by time range.
        
        Args:
            entries: List of log entries
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of entries within the time range
        """
        return [
            entry for entry in entries
            if start_time <= entry.timestamp <= end_time
        ]
    
    def extract_stack_traces(self, entries: List[LogEntry]) -> Dict[str, str]:
        """
        Extract stack traces from error log entries.
        
        Args:
            entries: List of log entries
            
        Returns:
            Dictionary mapping execution_id to stack trace
        """
        stack_traces = {}
        
        for entry in entries:
            if entry.is_error() and entry.exception:
                key = entry.execution_id or f"{entry.function_name}_{entry.timestamp.isoformat()}"
                stack_traces[key] = entry.exception
        
        return stack_traces
    
    def get_error_summary(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """
        Generate a summary of errors from log entries.
        
        Args:
            entries: List of log entries
            
        Returns:
            Dictionary with error statistics
        """
        error_entries = self.filter_errors(entries)
        
        # Count by function
        by_function = {}
        for entry in error_entries:
            func = entry.function_name or "unknown"
            by_function[func] = by_function.get(func, 0) + 1
        
        # Count by level
        by_level = {}
        for entry in error_entries:
            level = entry.level.upper()
            by_level[level] = by_level.get(level, 0) + 1
        
        return {
            "total_errors": len(error_entries),
            "total_entries": len(entries),
            "error_rate": len(error_entries) / len(entries) if entries else 0,
            "by_function": by_function,
            "by_level": by_level,
            "time_range": {
                "start": min(e.timestamp for e in entries).isoformat() if entries else None,
                "end": max(e.timestamp for e in entries).isoformat() if entries else None
            }
        }
