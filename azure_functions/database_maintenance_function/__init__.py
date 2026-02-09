"""
Azure Function for database maintenance and optimization operations.
Provides HTTP endpoints for manual and scheduled maintenance tasks.
"""

import azure.functions as func
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database_handler import DatabaseHandler, create_database_handler
from shared.database_optimization import DatabaseOptimizer
from shared.database_maintenance_scheduler import (
    DatabaseMaintenanceScheduler, 
    create_maintenance_scheduler
)
from shared.models import DatabaseConfig
from shared.config import config_manager


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function for database maintenance operations.
    
    Supported operations:
    - health_check: Check database health status
    - run_maintenance: Run comprehensive maintenance
    - analyze_indexes: Analyze index usage and fragmentation
    - rebuild_indexes: Rebuild fragmented indexes
    - update_statistics: Update table statistics
    - cleanup_logs: Clean up old execution logs
    - create_indexes: Create missing performance indexes
    - performance_report: Generate performance report
    - scheduled_maintenance: Run scheduled maintenance tasks
    """
    logging.info('Database maintenance function triggered')
    
    try:
        # Get operation from query parameters or request body
        operation = req.params.get('operation')
        
        if not operation:
            try:
                req_body = req.get_json()
                operation = req_body.get('operation')
            except ValueError:
                pass
        
        if not operation:
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing 'operation' parameter",
                    "supported_operations": [
                        "health_check",
                        "run_maintenance",
                        "analyze_indexes",
                        "rebuild_indexes",
                        "update_statistics",
                        "cleanup_logs",
                        "create_indexes",
                        "performance_report",
                        "scheduled_maintenance"
                    ]
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Initialize database handler
        db_config = await config_manager.get_database_config()
        db_handler = await create_database_handler(db_config)
        
        # Execute requested operation
        if operation == "health_check":
            result = await handle_health_check(db_handler)
        
        elif operation == "run_maintenance":
            result = await handle_run_maintenance(db_handler, req)
        
        elif operation == "analyze_indexes":
            result = await handle_analyze_indexes(db_handler)
        
        elif operation == "rebuild_indexes":
            result = await handle_rebuild_indexes(db_handler, req)
        
        elif operation == "update_statistics":
            result = await handle_update_statistics(db_handler, req)
        
        elif operation == "cleanup_logs":
            result = await handle_cleanup_logs(db_handler, req)
        
        elif operation == "create_indexes":
            result = await handle_create_indexes(db_handler)
        
        elif operation == "performance_report":
            result = await handle_performance_report(db_handler)
        
        elif operation == "scheduled_maintenance":
            result = await handle_scheduled_maintenance(db_handler)
        
        else:
            return func.HttpResponse(
                json.dumps({
                    "error": f"Unknown operation: {operation}",
                    "supported_operations": [
                        "health_check",
                        "run_maintenance",
                        "analyze_indexes",
                        "rebuild_indexes",
                        "update_statistics",
                        "cleanup_logs",
                        "create_indexes",
                        "performance_report",
                        "scheduled_maintenance"
                    ]
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Close database handler
        await db_handler.close()
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Database maintenance function failed: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


async def handle_health_check(db_handler: DatabaseHandler) -> Dict[str, Any]:
    """Handle health check operation."""
    logging.info("Executing health check")
    
    scheduler = create_maintenance_scheduler(db_handler)
    health_status = await scheduler.run_health_check()
    
    return {
        "operation": "health_check",
        "timestamp": datetime.utcnow().isoformat(),
        "result": health_status
    }


async def handle_run_maintenance(db_handler: DatabaseHandler, req: func.HttpRequest) -> Dict[str, Any]:
    """Handle comprehensive maintenance operation."""
    logging.info("Executing comprehensive maintenance")
    
    # Get parameters from request
    try:
        req_body = req.get_json()
    except ValueError:
        req_body = {}
    
    rebuild_indexes = req_body.get('rebuild_indexes', True)
    update_statistics = req_body.get('update_statistics', True)
    cleanup_logs = req_body.get('cleanup_logs', True)
    create_indexes = req_body.get('create_indexes', True)
    retention_days = req_body.get('retention_days', 30)
    
    optimizer = DatabaseOptimizer(db_handler)
    results = await optimizer.run_comprehensive_maintenance(
        rebuild_indexes=rebuild_indexes,
        update_statistics=update_statistics,
        cleanup_logs=cleanup_logs,
        create_indexes=create_indexes,
        retention_days=retention_days
    )
    
    return {
        "operation": "run_maintenance",
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": {
            "rebuild_indexes": rebuild_indexes,
            "update_statistics": update_statistics,
            "cleanup_logs": cleanup_logs,
            "create_indexes": create_indexes,
            "retention_days": retention_days
        },
        "results": [
            {
                "operation_type": r.operation_type.value,
                "success": r.success,
                "duration_seconds": r.duration_seconds,
                "message": r.message,
                "affected_objects": r.affected_objects,
                "performance_improvement": r.performance_improvement
            }
            for r in results
        ]
    }


async def handle_analyze_indexes(db_handler: DatabaseHandler) -> Dict[str, Any]:
    """Handle index analysis operation."""
    logging.info("Analyzing indexes")
    
    optimizer = DatabaseOptimizer(db_handler)
    indexes = await optimizer.analyze_index_usage()
    
    return {
        "operation": "analyze_indexes",
        "timestamp": datetime.utcnow().isoformat(),
        "total_indexes": len(indexes),
        "indexes": [
            {
                "table_name": idx.table_name,
                "index_name": idx.index_name,
                "columns": idx.column_names,
                "index_type": idx.index_type.value,
                "fragmentation_percent": idx.fragmentation_percent,
                "size_mb": idx.size_mb,
                "page_count": idx.page_count
            }
            for idx in indexes
        ]
    }


async def handle_rebuild_indexes(db_handler: DatabaseHandler, req: func.HttpRequest) -> Dict[str, Any]:
    """Handle index rebuild operation."""
    logging.info("Rebuilding indexes")
    
    # Get parameters from request
    try:
        req_body = req.get_json()
    except ValueError:
        req_body = {}
    
    fragmentation_threshold = req_body.get('fragmentation_threshold', 30.0)
    
    optimizer = DatabaseOptimizer(db_handler)
    result = await optimizer.rebuild_fragmented_indexes(fragmentation_threshold)
    
    return {
        "operation": "rebuild_indexes",
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": {
            "fragmentation_threshold": fragmentation_threshold
        },
        "result": {
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "message": result.message,
            "affected_objects": result.affected_objects,
            "performance_improvement": result.performance_improvement
        }
    }


async def handle_update_statistics(db_handler: DatabaseHandler, req: func.HttpRequest) -> Dict[str, Any]:
    """Handle statistics update operation."""
    logging.info("Updating statistics")
    
    # Get parameters from request
    try:
        req_body = req.get_json()
    except ValueError:
        req_body = {}
    
    table_names = req_body.get('table_names')
    
    optimizer = DatabaseOptimizer(db_handler)
    result = await optimizer.update_table_statistics(table_names)
    
    return {
        "operation": "update_statistics",
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": {
            "table_names": table_names
        },
        "result": {
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "message": result.message,
            "affected_objects": result.affected_objects,
            "performance_improvement": result.performance_improvement
        }
    }


async def handle_cleanup_logs(db_handler: DatabaseHandler, req: func.HttpRequest) -> Dict[str, Any]:
    """Handle log cleanup operation."""
    logging.info("Cleaning up logs")
    
    # Get parameters from request
    try:
        req_body = req.get_json()
    except ValueError:
        req_body = {}
    
    retention_days = req_body.get('retention_days', 30)
    
    optimizer = DatabaseOptimizer(db_handler)
    result = await optimizer.cleanup_old_logs(retention_days)
    
    return {
        "operation": "cleanup_logs",
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": {
            "retention_days": retention_days
        },
        "result": {
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "message": result.message,
            "affected_objects": result.affected_objects,
            "performance_improvement": result.performance_improvement
        }
    }


async def handle_create_indexes(db_handler: DatabaseHandler) -> Dict[str, Any]:
    """Handle index creation operation."""
    logging.info("Creating missing indexes")
    
    optimizer = DatabaseOptimizer(db_handler)
    result = await optimizer.create_missing_indexes()
    
    return {
        "operation": "create_indexes",
        "timestamp": datetime.utcnow().isoformat(),
        "result": {
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "message": result.message,
            "affected_objects": result.affected_objects,
            "performance_improvement": result.performance_improvement
        }
    }


async def handle_performance_report(db_handler: DatabaseHandler) -> Dict[str, Any]:
    """Handle performance report generation."""
    logging.info("Generating performance report")
    
    optimizer = DatabaseOptimizer(db_handler)
    report = await optimizer.generate_performance_report()
    
    return {
        "operation": "performance_report",
        "timestamp": datetime.utcnow().isoformat(),
        "report": report
    }


async def handle_scheduled_maintenance(db_handler: DatabaseHandler) -> Dict[str, Any]:
    """Handle scheduled maintenance execution."""
    logging.info("Running scheduled maintenance")
    
    scheduler = create_maintenance_scheduler(db_handler)
    results = await scheduler.run_scheduled_maintenance()
    
    return {
        "operation": "scheduled_maintenance",
        "timestamp": datetime.utcnow().isoformat(),
        "results": [
            {
                "operation_type": r.operation_type.value,
                "success": r.success,
                "duration_seconds": r.duration_seconds,
                "message": r.message,
                "affected_objects": r.affected_objects,
                "performance_improvement": r.performance_improvement
            }
            for r in results
        ]
    }
