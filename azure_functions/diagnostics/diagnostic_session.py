"""
Diagnostic session tracking for debugging workflows.

Tracks:
- Errors identified
- Fixes applied
- Test results
- Session summary
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from .error_classifier import ErrorReport


@dataclass
class TestResult:
    """Represents the result of a scraper function test."""
    
    source_name: str
    success: bool
    http_status_code: int
    articles_found: int
    articles_saved: int
    execution_time_seconds: float
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary."""
        return {
            "source_name": self.source_name,
            "success": self.success,
            "http_status_code": self.http_status_code,
            "articles_found": self.articles_found,
            "articles_saved": self.articles_saved,
            "execution_time_seconds": self.execution_time_seconds,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class DiagnosticSession:
    """
    Tracks a complete debugging session.
    
    Validates: Requirements 1.2, 2.1, 8.4
    """
    
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    errors_identified: List[ErrorReport] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETED, FAILED
    notes: List[str] = field(default_factory=list)
    
    def add_error(self, error: ErrorReport) -> None:
        """Add an identified error to the session."""
        self.errors_identified.append(error)
    
    def add_fix(self, fix_description: str) -> None:
        """Add a fix that was applied."""
        self.fixes_applied.append(fix_description)
    
    def add_test_result(self, result: TestResult) -> None:
        """Add a test result to the session."""
        self.test_results.append(result)
    
    def add_note(self, note: str) -> None:
        """Add a note to the session."""
        self.notes.append(f"[{datetime.utcnow().isoformat()}] {note}")
    
    def complete(self) -> None:
        """Mark the session as completed."""
        self.end_time = datetime.utcnow()
        self.status = "COMPLETED"
    
    def fail(self, reason: str) -> None:
        """Mark the session as failed."""
        self.end_time = datetime.utcnow()
        self.status = "FAILED"
        self.add_note(f"Session failed: {reason}")
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get the session duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the diagnostic session.
        
        Returns:
            Dictionary with session statistics
        """
        duration = self.get_duration_seconds()
        
        # Count errors by type
        errors_by_type = {}
        for error in self.errors_identified:
            error_type = error.error_type.value
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1
        
        # Count test results
        tests_passed = sum(1 for r in self.test_results if r.success)
        tests_failed = sum(1 for r in self.test_results if not r.success)
        
        return {
            "session_id": self.session_id,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "errors": {
                "total": len(self.errors_identified),
                "by_type": errors_by_type
            },
            "fixes": {
                "total": len(self.fixes_applied),
                "list": self.fixes_applied
            },
            "tests": {
                "total": len(self.test_results),
                "passed": tests_passed,
                "failed": tests_failed,
                "pass_rate": tests_passed / len(self.test_results) if self.test_results else 0
            }
        }
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        Get a detailed report of the diagnostic session.
        
        Returns:
            Dictionary with complete session data
        """
        return {
            "summary": self.get_summary(),
            "errors": [error.to_dict() for error in self.errors_identified],
            "test_results": [result.to_dict() for result in self.test_results],
            "notes": self.notes
        }
    
    def export_to_json(self, filepath: str) -> None:
        """
        Export the diagnostic session to a JSON file.
        
        Args:
            filepath: Path to save the JSON file
        """
        report = self.get_detailed_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
    
    def export_to_markdown(self, filepath: str) -> None:
        """
        Export the diagnostic session to a Markdown file.
        
        Args:
            filepath: Path to save the Markdown file
        """
        summary = self.get_summary()
        
        lines = [
            f"# Diagnostic Session Report",
            f"",
            f"**Session ID:** {self.session_id}",
            f"**Status:** {self.status}",
            f"**Start Time:** {self.start_time.isoformat()}",
            f"**End Time:** {self.end_time.isoformat() if self.end_time else 'In Progress'}",
            f"**Duration:** {summary['duration_seconds']:.2f} seconds" if summary['duration_seconds'] else "**Duration:** In Progress",
            f"",
            f"## Summary",
            f"",
            f"- **Total Errors Identified:** {summary['errors']['total']}",
            f"- **Total Fixes Applied:** {summary['fixes']['total']}",
            f"- **Total Tests Run:** {summary['tests']['total']}",
            f"- **Tests Passed:** {summary['tests']['passed']}",
            f"- **Tests Failed:** {summary['tests']['failed']}",
            f"- **Pass Rate:** {summary['tests']['pass_rate']:.1%}",
            f"",
            f"## Errors by Type",
            f""
        ]
        
        for error_type, count in summary['errors']['by_type'].items():
            lines.append(f"- **{error_type}:** {count}")
        
        lines.extend([
            f"",
            f"## Fixes Applied",
            f""
        ])
        
        for i, fix in enumerate(self.fixes_applied, 1):
            lines.append(f"{i}. {fix}")
        
        lines.extend([
            f"",
            f"## Test Results",
            f"",
            f"| Source | Status | HTTP | Articles Found | Articles Saved | Time (s) |",
            f"|--------|--------|------|----------------|----------------|----------|"
        ])
        
        for result in self.test_results:
            status = "✅ Pass" if result.success else "❌ Fail"
            lines.append(
                f"| {result.source_name} | {status} | {result.http_status_code} | "
                f"{result.articles_found} | {result.articles_saved} | "
                f"{result.execution_time_seconds:.2f} |"
            )
        
        if self.notes:
            lines.extend([
                f"",
                f"## Notes",
                f""
            ])
            for note in self.notes:
                lines.append(f"- {note}")
        
        lines.extend([
            f"",
            f"## Detailed Errors",
            f""
        ])
        
        for i, error in enumerate(self.errors_identified, 1):
            lines.extend([
                f"### Error {i}: {error.function_name}",
                f"",
                f"- **Type:** {error.error_type.value}",
                f"- **Time:** {error.timestamp.isoformat()}",
                f"- **HTTP Status:** {error.http_status_code}",
                f"- **Message:** {error.error_message[:200]}...",
                f"",
                f"```",
                error.stack_trace[:500] if error.stack_trace else "No stack trace available",
                f"```",
                f""
            ])
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'DiagnosticSession':
        """
        Load a diagnostic session from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            DiagnosticSession instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct the session
        session = cls(
            session_id=data['summary']['session_id'],
            start_time=datetime.fromisoformat(data['summary']['start_time']),
            end_time=datetime.fromisoformat(data['summary']['end_time']) if data['summary']['end_time'] else None,
            status=data['summary']['status']
        )
        
        # Add fixes
        for fix in data['summary']['fixes']['list']:
            session.fixes_applied.append(fix)
        
        # Add notes
        if 'notes' in data:
            session.notes = data['notes']
        
        return session
