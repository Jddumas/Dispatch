#!/bin/sh
# Idempotent seed + start for Render and Docker deployments.
python init_db.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
