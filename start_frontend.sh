#!/bin/bash
# ============================================================
# RAG Recipe App — Frontend Startup Script
# ============================================================
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd)"
cd "$FRONTEND_DIR"

echo "============================================"
echo "  RAG Recipe Frontend"
echo "  Angular 17"
echo "============================================"
echo ""
echo "Starting Angular dev server at http://localhost:4200"
echo ""
echo "Default login:"
echo "  Email:    admin@example.com"
echo "  Password: admin12345"
echo ""
echo "Press Ctrl+C to stop."
echo ""

npm start
