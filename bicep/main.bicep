// Non-authoritative legacy infrastructure draft.
// Docker + GitLab CI is the supported delivery path for this repository.
// This file remains only as an exploratory reference and is not production-ready.
param location string = resourceGroup().location
param appName string = 'eduboost-sa'

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: appName
  location: location
  properties: {
    configuration: {
      ingress: { external: true, targetPort: 8000 }
    }
    template: {
      containers: [{
        name: 'api'
        image: 'eduboost/api:latest'
        resources: { cpu: '0.5', memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
}
