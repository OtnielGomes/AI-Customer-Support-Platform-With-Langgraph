# Bootstrap local development environment
$ErrorActionPreference = "Stop"

Write-Host "Installing dependencies with uv..."
uv sync

Write-Host "Starting Docker services..."
docker compose up -d db redis

Write-Host "Waiting for database..."
Start-Sleep -Seconds 8

Write-Host "Running migrations..."
uv run alembic upgrade head

Write-Host "Seeding demo data..."
uv run python scripts/seed_demo.py

Write-Host "Ingesting knowledge base..."
uv run python scripts/ingest_kb.py

Write-Host "Bootstrap complete. Run: uv run fastapi dev"
