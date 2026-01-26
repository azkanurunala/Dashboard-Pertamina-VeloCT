"""
Database maintenance scheduler for automated performance optimization.
Provides scheduled maintenance operations and health monitoring.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .database_handler import DatabaseHandler
from .database_optimization import DatabaseOptimizer, MaintenanceResult, MaintenanceType
from .interfaces import DatabaseError
from .logging_config import get_logger


class MaintenanceSchedule(Enum):
    """Maintenance operation schedules."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


@dataclass
class MaintenanceTask:
    """Configuration for a maintenance task."""
    name: str
    operation_type: MaintenanceType
    schedule: MaintenanceSchedule
    enabled: bool
    parameters: Dict[str, Any]
    last_run: Optional[datetime]
    next_run: Optional[datetime]


@dataclass
class MaintenanceScheduleConfig:
    """Configuration for maintenance scheduling."""
    daily_time: str  # HH:MM format
    weekly_day: int  # 0=Monday, 6=Sunday
    monthly_day: int  # Day of month (1-28)
    timezone: str
    max_duration_minutes: int
    enable_online_operations: bool


class DatabaseMaintenanceScheduler:
    """
    Automated database maintenance scheduler.
    Manages scheduled maintenance operations and health monitoring.
    """
    
    def __init__(self, db_handler: DatabaseHandler, config: MaintenanceScheduleConfig):
        """
        Initialize the maintenance scheduler.
        
        Args:
            db_handler: Database handler instance
            config: Maintenance schedule configuration
        """
        self.db_handler = db_handler
        self.config = config
        self.optimizer = DatabaseOptimizer(db_handler)
        self.logger = get_logger(__name__)
        
        # Default maintenance tasks
        self.tasks = self._initialize_default_tasks()
    
    def _initialize_default_tasks(self) -> List[MaintenanceTask]:
        """Initialize default maintenance tasks."""
        return [
            MaintenanceTask(
                name="daily_log_cleanup",
                operation_type=MaintenanceType.CLEANUP_LOGS,
                schedule=MaintenanceSchedule.DAILY,
                enabled=True,
                parameters={"retention_days": 30},
                last_run=None,
                next_run=None
            ),
            MaintenanceTask(
                name="weekly_statistics_update",
                operation_type=MaintenanceType.UPDATE_STATISTICS,
                schedule=MaintenanceSchedule.WEEKLY,
                enabled=True,
                parameters={"table_names": None},
                last_run=None,
                next_run=None
            ),
            MaintenanceTask(
                name="weekly_index_rebuild",
                operation_type=MaintenanceType.REBUILD_INDEXES,
                schedule=MaintenanceSchedule.WEEKLY,
                enabled=True,
                parameters={"fragmentation_threshold": 30.0},
                last_run=None,
                next_run=None
            ),
            MaintenanceTask(
                name="monthly_optimization",
                operation_type=MaintenanceType.OPTIMIZE_QUERIES,
                schedule=MaintenanceSchedule.MONTHLY,
                enabled=True,
                parameters={},
                last_run=None,
                next_run=None
            )
        ]
    
    async def run_scheduled_maintenance(self) -> List[MaintenanceResult]:
        """
        Run all scheduled maintenance tasks that are due.
        
        Returns:
            List of maintenance results
        """
        results = []
        current_time = datetime.utcnow()
        
        self.logger.info("Starting scheduled maintenance check")
        
        try:
            # Update next run times for all tasks
            self._update_next_run_times()
            
            # Find tasks that are due
            due_tasks = [
                task for task in self.tasks 
                if task.enabled and task.next_run and task.next_run <= current_time
            ]
            
            if not due_tasks:
                self.logger.info("No maintenance tasks are due")
                return results
            
            self.logger.info(f"Found {len(due_tasks)} maintenance tasks due for execution")
            
            # Execute due tasks
            for task in due_tasks:
                try:
                    self.logger.info(f"Executing maintenance task: {task.name}")
                    result = await self._execute_maintenance_task(task)
                    results.append(result)
                    
                    # Update last run time
                    task.last_run = current_time
                    
                except Exception as e:
                    self.logger.error(f"Failed to execute maintenance task {task.name}: {str(e)}")
                    
                    # Create error result
                    error_result = MaintenanceResult(
                        operation_type=task.operation_type,
                        start_time=current_time,
                        end_time=datetime.utcnow(),
                        duration_seconds=0.0,
                        success=False,
                        message=f"Task execution failed: {str(e)}",
                        affected_objects=[],
                        performance_improvement=None
                    )
                    results.append(error_result)
            
            # Log maintenance summary
            successful_tasks = sum(1 for r in results if r.success)
            self.logger.info(
                f"Scheduled maintenance completed: {successful_tasks}/{len(results)} tasks successful"
            )
            
        except Exception as e:
            self.logger.error(f"Scheduled maintenance failed: {str(e)}")
            raise DatabaseError(f"Maintenance scheduling failed: {str(e)}")
        
        return results
    
    async def _execute_maintenance_task(self, task: MaintenanceTask) -> MaintenanceResult:
        """Execute a specific maintenance task."""
        if task.operation_type == MaintenanceType.CLEANUP_LOGS:
            return await self.optimizer.cleanup_old_logs(
                retention_days=task.parameters.get("retention_days", 30)
            )
        
        elif task.operation_type == MaintenanceType.UPDATE_STATISTICS:
            return await self.optimizer.update_table_statistics(
                table_names=task.parameters.get("table_names")
            )
        
        elif task.operation_type == MaintenanceType.REBUILD_INDEXES:
            return await self.optimizer.rebuild_fragmented_indexes(
                fragmentation_threshold=task.parameters.get("fragmentation_threshold", 30.0)
            )
        
        elif task.operation_type == MaintenanceType.OPTIMIZE_QUERIES:
            return await self.optimizer.create_missing_indexes()
        
        else:
            raise DatabaseError(f"Unknown maintenance operation type: {task.operation_type}")
    
    def _update_next_run_times(self) -> None:
        """Update next run times for all tasks based on their schedules."""
        current_time = datetime.utcnow()
        
        for task in self.tasks:
            if not task.enabled:
                continue
            
            if task.next_run is None or task.next_run <= current_time:
                task.next_run = self._calculate_next_run_time(task, current_time)
    
    def _calculate_next_run_time(self, task: MaintenanceTask, current_time: datetime) -> datetime:
        """Calculate the next run time for a task."""
        if task.schedule == MaintenanceSchedule.DAILY:
            # Parse daily time (HH:MM)
            hour, minute = map(int, self.config.daily_time.split(':'))
            next_run = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if next_run <= current_time:
                next_run += timedelta(days=1)
            
            return next_run
        
        elif task.schedule == MaintenanceSchedule.WEEKLY:
            # Calculate next occurrence of the specified weekday
            days_ahead = self.config.weekly_day - current_time.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            hour, minute = map(int, self.config.daily_time.split(':'))
            next_run = current_time + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return next_run
        
        elif task.schedule == MaintenanceSchedule.MONTHLY:
            # Calculate next occurrence of the specified day of month
            next_month = current_time.month + 1
            next_year = current_time.year
            
            if next_month > 12:
                next_month = 1
                next_year += 1
            
            # Ensure day exists in the target month
            import calendar
            max_day = calendar.monthrange(next_year, next_month)[1]
            target_day = min(self.config.monthly_day, max_day)
            
            hour, minute = map(int, self.config.daily_time.split(':'))
            next_run = datetime(next_year, next_month, target_day, hour, minute)
            
            return next_run
        
        else:
            # For on-demand tasks, don't schedule automatically
            return current_time + timedelta(days=365)  # Far future
    
    async def run_comprehensive_maintenance(self) -> List[MaintenanceResult]:
        """
        Run comprehensive maintenance regardless of schedule.
        
        Returns:
            List of maintenance results
        """
        self.logger.info("Starting comprehensive database maintenance")
        
        return await self.optimizer.run_comprehensive_maintenance(
            rebuild_indexes=True,
            update_statistics=True,
            cleanup_logs=True,
            create_indexes=True,
            retention_days=30
        )
    
    async def run_health_check(self) -> Dict[str, Any]:
        """
        Run database health check and return status.
        
        Returns:
            Health check results
        """
        try:
            # Basic connectivity check
            is_healthy = await self.db_handler.health_check()
            
            if not is_healthy:
                return {
                    "status": "CRITICAL",
                    "message": "Database connectivity failed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {}
                }
            
            # Run comprehensive health analysis
            health_query = "EXEC sp_DatabaseHealthCheck"
            health_results = await self.db_handler.execute_query(health_query)
            
            # Generate performance report
            performance_report = await self.optimizer.generate_performance_report()
            
            # Determine overall health status
            if health_results:
                health_info = health_results[0]
                health_score = health_info.get('health_score', 0)
                health_status = health_info.get('health_status', 'UNKNOWN')
                critical_issues = health_info.get('critical_issues', 0)
                warning_issues = health_info.get('warning_issues', 0)
            else:
                health_score = 50
                health_status = 'UNKNOWN'
                critical_issues = 0
                warning_issues = 0
            
            return {
                "status": health_status,
                "score": health_score,
                "critical_issues": critical_issues,
                "warning_issues": warning_issues,
                "timestamp": datetime.utcnow().isoformat(),
                "performance_report": performance_report,
                "next_maintenance": self._get_next_maintenance_schedule()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "ERROR",
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {}
            }
    
    def _get_next_maintenance_schedule(self) -> Dict[str, Any]:
        """Get information about next scheduled maintenance."""
        self._update_next_run_times()
        
        next_tasks = []
        for task in self.tasks:
            if task.enabled and task.next_run:
                next_tasks.append({
                    "task_name": task.name,
                    "operation_type": task.operation_type.value,
                    "schedule": task.schedule.value,
                    "next_run": task.next_run.isoformat(),
                    "last_run": task.last_run.isoformat() if task.last_run else None
                })
        
        # Sort by next run time
        next_tasks.sort(key=lambda x: x["next_run"])
        
        return {
            "next_task": next_tasks[0] if next_tasks else None,
            "all_scheduled_tasks": next_tasks
        }
    
    async def execute_stored_procedure_maintenance(self, procedure_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a stored procedure for maintenance operations.
        
        Args:
            procedure_name: Name of the stored procedure
            parameters: Optional parameters for the procedure
            
        Returns:
            Procedure execution results
        """
        try:
            # Build procedure call
            if parameters:
                param_list = []
                for key, value in parameters.items():
                    if isinstance(value, str):
                        param_list.append(f"@{key} = '{value}'")
                    elif isinstance(value, bool):
                        param_list.append(f"@{key} = {1 if value else 0}")
                    else:
                        param_list.append(f"@{key} = {value}")
                
                query = f"EXEC {procedure_name} {', '.join(param_list)}"
            else:
                query = f"EXEC {procedure_name}"
            
            self.logger.info(f"Executing stored procedure: {procedure_name}")
            
            start_time = datetime.utcnow()
            results = await self.db_handler.execute_query(query)
            end_time = datetime.utcnow()
            
            duration = (end_time - start_time).total_seconds()
            
            return {
                "procedure": procedure_name,
                "success": True,
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Stored procedure execution failed: {str(e)}")
            return {
                "procedure": procedure_name,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def add_custom_task(self, task: MaintenanceTask) -> None:
        """Add a custom maintenance task."""
        self.tasks.append(task)
        self.logger.info(f"Added custom maintenance task: {task.name}")
    
    def remove_task(self, task_name: str) -> bool:
        """Remove a maintenance task by name."""
        original_count = len(self.tasks)
        self.tasks = [task for task in self.tasks if task.name != task_name]
        
        removed = len(self.tasks) < original_count
        if removed:
            self.logger.info(f"Removed maintenance task: {task_name}")
        
        return removed
    
    def enable_task(self, task_name: str) -> bool:
        """Enable a maintenance task."""
        for task in self.tasks:
            if task.name == task_name:
                task.enabled = True
                self.logger.info(f"Enabled maintenance task: {task_name}")
                return True
        return False
    
    def disable_task(self, task_name: str) -> bool:
        """Disable a maintenance task."""
        for task in self.tasks:
            if task.name == task_name:
                task.enabled = False
                self.logger.info(f"Disabled maintenance task: {task_name}")
                return True
        return False
    
    def get_task_status(self) -> List[Dict[str, Any]]:
        """Get status of all maintenance tasks."""
        self._update_next_run_times()
        
        return [
            {
                "name": task.name,
                "operation_type": task.operation_type.value,
                "schedule": task.schedule.value,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "parameters": task.parameters
            }
            for task in self.tasks
        ]


# Factory function for creating maintenance scheduler
def create_maintenance_scheduler(
    db_handler: DatabaseHandler,
    daily_time: str = "02:00",
    weekly_day: int = 6,  # Sunday
    monthly_day: int = 1,
    timezone: str = "UTC",
    max_duration_minutes: int = 60,
    enable_online_operations: bool = True
) -> DatabaseMaintenanceScheduler:
    """
    Factory function to create a maintenance scheduler.
    
    Args:
        db_handler: Database handler instance
        daily_time: Time for daily maintenance (HH:MM format)
        weekly_day: Day of week for weekly maintenance (0=Monday, 6=Sunday)
        monthly_day: Day of month for monthly maintenance (1-28)
        timezone: Timezone for scheduling
        max_duration_minutes: Maximum duration for maintenance operations
        enable_online_operations: Whether to use online index operations
        
    Returns:
        Configured maintenance scheduler
    """
    config = MaintenanceScheduleConfig(
        daily_time=daily_time,
        weekly_day=weekly_day,
        monthly_day=monthly_day,
        timezone=timezone,
        max_duration_minutes=max_duration_minutes,
        enable_online_operations=enable_online_operations
    )
    
    return DatabaseMaintenanceScheduler(db_handler, config)