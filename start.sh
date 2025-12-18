#!/bin/bash
echo "Starting Mine-AI Server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
