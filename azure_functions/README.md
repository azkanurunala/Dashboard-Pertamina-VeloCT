# Azure Functions News Scraping System

This folder contains the Azure Functions implementation of the news scraping and sentiment analysis system. It provides a complete serverless solution that maintains 100% functional parity with the existing system while upgrading to modern cloud-native technologies.

## Project Structure

```
azure_functions/
├── README.md                    # This file
├── host.json                    # Azure Functions host configuration
├── local.settings.json          # Local development settings
├── requirements.txt             # Python dependencies
├── scrapers/                    # News scraper functions
│   └── __init__.py
├── processing/                  # Data processing and aggregation functions
│   └── __init__.py
├── analysis/                    # Sentiment analysis and summary functions
│   └── __init__.py
├── orchestration/              # Scheduling and workflow orchestration
│   └── __init__.py
└── shared/                     # Shared utilities and common functionality
    ├── __init__.py
    ├── models.py               # Core data models and classes
    ├── interfaces.py           # Abstract interfaces and contracts
    ├── config.py               # Configuration management
    ├── logging_config.py       # Logging and Application Insights setup
    └── utils.py                # Utility functions and helpers
```

## Core Components

### Data Models (`shared/models.py`)
- **NewsArticle**: Represents a news article with metadata
- **SentimentAnalysis**: Represents sentiment analysis results
- **ScrapingConfig**: Configuration for news scrapers
- **CopilotConfig**: Configuration for Microsoft Copilot integration
- **DatabaseConfig**: Configuration for SQL Server database
- **ExecutionResult**: Function execution tracking
- **ArticleFilters**: Database query filters
- **DateRange**: Date range specifications

### Interfaces (`shared/interfaces.py`)
- **INewsScraperFunction**: Contract for news scrapers
- **IDatabaseHandler**: Contract for database operations
- **ICopilotIntegration**: Contract for AI integration
- **ISchedulerFunction**: Contract for scheduled functions
- **IOrchestratorFunction**: Contract for workflow orchestration
- **IConfigurationManager**: Contract for configuration management
- **IDataProcessor**: Contract for data processing

### Configuration Management (`shared/config.py`)
- Environment-based configuration loading
- Source-specific scraper configurations
- Azure services integration settings
- Role-specific prompts for Copilot

### Logging and Monitoring (`shared/logging_config.py`)
- Structured JSON logging
- Application Insights integration
- Custom metrics and event tracking
- Performance monitoring
- Error tracking and alerting

### Utilities (`shared/utils.py`)
- Retry mechanisms with exponential backoff
- Rate limiting decorators
- Circuit breaker pattern
- Data validation and cleaning
- Batch processing helpers

## Technology Stack

- **Runtime**: Python 3.9+
- **Compute**: Azure Functions v4
- **Database**: Microsoft SQL Server (Azure SQL Database)
- **AI/ML**: Microsoft Copilot API
- **Storage**: Azure Blob Storage
- **Security**: Azure Key Vault, Managed Identities
- **Monitoring**: Application Insights, Azure Monitor

## Key Features

### Security and Isolation
- Separate Azure accounts for Copilot, Functions, and SQL Server
- Managed identity authentication
- Secure credential storage in Azure Key Vault
- No hardcoded secrets or connection strings

### Scalability and Performance
- Serverless architecture with automatic scaling
- Connection pooling for database operations
- Rate limiting and circuit breaker patterns
- Batch processing for large data volumes
- Efficient memory usage with streaming operations

### Monitoring and Observability
- Comprehensive logging with structured format
- Application Insights integration
- Custom metrics and performance tracking
- Error tracking and alerting
- Execution tracing and correlation

### Data Management
- SQL Server database with normalized schema
- Automated deduplication based on URL
- Data integrity and referential constraints
- Backup and recovery procedures
- Migration from existing Excel files

## Configuration

### Environment Variables
The system uses environment variables for configuration:

- `SQL_SERVER_CONNECTION_STRING`: Database connection string
- `COPILOT_API_ENDPOINT`: Microsoft Copilot API endpoint
- `AI_API_KEY`: Copilot API authentication key
- `AZURE_KEY_VAULT_URL`: Azure Key Vault URL
- `BLOB_STORAGE_CONNECTION_STRING`: Blob storage connection
- `APPINSIGHTS_INSTRUMENTATIONKEY`: Application Insights key
- `APPLICATIONINSIGHTS_CONNECTION_STRING`: Application Insights connection

### Local Development
1. Copy `local.settings.json.example` to `local.settings.json`
2. Fill in the required configuration values
3. Install dependencies: `pip install -r requirements.txt`
4. Run locally: `func start`

## Deployment

The system uses Infrastructure as Code (IaC) for deployment:

1. **Resource Provisioning**: Bicep/ARM templates create all Azure resources
2. **Function Deployment**: Blue-green deployment with zero downtime
3. **Configuration Management**: Automated secret and setting deployment
4. **Testing**: Automated validation and smoke tests

## Migration Strategy

The system is designed for zero-impact migration:

1. **Parallel Operation**: New system runs alongside existing system
2. **Data Migration**: Historical data migrated from Excel to SQL Server
3. **Validation**: Output comparison between old and new systems
4. **Gradual Cutover**: Phased migration of functionality
5. **Rollback Capability**: Ability to revert if needed

## Testing Strategy

### Unit Testing
- Individual function testing with mocks
- Database operation validation
- Configuration and error handling tests
- Performance and memory usage tests

### Property-Based Testing
- Universal correctness properties validation
- 100+ iterations per property test
- Automated shrinking for minimal failing examples
- Comprehensive input space coverage

### Integration Testing
- End-to-end workflow validation
- Multi-function orchestration testing
- External service integration testing
- Database integration with test containers

## Maintenance and Operations

### Monitoring
- Real-time performance metrics
- Error rate and success rate tracking
- Resource utilization monitoring
- Custom business metrics

### Alerting
- Automated failure notifications
- Performance degradation alerts
- Resource threshold warnings
- Business metric anomalies

### Troubleshooting
- Structured logging for easy debugging
- Correlation IDs for request tracing
- Performance profiling capabilities
- Error reproduction and analysis tools

## Next Steps

1. **Database Layer**: Implement SQL Server integration and schema
2. **Core Utilities**: Set up Azure Key Vault and Blob Storage integration
3. **Scraper Functions**: Convert existing scrapers to Azure Functions
4. **Analysis Functions**: Implement Copilot integration for sentiment analysis
5. **Orchestration**: Set up scheduling and workflow management
6. **Testing**: Implement comprehensive test suite
7. **Deployment**: Set up CI/CD pipeline and IaC templates

## Support and Documentation

For detailed implementation guidance, refer to:
- Design Document: `.kiro/specs/azure-functions-porting/design.md`
- Requirements Document: `.kiro/specs/azure-functions-porting/requirements.md`
- Task List: `.kiro/specs/azure-functions-porting/tasks.md`