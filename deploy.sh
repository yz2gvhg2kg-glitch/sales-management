#!/bin/bash
# Quick deploy script for Sales Management System
set -e

echo "=== 销售管理系统部署 ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  请修改 .env 中的密钥和密码!"
fi

# Build and start
echo "Building and starting services..."
docker compose up -d --build

# Wait for postgres to be ready
echo "Waiting for database..."
sleep 5

# Init database
echo "Initializing database..."
docker compose exec backend python init_db.py

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://localhost"
echo "默认管理员: admin / admin123"
echo "⚠️  请立即修改默认密码!"
