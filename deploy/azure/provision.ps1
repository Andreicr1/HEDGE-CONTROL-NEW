<#
.SYNOPSIS
    Idempotent Azure provisioning script for Hedge Control Platform.

.DESCRIPTION
    Creates all Azure resources needed for production in the Alcast-Hedge resource group.
    Safe to re-run — checks for existing resources before creating.

.PARAMETER PgAdminPassword
    PostgreSQL admin password. Required on first run.
#>

param(
    [string]$ResourceGroup = "Alcast-Hedge",
    [string]$Location = "eastus",
    [string]$PgLocation = "eastus2",
    [string]$AppServiceLocation = "centralus",
    [string]$AcrName = "alcasthedgeacr",
    [string]$PgServerName = "alcast-hedge-db",
    [string]$PgAdminUser = "hedgeadmin",
    [string]$PgAdminPassword,
    [string]$PgDatabase = "hedgecontrol",
    [string]$StorageName = "alcasthedgestore",
    [string]$AppPlanName = "alcast-hedge-plan",
    [string]$WebAppName = "alcast-hedge-api",
    [string]$SwaName = "alcast-hedge-web",
    [string]$OpenAiName = "AlcastLLM",
    [string]$OpenAiDeployment = "gpt-4o-mini"
)

$ErrorActionPreference = "Stop"

function Test-AzResource {
    param([string]$Type, [string]$Name)
    $result = az resource list --resource-group $ResourceGroup --resource-type $Type --query "[?name=='$Name'].id" --output tsv 2>$null
    return -not [string]::IsNullOrWhiteSpace($result)
}

Write-Host "`n=== Hedge Control Azure Provisioning ===" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroup"

# 1. ACR
Write-Host "`n[1/6] Container Registry ($AcrName)..." -ForegroundColor Yellow
$acrExists = az acr show --name $AcrName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
if ($acrExists) {
    Write-Host "  Already exists." -ForegroundColor Green
} else {
    az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --location $Location --output none
    Write-Host "  Created." -ForegroundColor Green
}

# 2. PostgreSQL Flexible Server
Write-Host "`n[2/6] PostgreSQL Flexible Server ($PgServerName)..." -ForegroundColor Yellow
$pgExists = az postgres flexible-server show --resource-group $ResourceGroup --name $PgServerName --query "state" --output tsv 2>$null
if ($pgExists) {
    Write-Host "  Already exists (state: $pgExists)." -ForegroundColor Green
} else {
    if (-not $PgAdminPassword) {
        throw "PgAdminPassword is required when creating PostgreSQL for the first time."
    }
    az postgres flexible-server create `
        --resource-group $ResourceGroup --name $PgServerName --location $PgLocation `
        --admin-user $PgAdminUser --admin-password $PgAdminPassword `
        --sku-name Standard_B1ms --tier Burstable --version 16 --storage-size 32 `
        --public-access 0.0.0.0 --yes --output none
    Write-Host "  Created." -ForegroundColor Green
}

# 2b. Database
Write-Host "  Ensuring database '$PgDatabase'..." -ForegroundColor Yellow
az postgres flexible-server db create --resource-group $ResourceGroup --server-name $PgServerName --database-name $PgDatabase --output none 2>$null
Write-Host "  Database ready." -ForegroundColor Green

# 2c. Firewall
az postgres flexible-server firewall-rule create `
    --resource-group $ResourceGroup --name $PgServerName `
    --rule-name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 --output none 2>$null

# 3. Storage Account
Write-Host "`n[3/6] Storage Account ($StorageName)..." -ForegroundColor Yellow
$storExists = az storage account show --name $StorageName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
if ($storExists) {
    Write-Host "  Already exists." -ForegroundColor Green
} else {
    az storage account create --resource-group $ResourceGroup --name $StorageName --location $Location `
        --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 --output none
    Write-Host "  Created." -ForegroundColor Green
}
$storKey = az storage account keys list --resource-group $ResourceGroup --account-name $StorageName --query "[0].value" --output tsv
az storage container create --name documents --account-name $StorageName --account-key $storKey --output none 2>$null
az storage container create --name backups --account-name $StorageName --account-key $storKey --output none 2>$null
Write-Host "  Blob containers ready." -ForegroundColor Green

# 4. App Service Plan
Write-Host "`n[4/6] App Service Plan ($AppPlanName)..." -ForegroundColor Yellow
$planExists = az appservice plan show --resource-group $ResourceGroup --name $AppPlanName --query "name" --output tsv 2>$null
if ($planExists) {
    Write-Host "  Already exists." -ForegroundColor Green
} else {
    az appservice plan create --resource-group $ResourceGroup --name $AppPlanName `
        --location $AppServiceLocation --is-linux --sku B1 --output none
    Write-Host "  Created." -ForegroundColor Green
}

# 5. Web App
Write-Host "`n[5/6] Web App ($WebAppName)..." -ForegroundColor Yellow
$webExists = az webapp show --resource-group $ResourceGroup --name $WebAppName --query "name" --output tsv 2>$null
if ($webExists) {
    Write-Host "  Already exists." -ForegroundColor Green
} else {
    az webapp create --resource-group $ResourceGroup --name $WebAppName `
        --plan $AppPlanName --container-image-name "$AcrName.azurecr.io/hedge-backend:latest" --output none
    Write-Host "  Created." -ForegroundColor Green
}

# 5b. Managed Identity + ACR Pull
Write-Host "  Configuring Managed Identity and ACR pull..." -ForegroundColor Yellow
$principalId = az webapp identity assign --resource-group $ResourceGroup --name $WebAppName --query "principalId" --output tsv
$acrId = az acr show --name $AcrName --resource-group $ResourceGroup --query "id" --output tsv
az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal `
    --role AcrPull --scope $acrId --output none 2>$null
az resource update --ids "/subscriptions/$(az account show --query 'id' --output tsv)/resourceGroups/$ResourceGroup/providers/Microsoft.Web/sites/$WebAppName/config/web" `
    --set properties.acrUseManagedIdentityCreds=true --output none

# 5c. HTTPS + TLS
az webapp update --resource-group $ResourceGroup --name $WebAppName --https-only true --output none
az webapp config set --resource-group $ResourceGroup --name $WebAppName --min-tls-version 1.2 --output none

# 5d. Environment variables
$pgFqdn = az postgres flexible-server show --resource-group $ResourceGroup --name $PgServerName --query "fullyQualifiedDomainName" --output tsv
$openAiKey = az cognitiveservices account keys list --name $OpenAiName --resource-group $ResourceGroup --query "key1" --output tsv
$openAiEndpoint = az cognitiveservices account show --name $OpenAiName --resource-group $ResourceGroup --query "properties.endpoint" --output tsv
$swaHostname = az staticwebapp show --name $SwaName --resource-group $ResourceGroup --query "defaultHostname" --output tsv

$dbUrl = "postgresql+psycopg://${PgAdminUser}:${PgAdminPassword}@${pgFqdn}:5432/${PgDatabase}?sslmode=require"

az webapp config appsettings set --resource-group $ResourceGroup --name $WebAppName --settings `
    "DATABASE_URL=$dbUrl" `
    "AZURE_OPENAI_ENDPOINT=$openAiEndpoint" `
    "AZURE_OPENAI_API_KEY=$openAiKey" `
    "AZURE_OPENAI_DEPLOYMENT=$OpenAiDeployment" `
    "CORS_ALLOW_ORIGINS=https://$swaHostname" `
    "APP_VERSION=1.0.0" `
    "WEBSITES_PORT=8000" `
    "SCM_DO_BUILD_DURING_DEPLOYMENT=false" --output none

Write-Host "  App Service configured." -ForegroundColor Green

# 6. Static Web App
Write-Host "`n[6/6] Static Web App ($SwaName)..." -ForegroundColor Yellow
$swaExists = az staticwebapp show --name $SwaName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
if ($swaExists) {
    Write-Host "  Already exists (https://$swaHostname)." -ForegroundColor Green
} else {
    az staticwebapp create --resource-group $ResourceGroup --name $SwaName --location eastus2 --sku Free --output none
    Write-Host "  Created." -ForegroundColor Green
}

Write-Host "`n=== Provisioning Complete ===" -ForegroundColor Cyan
Write-Host "Frontend: https://$swaHostname"
Write-Host "Backend:  https://$WebAppName.azurewebsites.net"
Write-Host "Health:   https://$WebAppName.azurewebsites.net/health"
Write-Host ""
