"""
Azure log access utilities.

Provides methods to:
- Access Azure Portal log stream
- Query Application Insights
- Download historical logs
"""

import subprocess
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from .log_parser import LogParser, LogEntry


class AzureLogAccess:
    """
    Provides access to Azure Function logs.
    
    Validates: Requirements 1.1, 1.3
    """
    
    def __init__(
        self,
        function_app_name: str = "pei-dashboard",
        resource_group: str = "PeiDashboard",
        appinsights_name: Optional[str] = None
    ):
        """
        Initialize Azure log access.
        
        Args:
            function_app_name: Name of the Function App
            resource_group: Name of the resource group
            appinsights_name: Name of Application Insights (defaults to function_app_name)
        """
        self.function_app_name = function_app_name
        self.resource_group = resource_group
        self.appinsights_name = appinsights_name or function_app_name
        self.log_parser = LogParser()
    
    def tail_logs(self, timeout_seconds: int = 30) -> List[LogEntry]:
        """
        Tail the function app logs in real-time.
        
        Args:
            timeout_seconds: How long to capture logs
            
        Returns:
            List of parsed log entries
        """
        try:
            cmd = [
                "az", "functionapp", "log", "tail",
                "--name", self.function_app_name,
                "--resource-group", self.resource_group,
                "--timeout", str(timeout_seconds)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 5
            )
            
            if result.returncode == 0:
                return self.log_parser.parse_log_stream(result.stdout)
            else:
                print(f"Error tailing logs: {result.stderr}")
                return []
        
        except subprocess.TimeoutExpired:
            print(f"Log tail timed out after {timeout_seconds} seconds")
            return []
        except FileNotFoundError:
            print("Azure CLI not found. Please install Azure CLI.")
            return []
        except Exception as e:
            print(f"Error accessing logs: {e}")
            return []
    
    def query_application_insights(
        self,
        query: str,
        timespan: Optional[str] = None
    ) -> List[LogEntry]:
        """
        Query Application Insights using Kusto query language.
        
        Args:
            query: Kusto query string
            timespan: Time span for the query (e.g., "PT30M" for last 30 minutes)
            
        Returns:
            List of parsed log entries
        """
        try:
            cmd = [
                "az", "monitor", "app-insights", "query",
                "--app", self.appinsights_name,
                "--resource-group", self.resource_group,
                "--analytics-query", query
            ]
            
            if timespan:
                cmd.extend(["--timespan", timespan])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return self.log_parser.parse_application_insights_json(result.stdout)
            else:
                print(f"Error querying Application Insights: {result.stderr}")
                return []
        
        except subprocess.TimeoutExpired:
            print("Application Insights query timed out")
            return []
        except FileNotFoundError:
            print("Azure CLI not found. Please install Azure CLI.")
            return []
        except Exception as e:
            print(f"Error querying Application Insights: {e}")
            return []
    
    def get_recent_errors(self, minutes: int = 30) -> List[LogEntry]:
        """
        Get recent error logs from Application Insights.
        
        Args:
            minutes: How many minutes back to search
            
        Returns:
            List of error log entries
        """
        query = f"""
        traces
        | where timestamp > ago({minutes}m)
        | where severityLevel >= 3
        | order by timestamp desc
        | project timestamp, message, severityLevel, operation_Name, operation_Id
        """
        
        entries = self.query_application_insights(query, f"PT{minutes}M")
        return self.log_parser.filter_errors(entries)
    
    def get_function_logs(
        self,
        function_name: str,
        minutes: int = 30
    ) -> List[LogEntry]:
        """
        Get logs for a specific function.
        
        Args:
            function_name: Name of the function
            minutes: How many minutes back to search
            
        Returns:
            List of log entries for the function
        """
        query = f"""
        traces
        | where timestamp > ago({minutes}m)
        | where operation_Name contains "{function_name}"
        | order by timestamp desc
        | project timestamp, message, severityLevel, operation_Name, operation_Id
        """
        
        return self.query_application_insights(query, f"PT{minutes}M")
    
    def get_failed_requests(self, minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Get failed HTTP requests from Application Insights.
        
        Args:
            minutes: How many minutes back to search
            
        Returns:
            List of failed request details
        """
        query = f"""
        requests
        | where timestamp > ago({minutes}m)
        | where success == false
        | order by timestamp desc
        | project timestamp, name, resultCode, duration, operation_Id
        """
        
        try:
            cmd = [
                "az", "monitor", "app-insights", "query",
                "--app", self.appinsights_name,
                "--resource-group", self.resource_group,
                "--analytics-query", query,
                "--timespan", f"PT{minutes}M",
                "--output", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if 'tables' in data and data['tables']:
                    table = data['tables'][0]
                    columns = [col['name'] for col in table['columns']]
                    
                    failed_requests = []
                    for row in table['rows']:
                        request = dict(zip(columns, row))
                        failed_requests.append(request)
                    
                    return failed_requests
            
            return []
        
        except Exception as e:
            print(f"Error getting failed requests: {e}")
            return []
    
    def get_exceptions(self, minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Get exceptions from Application Insights.
        
        Args:
            minutes: How many minutes back to search
            
        Returns:
            List of exception details
        """
        query = f"""
        exceptions
        | where timestamp > ago({minutes}m)
        | order by timestamp desc
        | project timestamp, type, outerMessage, innermostMessage, operation_Name, operation_Id
        """
        
        try:
            cmd = [
                "az", "monitor", "app-insights", "query",
                "--app", self.appinsights_name,
                "--resource-group", self.resource_group,
                "--analytics-query", query,
                "--timespan", f"PT{minutes}M",
                "--output", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if 'tables' in data and data['tables']:
                    table = data['tables'][0]
                    columns = [col['name'] for col in table['columns']]
                    
                    exceptions = []
                    for row in table['rows']:
                        exception = dict(zip(columns, row))
                        exceptions.append(exception)
                    
                    return exceptions
            
            return []
        
        except Exception as e:
            print(f"Error getting exceptions: {e}")
            return []
    
    def check_azure_cli_installed(self) -> bool:
        """
        Check if Azure CLI is installed and accessible.
        
        Returns:
            True if Azure CLI is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["az", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def check_logged_in(self) -> bool:
        """
        Check if user is logged in to Azure CLI.
        
        Returns:
            True if logged in, False otherwise
        """
        try:
            result = subprocess.run(
                ["az", "account", "show"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def get_portal_url(self) -> str:
        """
        Get the Azure Portal URL for the function app log stream.
        
        Returns:
            URL to the log stream in Azure Portal
        """
        return (
            f"https://portal.azure.com/#@/resource/subscriptions/"
            f"{{subscription_id}}/resourceGroups/{self.resource_group}/"
            f"providers/Microsoft.Web/sites/{self.function_app_name}/logStream"
        )
    
    def print_access_instructions(self) -> None:
        """Print instructions for accessing logs."""
        print("\n=== Azure Function Log Access ===\n")
        
        # Check Azure CLI
        if not self.check_azure_cli_installed():
            print("❌ Azure CLI is not installed")
            print("   Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
            print()
        else:
            print("✅ Azure CLI is installed")
            
            if not self.check_logged_in():
                print("❌ Not logged in to Azure CLI")
                print("   Run: az login")
                print()
            else:
                print("✅ Logged in to Azure CLI")
                print()
        
        print("📋 Log Access Methods:\n")
        print("1. Real-time log stream (Azure CLI):")
        print(f"   az functionapp log tail --name {self.function_app_name} --resource-group {self.resource_group}")
        print()
        print("2. Application Insights query (Azure CLI):")
        print(f"   az monitor app-insights query --app {self.appinsights_name} --resource-group {self.resource_group} \\")
        print('     --analytics-query "traces | where timestamp > ago(30m) | order by timestamp desc"')
        print()
        print("3. Azure Portal (Web UI):")
        print(f"   https://portal.azure.com -> {self.function_app_name} -> Log stream")
        print()
