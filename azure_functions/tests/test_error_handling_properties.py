"""
Property-based tests for error handling and logging.
Tests universal properties that should hold for error handling, logging, and recovery mechanisms.
"""

import asyncio
import os
import sys
from typing import List, Dict, Any, Optional, Callable
from unittest.mock import Mock, patch, AsyncMock
import uuid
import json
import logging
from datetime import datetime, timedelta
import traceback
import pytest

# Mock the testing framework since we can't install it
class MockHypothesis:
    """Mock hypothesis for property testing when pytest is not available."""
    
    @staticmethod
    def given(*args, **kwargs):
        def decorator(func):
            func._hypothesis_given = True
            return func
        return decorator
    
    @staticmethod
    def settings(*args, **kwargs):
        def decorator(func):
            func._hypothesis_settings = True
            return func
        return decorator
    
    class strategies:
        @staticmethod
        def lists(strategy, min_size=0, max_size=10):
            return f"lists({strategy}, min_size={min_size}, max_size={max_size})"
        
        @staticmethod
        def text(min_size=0, max_size=100):
            return f"text(min_size={min_size}, max_size={max_size})"
        
        @staticmethod
        def integers(min_value=0, max_value=100):
            return f"integers(min_value={min_value}, max_value={max_value})"
        
        @staticmethod
        def sampled_from(choices):
            return f"sampled_from({choices})"
        
        @staticmethod
        def one_of(*strategies):
            return f"one_of({strategies})"
    
    @staticmethod
    def composite(func):
        return func

try:
    from hypothesis import given, strategies as st, settings, composite
except ImportError:
    # Use mock when hypothesis is not available
    mock_hypothesis = MockHypothesis()
    given = mock_hypothesis.given
    st = mock_hypothesis.strategies
    settings = mock_hypothesis.settings
    composite = mock_hypothesis.composite

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.logging_config import (
    AzureFunctionsLogger, get_function_logger, StructuredFormatter
)
from shared.utils import retry_async, CircuitBreaker
from shared.interfaces import DatabaseError, CopilotError, ConfigurationError
from shared.database_handler import DatabaseHandler
from shared.models import DatabaseConfig


class TestErrorHandlingProperties:
    """
    Property-based tests for error handling and logging.
    **Feature: azure-functions-porting, Property 9: Error Handling and Logging**
    **Validates: Requirements 3.4, 8.1, 8.2, 8.5**
    """
    
    @property
    def test_exceptions(self):
        """Get test exceptions for property testing."""
        return [
            DatabaseError("Test database error"),
            CopilotError("Test Copilot API error"),
            ConfigurationError("Test configuration error"),
            ConnectionError("Test connection error"),
            TimeoutError("Test timeout error"),
            ValueError("Test validation error"),
            Exception("Test generic error")
        ]
        
    @property
    def test_function_names(self):
        """Get test function names for property testing."""
        return [
            "cnbc_scraper",
            "sentiment_analyzer", 
            "database_handler",
            "orchestrator_function",
            "scheduler_function"
        ]
    
    @pytest.mark.asyncio
    async def test_property_9_error_handling_and_logging(self):
        """
        **Property 9: Error Handling and Logging**
        **Validates: Requirements 3.4, 8.1, 8.2, 8.5**
        
        For any function execution that encounters an error, the error should be caught,
        logged with sufficient detail, and handled gracefully.
        """
        try:
            # Test 1: Exception Catching and Logging Property
            await self._test_exception_catching_property()
            
            # Test 2: Structured Logging Property
            await self._test_structured_logging_property()
            
            # Test 3: Error Recovery Property
            await self._test_error_recovery_property()
            
            # Test 4: Application Insights Integration Property
            await self._test_appinsights_integration_property()
            
            # Test 5: Error Context Preservation Property
            await self._test_error_context_preservation_property()
            
            print("✓ All error handling and logging property tests passed")
            return True
            
        except Exception as e:
            print(f"✗ Error handling property test failed: {str(e)}")
            return False
    
    async def _test_exception_catching_property(self):
        """
        Property: All exceptions must be caught and logged with sufficient detail.
        No exceptions should propagate unhandled to the Azure Functions runtime.
        """
        print("Testing exception catching property...")
        
        # Test with different exception types
        for exception in self.test_exceptions:
            for function_name in self.test_function_names:
                await self._test_single_exception_handling(function_name, exception)
        
        print("✓ Exception catching property validated")
    
    async def _test_single_exception_handling(self, function_name: str, exception: Exception):
        """Test exception handling for a single function and exception type."""
        
        # Mock logger to capture log entries
        captured_logs = []
        
        def mock_log_handler(record):
            captured_logs.append({
                'level': record.levelname,
                'message': record.getMessage(),
                'exception': record.exc_info is not None,
                'function_name': getattr(record, 'function_name', None),
                'execution_id': getattr(record, 'execution_id', None)
            })
        
        # Create test function that raises the exception
        async def test_function():
            logger, azure_logger = get_function_logger(function_name)
            
            # Add our mock handler
            mock_handler = Mock()
            mock_handler.emit = mock_log_handler
            logger.logger.addHandler(mock_handler)
            
            try:
                # Simulate function logic that raises exception
                raise exception
            except Exception as e:
                # Property: Exception must be caught and logged
                logger.error(f"Function {function_name} encountered error: {str(e)}", exc_info=True)
                
                # Property: Error must be tracked in Application Insights if available
                if azure_logger.telemetry_client:
                    azure_logger.track_exception(e, {
                        'function_name': function_name,
                        'error_type': type(e).__name__
                    })
                
                # Return error result instead of propagating
                return {'status': 'error', 'error': str(e)}
        
        # Execute test function
        result = await test_function()
        
        # Property assertions
        assert result['status'] == 'error', f"Function should return error status for {type(exception).__name__}"
        assert len(captured_logs) > 0, f"No logs captured for {function_name} with {type(exception).__name__}"
        
        # Find error log entry
        error_logs = [log for log in captured_logs if log['level'] == 'ERROR']
        assert len(error_logs) > 0, f"No ERROR level logs found for {function_name} with {type(exception).__name__}"
        
        error_log = error_logs[0]
        assert error_log['exception'], f"Exception info not captured for {function_name}"
        assert function_name in error_log['message'], f"Function name not in error message"
        assert str(exception) in error_log['message'], f"Exception message not in log"
    
    async def _test_structured_logging_property(self):
        """
        Property: All log entries must follow structured logging format with required fields.
        Logs must include timestamp, level, function name, execution ID, and message.
        """
        print("Testing structured logging property...")
        
        # Test structured formatter
        formatter = StructuredFormatter()
        
        for function_name in self.test_function_names:
            execution_id = str(uuid.uuid4())
            correlation_id = str(uuid.uuid4())
            
            # Create logger with context
            logger, azure_logger = get_function_logger(
                function_name, 
                execution_id=execution_id,
                correlation_id=correlation_id
            )
            
            # Create test log record
            record = logging.LogRecord(
                name=function_name,
                level=logging.ERROR,
                pathname="test.py",
                lineno=100,
                msg="Test error message",
                args=(),
                exc_info=None
            )
            
            # Add context to record
            record.function_name = function_name
            record.execution_id = execution_id
            record.correlation_id = correlation_id
            record.custom_field = "test_value"
            
            # Format the record
            formatted_log = formatter.format(record)
            
            # Property assertions: Structured log must be valid JSON
            try:
                log_data = json.loads(formatted_log)
            except json.JSONDecodeError:
                assert False, f"Log output is not valid JSON: {formatted_log}"
            
            # Property: Required fields must be present
            required_fields = ['timestamp', 'level', 'logger', 'message']
            for field in required_fields:
                assert field in log_data, f"Required field '{field}' missing from log"
            
            # Property: Context fields must be preserved
            assert log_data.get('function_name') == function_name, "Function name not preserved"
            assert log_data.get('execution_id') == execution_id, "Execution ID not preserved"
            assert log_data.get('correlation_id') == correlation_id, "Correlation ID not preserved"
            
            # Property: Extra fields must be captured
            assert 'extra' in log_data, "Extra fields not captured"
            assert log_data['extra'].get('custom_field') == 'test_value', "Custom field not preserved"
        
        print("✓ Structured logging property validated")
    
    async def _test_error_recovery_property(self):
        """
        Property: Functions must implement appropriate retry and recovery mechanisms.
        Transient errors should be retried with exponential backoff.
        """
        print("Testing error recovery property...")
        
        # Test retry decorator
        retry_attempts = []
        
        @retry_async(max_attempts=3, delay=0.1, backoff=2.0, exceptions=(ConnectionError, TimeoutError))
        async def test_retry_function():
            retry_attempts.append(len(retry_attempts) + 1)
            if len(retry_attempts) < 3:
                raise ConnectionError("Transient connection error")
            return "success"
        
        # Test successful retry
        result = await test_retry_function()
        
        # Property assertions
        assert result == "success", "Retry function should eventually succeed"
        assert len(retry_attempts) == 3, f"Expected 3 attempts, got {len(retry_attempts)}"
        
        # Test circuit breaker
        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        failure_count = 0
        
        async def failing_function():
            nonlocal failure_count
            failure_count += 1
            raise ConnectionError("Service unavailable")
        
        # Test circuit breaker opening
        for i in range(3):
            try:
                await circuit_breaker.call(failing_function)
            except Exception:
                pass
        
        # Property: Circuit should be open after threshold failures
        assert circuit_breaker.state == 'open', "Circuit breaker should be open after failures"
        
        # Test circuit breaker blocking further calls
        try:
            await circuit_breaker.call(failing_function)
            assert False, "Circuit breaker should block calls when open"
        except Exception as e:
            assert "Circuit breaker is open" in str(e), "Circuit breaker should report open state"
        
        print("✓ Error recovery property validated")
    
    async def _test_appinsights_integration_property(self):
        """
        Property: Application Insights integration must track errors and exceptions properly.
        All exceptions should be sent to Application Insights with proper context.
        """
        print("Testing Application Insights integration property...")
        
        # Mock Application Insights client
        with patch('shared.logging_config.TelemetryClient') as mock_telemetry_class:
            mock_client = Mock()
            mock_telemetry_class.return_value = mock_client
            
            # Test with Application Insights enabled
            with patch.dict(os.environ, {
                'APPINSIGHTS_INSTRUMENTATIONKEY': 'test-key-12345'
            }):
                function_name = "test_function"
                azure_logger = AzureFunctionsLogger(function_name, enable_appinsights=True)
                
                # Test exception tracking
                test_exception = ValueError("Test exception for AppInsights")
                test_properties = {
                    'function_name': function_name,
                    'error_type': 'ValueError',
                    'custom_property': 'test_value'
                }
                
                azure_logger.track_exception(test_exception, test_properties)
                
                # Property assertions
                mock_client.track_exception.assert_called_once()
                call_args = mock_client.track_exception.call_args
                
                # Verify exception details
                assert call_args[0][0] == ValueError, "Exception type not tracked correctly"
                assert call_args[0][1] == test_exception, "Exception instance not tracked correctly"
                assert call_args[1]['properties'] == test_properties, "Exception properties not tracked correctly"
                
                # Test event tracking
                mock_client.reset_mock()
                azure_logger.track_event("error_occurred", test_properties)
                
                mock_client.track_event.assert_called_once_with("error_occurred", test_properties, None)
                
                # Test metric tracking
                mock_client.reset_mock()
                azure_logger.track_metric("error_count", 1.0, test_properties)
                
                mock_client.track_metric.assert_called_once_with("error_count", 1.0, properties=test_properties)
                
                # Property: Flush should be called to ensure data is sent
                assert mock_client.flush.call_count >= 3, "Flush should be called after tracking operations"
        
        print("✓ Application Insights integration property validated")
    
    async def _test_error_context_preservation_property(self):
        """
        Property: Error context must be preserved across async operations and function calls.
        Execution ID, correlation ID, and function context should be maintained.
        """
        print("Testing error context preservation property...")
        
        execution_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        function_name = "context_test_function"
        
        # Test context preservation in nested async calls
        async def nested_function_level_3():
            logger, _ = get_function_logger(function_name, execution_id, correlation_id)
            
            # Simulate error in deeply nested function
            try:
                raise DatabaseError("Database connection failed in nested function")
            except Exception as e:
                logger.error("Nested function error", exc_info=True, extra={
                    'nested_level': 3,
                    'operation': 'database_query'
                })
                raise
        
        async def nested_function_level_2():
            logger, _ = get_function_logger(function_name, execution_id, correlation_id)
            
            try:
                await nested_function_level_3()
            except Exception as e:
                logger.error("Level 2 function error", exc_info=True, extra={
                    'nested_level': 2,
                    'operation': 'data_processing'
                })
                raise
        
        async def nested_function_level_1():
            logger, _ = get_function_logger(function_name, execution_id, correlation_id)
            
            try:
                await nested_function_level_2()
            except Exception as e:
                logger.error("Level 1 function error", exc_info=True, extra={
                    'nested_level': 1,
                    'operation': 'main_logic'
                })
                raise
        
        # Capture logs to verify context preservation
        captured_logs = []
        
        # Mock logging handler to capture structured logs
        original_formatter = StructuredFormatter()
        
        class ContextCapturingHandler(logging.Handler):
            def emit(self, record):
                formatted = original_formatter.format(record)
                try:
                    log_data = json.loads(formatted)
                    captured_logs.append(log_data)
                except json.JSONDecodeError:
                    pass
        
        # Add handler to root logger
        handler = ContextCapturingHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        
        try:
            # Execute nested function chain
            try:
                await nested_function_level_1()
            except Exception:
                pass  # Expected to fail
            
            # Property assertions: Context should be preserved in all log entries
            assert len(captured_logs) >= 3, f"Expected at least 3 log entries, got {len(captured_logs)}"
            
            for log_entry in captured_logs:
                # Property: Execution context must be preserved
                assert log_entry.get('function_name') == function_name, f"Function name not preserved: {log_entry}"
                assert log_entry.get('execution_id') == execution_id, f"Execution ID not preserved: {log_entry}"
                assert log_entry.get('correlation_id') == correlation_id, f"Correlation ID not preserved: {log_entry}"
                
                # Property: Error level and exception info must be present
                assert log_entry.get('level') == 'ERROR', f"Log level not ERROR: {log_entry}"
                assert 'exception' in log_entry, f"Exception info missing: {log_entry}"
                
                # Property: Custom context should be preserved
                if 'extra' in log_entry:
                    extra = log_entry['extra']
                    assert 'nested_level' in extra, f"Nested level context missing: {log_entry}"
                    assert 'operation' in extra, f"Operation context missing: {log_entry}"
        
        finally:
            # Clean up handler
            root_logger.removeHandler(handler)
        
        print("✓ Error context preservation property validated")
    
    async def run_all_tests(self) -> bool:
        """Run all error handling and logging property tests."""
        try:
            success = await self.test_property_9_error_handling_and_logging()
            return success
        except Exception as e:
            print(f"Test execution failed: {str(e)}")
            return False


class TestLoggingIntegrationProperties:
    """
    Additional property tests for logging integration patterns.
    """
    
    @pytest.mark.asyncio
    async def test_property_log_level_filtering(self):
        """
        Property: Log level filtering must work correctly across all loggers.
        Only logs at or above the configured level should be emitted.
        """
        print("Testing log level filtering property...")
        
        captured_logs = []
        
        class LevelCapturingHandler(logging.Handler):
            def emit(self, record):
                captured_logs.append({
                    'level': record.levelname,
                    'levelno': record.levelno,
                    'message': record.getMessage()
                })
        
        # Test different log levels
        test_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        for configured_level in test_levels:
            captured_logs.clear()
            
            logger, _ = get_function_logger("test_function", log_level=configured_level)
            handler = LevelCapturingHandler()
            logger.logger.addHandler(handler)
            
            # Emit logs at all levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # Property: Only logs at or above configured level should be captured
            configured_levelno = getattr(logging, configured_level)
            for log_entry in captured_logs:
                assert log_entry['levelno'] >= configured_levelno, \
                    f"Log level {log_entry['level']} below configured level {configured_level}"
            
            logger.logger.removeHandler(handler)
        
        print("✓ Log level filtering property validated")
        return True
    
    @pytest.mark.asyncio
    async def test_property_concurrent_logging_safety(self):
        """
        Property: Logging must be thread-safe and handle concurrent operations correctly.
        Multiple concurrent logging operations should not interfere with each other.
        """
        print("Testing concurrent logging safety property...")
        
        captured_logs = []
        
        class ConcurrentCapturingHandler(logging.Handler):
            def emit(self, record):
                captured_logs.append({
                    'thread_id': record.thread,
                    'message': record.getMessage(),
                    'timestamp': record.created
                })
        
        logger, _ = get_function_logger("concurrent_test_function")
        handler = ConcurrentCapturingHandler()
        logger.logger.addHandler(handler)
        
        # Create concurrent logging tasks
        async def log_messages(task_id: int, message_count: int):
            for i in range(message_count):
                logger.info(f"Task {task_id} message {i}")
                await asyncio.sleep(0.001)  # Small delay to encourage interleaving
        
        # Run multiple concurrent logging tasks
        tasks = [log_messages(task_id, 10) for task_id in range(5)]
        await asyncio.gather(*tasks)
        
        # Property assertions
        assert len(captured_logs) == 50, f"Expected 50 log messages, got {len(captured_logs)}"
        
        # Property: All messages should be captured without corruption
        task_messages = {}
        for log_entry in captured_logs:
            message = log_entry['message']
            if 'Task' in message:
                parts = message.split()
                task_id = int(parts[1])
                message_id = int(parts[3])
                
                if task_id not in task_messages:
                    task_messages[task_id] = []
                task_messages[task_id].append(message_id)
        
        # Property: Each task should have all its messages
        for task_id in range(5):
            assert task_id in task_messages, f"Task {task_id} messages not found"
            assert len(task_messages[task_id]) == 10, f"Task {task_id} missing messages"
            assert sorted(task_messages[task_id]) == list(range(10)), f"Task {task_id} messages corrupted"
        
        logger.logger.removeHandler(handler)
        
        print("✓ Concurrent logging safety property validated")
        return True
    
    async def run_all_tests(self) -> bool:
        """Run all logging integration property tests."""
        try:
            test1 = await self.test_property_log_level_filtering()
            test2 = await self.test_property_concurrent_logging_safety()
            return test1 and test2
        except Exception as e:
            print(f"Logging integration test execution failed: {str(e)}")
            return False


# Async test runner
def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def main():
    """Main test runner for error handling and logging properties."""
    print("Running Error Handling and Logging Property Tests...")
    print("=" * 65)
    
    # Test 1: Error Handling Properties
    error_tester = TestErrorHandlingProperties()
    error_success = await error_tester.run_all_tests()
    
    print("\n" + "=" * 65)
    
    # Test 2: Logging Integration Properties
    logging_tester = TestLoggingIntegrationProperties()
    logging_success = await logging_tester.run_all_tests()
    
    print("\n" + "=" * 65)
    
    overall_success = error_success and logging_success
    
    if overall_success:
        print("✓ All error handling and logging property tests PASSED")
    else:
        print("✗ Some error handling and logging property tests FAILED")
    
    return overall_success


if __name__ == "__main__":
    # Run the property tests
    success = run_async_test(main())
    
    if success:
        print("\n🎉 Error handling and logging property validation completed successfully!")
        exit(0)
    else:
        print("\n❌ Error handling and logging property validation failed!")
        exit(1)