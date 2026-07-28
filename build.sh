#!/bin/bash
set -e

echo "=== Installing backend dependencies ==="
cd backend
pip install -r requirements.txt
cd ..

echo "=== Building frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Copying frontend dist to backend/static ==="
rm -rf backend/static
cp -r frontend/dist backend/static

echo "=== Build complete ==="
