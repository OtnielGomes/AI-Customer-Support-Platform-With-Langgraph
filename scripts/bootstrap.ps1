# Bootstrap local development environment (Windows-friendly)
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    Write-Host ""
    Write-Host "==> $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Label (exit code $LASTEXITCODE)"
    }
}

# Avoid hardlink failures on Windows (OneDrive, cloud-backed profile folders, os error 396).
$env:UV_LINK_MODE = "copy"

# Optional: keep uv cache on local disk if not already configured.
if (-not $env:UV_CACHE_DIR) {
    $defaultCache = "C:\uv-cache"
    if (-not (Test-Path $defaultCache)) {
        New-Item -ItemType Directory -Force -Path $defaultCache | Out-Null
    }
    $env:UV_CACHE_DIR = $defaultCache
    Write-Host "Using UV_CACHE_DIR=$defaultCache"
}

Write-Host "UV_LINK_MODE=copy (required on many Windows setups)"

Invoke-Step "Installing dependencies with uv" {
    uv sync --link-mode=copy
}

Invoke-Step "Verifying Python environment" {
    uv run python -c "import jsonpatch; import langchain_core; print('environment ok')"
}

Invoke-Step "Starting Docker services (db, redis)" {
    docker compose up -d db redis
}

Write-Host ""
Write-Host "Waiting for database..."
Start-Sleep -Seconds 8

Invoke-Step "Running migrations" {
    uv run alembic upgrade head
}

Invoke-Step "Seeding demo data" {
    uv run python scripts/seed_demo.py
}

Invoke-Step "Ingesting knowledge base" {
    uv run python scripts/ingest_kb.py
}

Write-Host ""
Write-Host "Bootstrap complete. Run: uv run fastapi dev"
