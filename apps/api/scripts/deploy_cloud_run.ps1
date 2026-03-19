param(
    [string]$ProjectId,
    [string]$Region = "us-central1",
    [string]$Service = "alloha-api",
    [string]$Repository = "cloud-run",
    [string]$ImageTag = "latest",
    [string]$EnvFile = "cloudrun.env.yaml"
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    throw "Informe -ProjectId."
}

$apiRoot = Split-Path -Parent $PSScriptRoot
$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/${Service}:${ImageTag}"

Write-Host "Projeto: $ProjectId"
Write-Host "Região: $Region"
Write-Host "Serviço: $Service"
Write-Host "Imagem: $image"

$repoExists = $false
try {
    gcloud artifacts repositories describe $Repository --location=$Region --project=$ProjectId | Out-Null
    $repoExists = $true
} catch {
    $repoExists = $false
}

if (-not $repoExists) {
    gcloud artifacts repositories create $Repository `
        --repository-format=docker `
        --location=$Region `
        --project=$ProjectId `
        --description="Alloha Cloud Run images"
}

Push-Location $apiRoot
try {
    gcloud builds submit . `
        --project=$ProjectId `
        --config cloudbuild.cloudrun.yaml `
        --substitutions "_IMAGE=$image"

    $deployArgs = @(
        "run", "deploy", $Service,
        "--project", $ProjectId,
        "--region", $Region,
        "--platform", "managed",
        "--image", $image,
        "--allow-unauthenticated",
        "--port", "8080",
        "--cpu", "0.5",
        "--memory", "512Mi",
        "--concurrency", "20",
        "--timeout", "30",
        "--min-instances", "0",
        "--max-instances", "2"
    )

    if (Test-Path $EnvFile) {
        $deployArgs += @("--env-vars-file", $EnvFile)
    } else {
        Write-Warning "Arquivo de ambiente não encontrado: $EnvFile. O deploy seguirá sem --env-vars-file."
    }

    gcloud @deployArgs
} finally {
    Pop-Location
}
