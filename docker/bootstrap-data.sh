#!/bin/sh
# One-off job: seed NexaCommerce demo data and ingest the knowledge base.
# Requires DATABASE_URL, OPENAI_API_KEY (ingest), and optional REDIS_URL.
set -eu
cd /app
python scripts/seed_demo.py
python scripts/ingest_kb.py
