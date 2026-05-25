#!/bin/bash
# ============================================================
# RAG Recipe App — Backend Startup Script
# ============================================================
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
cd "$BACKEND_DIR"

echo "============================================"
echo "  RAG Recipe Backend"
echo "  FastAPI + ChromaDB + Llama 3.1 70B"
echo "============================================"

# Activate virtual environment
source venv/bin/activate

# Optional: re-run ingest if recipes.json changed
# python ingest.py

echo ""
echo "Starting FastAPI server at http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Admin Dashboard: http://localhost:8000/admin/observability"
echo ""
echo "Press Ctrl+C to stop."
echo ""

uvicorn main:app --reload --port 8000
