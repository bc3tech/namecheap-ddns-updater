targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

param resourceGroupName string = ''
param containerAppsEnvironmentName string = ''
param containerRegistryName string = ''
param logAnalyticsWorkspaceName string = ''
param applicationInsightsName string = ''
param containerImage string

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = {
  'azd-env-name': environmentName
}

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  scope: rg
  name: 'resources'
  params: {
    location: location
    environmentName: environmentName
    containerAppsEnvironmentName: !empty(containerAppsEnvironmentName) ? containerAppsEnvironmentName : '${abbrs.containerAppsEnvironments}${resourceToken}'
    logAnalyticsWorkspaceName: !empty(logAnalyticsWorkspaceName) ? logAnalyticsWorkspaceName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    tags: tags
  }
}

module service 'service.bicep' = {
  scope: rg
  name: 'service'
  params: {
    location: location
    environmentName: environmentName
    containerAppsEnvironmentId: resources.outputs.containerAppsEnvironmentId
    containerImage: containerImage
    applicationInsightsConnectionString: resources.outputs.applicationInsightsConnectionString
    tags: tags
  }
}

output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = ''
output AZURE_CONTAINER_REGISTRY_NAME string = ''
output APPLICATION_INSIGHTS_CONNECTION_STRING string = resources.outputs.applicationInsightsConnectionString
output APPLICATION_INSIGHTS_INSTRUMENTATION_KEY string = resources.outputs.applicationInsightsInstrumentationKey
output SERVICE_NAMECHEAP_DDNS_UPDATER_ENDPOINT_URL string = 'https://${service.outputs.containerAppFqdn}/'
output SERVICE_NAMECHEAP_DDNS_UPDATER_NAME string = service.outputs.containerAppName
