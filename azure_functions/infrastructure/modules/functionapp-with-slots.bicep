// Function App with Deployment Slots Module
// Supports blue-green deployment strategy

@description('Function App name')
param functionAppName string

@description('App Service Plan ID')
param appServicePlanId string

@description('Location for resources')
param location string = resourceGroup().location

@description('Storage account connection string')
param storageConnectionString string

@description('Application Insights connection string')
param applicationInsightsConnectionString string

@description('Application Insights instrumentation key')
param applicationInsightsInstrumentationKey string

@description('SQL Server connection string')
param sqlConnectionString string

@description('Azure Key Vault URL')
param keyVaultUrl string

@description('Blob storage connection string')
param blobStorageConnectionString string

@description('Environment name')
param environment string

@description('Enable deployment slots')
param enableDeploymentSlots bool = true

// Common app settings for both production and staging slots
var commonAppSettings = [
  {
    name: 'AzureWebJobsStorage'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTSHARE'
    value: toLower(functionAppName)
  }
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
  {
    name: 'WEBSITE_NODE_DEFAULT_VERSION'
    value: '~18'
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: 'python'
  }
  {
    name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
    value: applicationInsightsInstrumentationKey
  }
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: applicationInsightsConnectionString
  }
  {
    name: 'SQL_SERVER_CONNECTION_STRING'
    value: sqlConnectionString
  }
  {
    name: 'AZURE_KEY_VAULT_URL'
    value: keyVaultUrl
  }
  {
    name: 'BLOB_STORAGE_CONNECTION_STRING'
    value: blobStorageConnectionString
  }
  {
    name: 'ENVIRONMENT'
    value: environment
  }
  {
    name: 'WEBSITE_RUN_FROM_PACKAGE'
    value: '1'
  }
  {
    name: 'WEBSITE_ENABLE_SYNC_UPDATE_SITE'
    value: 'true'
  }
  {
    name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
    value: 'true'
  }
]

// Production Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    enabled: true
    hostNameSslStates: [
      {
        name: '${functionAppName}.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Standard'
      }
      {
        name: '${functionAppName}.scm.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Repository'
      }
    ]
    serverFarmId: appServicePlanId
    reserved: false
    isXenon: false
    hyperV: false
    vnetRouteAllEnabled: false
    vnetImagePullEnabled: false
    vnetContentShareEnabled: false
    siteConfig: {
      numberOfWorkers: 1
      acrUseManagedIdentityCreds: false
      alwaysOn: false
      http20Enabled: false
      functionAppScaleLimit: 200
      minimumElasticInstanceCount: 0
      pythonVersion: '3.11'
      appSettings: commonAppSettings
      use32BitWorkerProcess: false
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      cors: {
        allowedOrigins: [
          'https://portal.azure.com'
        ]
        supportCredentials: false
      }
    }
    scmSiteAlsoStopped: false
    clientAffinityEnabled: false
    clientCertEnabled: false
    clientCertMode: 'Required'
    hostNamesDisabled: false
    containerSize: 1536
    dailyMemoryTimeQuota: 0
    httpsOnly: true
    redundancyMode: 'None'
    storageAccountRequired: false
    keyVaultReferenceIdentity: 'SystemAssigned'
  }
}

// Staging Deployment Slot
resource stagingSlot 'Microsoft.Web/sites/slots@2023-01-01' = if (enableDeploymentSlots) {
  parent: functionApp
  name: 'staging'
  location: location
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    enabled: true
    serverFarmId: appServicePlanId
    reserved: false
    isXenon: false
    hyperV: false
    siteConfig: {
      numberOfWorkers: 1
      acrUseManagedIdentityCreds: false
      alwaysOn: false
      http20Enabled: false
      functionAppScaleLimit: 200
      minimumElasticInstanceCount: 0
      pythonVersion: '3.11'
      appSettings: union(commonAppSettings, [
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower('${functionAppName}-staging')
        }
        {
          name: 'DEPLOYMENT_SLOT'
          value: 'staging'
        }
        {
          name: 'WEBSITE_SLOT_NAME'
          value: 'staging'
        }
      ])
      use32BitWorkerProcess: false
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
    }
    scmSiteAlsoStopped: false
    clientAffinityEnabled: false
    clientCertEnabled: false
    clientCertMode: 'Required'
    hostNamesDisabled: false
    containerSize: 1536
    dailyMemoryTimeQuota: 0
    httpsOnly: true
    redundancyMode: 'None'
    storageAccountRequired: false
    keyVaultReferenceIdentity: 'SystemAssigned'
  }
}

// Blue-Green Deployment Slot (for advanced scenarios)
resource blueGreenSlot 'Microsoft.Web/sites/slots@2023-01-01' = if (enableDeploymentSlots) {
  parent: functionApp
  name: 'blue-green'
  location: location
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    enabled: true
    serverFarmId: appServicePlanId
    reserved: false
    isXenon: false
    hyperV: false
    siteConfig: {
      numberOfWorkers: 1
      acrUseManagedIdentityCreds: false
      alwaysOn: false
      http20Enabled: false
      functionAppScaleLimit: 200
      minimumElasticInstanceCount: 0
      pythonVersion: '3.11'
      appSettings: union(commonAppSettings, [
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower('${functionAppName}-bluegreen')
        }
        {
          name: 'DEPLOYMENT_SLOT'
          value: 'blue-green'
        }
        {
          name: 'WEBSITE_SLOT_NAME'
          value: 'blue-green'
        }
      ])
      use32BitWorkerProcess: false
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
    }
    scmSiteAlsoStopped: false
    clientAffinityEnabled: false
    clientCertEnabled: false
    clientCertMode: 'Required'
    hostNamesDisabled: false
    containerSize: 1536
    dailyMemoryTimeQuota: 0
    httpsOnly: true
    redundancyMode: 'None'
    storageAccountRequired: false
    keyVaultReferenceIdentity: 'SystemAssigned'
  }
}

// Outputs
output functionAppName string = functionApp.name
output functionAppId string = functionApp.id
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output functionAppPrincipalId string = functionApp.identity.principalId
output stagingSlotName string = enableDeploymentSlots ? stagingSlot.name : ''
output stagingSlotUrl string = enableDeploymentSlots ? 'https://${functionApp.name}-staging.azurewebsites.net' : ''
output stagingSlotPrincipalId string = enableDeploymentSlots ? stagingSlot.identity.principalId : ''
output blueGreenSlotName string = enableDeploymentSlots ? blueGreenSlot.name : ''
output blueGreenSlotUrl string = enableDeploymentSlots ? 'https://${functionApp.name}-blue-green.azurewebsites.net' : ''
output blueGreenSlotPrincipalId string = enableDeploymentSlots ? blueGreenSlot.identity.principalId : ''