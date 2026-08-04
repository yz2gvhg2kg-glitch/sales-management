# 销售管理系统 v2.0 — 代码优化总结

## 🔴 安全修复

| 问题 | 修复 |
|------|------|
| ❌ `SECRET_KEY` 硬编码 | ✅ `secrets.token_urlsafe(32)` 自动生成，生产环境必改 |
| ❌ 无频率限制，登录可被暴力破解 | ✅ 登录限流 5次/分钟/IP；通用限流 60次/分钟 |
| ❌ 无 token 刷新机制 | ✅ JWT access + refresh token，refresh 按 7天过期 |
| ❌ 管理员密码 `admin123` 全局可见 | ✅ 从 SECRET_KEY 前8位派生或因环境变量 |
| ❌ `/api/init` 生产环境开放 | ✅ 显式说明 only for initialization |
| ❌ 无请求日志 | ✅ 结构化日志中间件，记录 method/path/status/latency/IP |

## ⚡ 性能优化

| 问题 | 修复 |
|------|------|
| ❌ 每条查询独立 count + data，N+1 问题严重 | ✅ 合并查询，`make_paginated_response` 统一分页 |
| ❌ 没有连接池调优 | ✅ pool_size=10, max_overflow=20, pool_recycle=3600s, pool_pre_ping |
| ❌ `expire_on_commit=True` 导致重复刷新 | ✅ 设为 False |
| ❌ 无数据库索引 | ✅ 关键字段全部加 Index（复合索引覆盖常用查询） |
| ❌ openpyxl 每次 import | ✅ 模块顶部导入 |
| ❌ 序列化散落在各处 | ✅ `utils/response.py` 统一序列化函数 |
| ❌ 客户查询无 eager loading | ✅ `lazy="selectin"` 避免 N+1 |
| ❌ Dockerfile 无 layer cache | ✅ `npm ci --production=false`, 分离 copy 层 |

## 🏗️ 代码架构改进

| 问题 | 修复 |
|------|------|
| ❌ 模型分别写 4 个文件 | ✅ 统一 `models/models.py`，BaseModel 抽象基类 |
| ❌ `main.py` 塞 `/api/init` 逻辑 | ✅ 抽到 `init_db.py`，main.py 只挂路由 |
| ❌ 大量重复的查询构建模式 | ✅ `utils/repository.py` 通用 Repository CRUD |
| ❌ 无输入校验 | ✅ Pydantic `@field_validator` 校验用户名/密码/手机号 |
| ❌ 无统一错误处理 | ✅ `global_exception_handler` + 生产/开发模式区分 |
| ❌ statistics/dashboard 代码重复 | ✅ 合并为一个文件，共享 helper 函数 |
| ❌ 数字转换无容错 | ✅ `safe_int/safe_float/safe_str` 防崩 |

## 🆕 新增功能

| 功能 | 说明 |
|------|------|
| 📧 用户邮箱字段 | `User.email` 字段 |
| 🖼 头像 URL | `User.avatar_url` |
| 📦 产品库存 | `Product.stock`、`Product.image_url` |
| 💰 优惠金额 | `Order.discount_amount`、`Order.actual_amount` |
| 💳 支付状态 | `PaymentStatus` 枚举（unpaid/partial/paid/refunded） |
| 📮 渠道字段 | `Order.channel`、完整发货字段 |
| 📈 趋势图 | `GET /statistics/trend` 日维度时间序列 |
| 🔐 修改密码 | `POST /auth/change-password` |
| 🔄 刷新 token | `POST /auth/refresh` |
| 👤 用户下拉列表 | `GET /users/simple` 简化列表 |
| 🏷 产品分类列表 | `GET /products/categories` |
| ✏ 客户编辑 | `PUT /customers/{id}` 更新客户信息 |

## 📊 数据模型优化

- 所有表新增 `Index` 复合索引，覆盖最常用的查询条件
- `AfterSales` 新增 `exchange_product`、`handler_id`、`remark`
- `Shipment` 新增 `delivery_date`、`shipping_fee`、`remark`
- `Customer` 新增 `lost_date`、`lost_reason`
- `User` 新增 `last_login_at`、`last_login_ip`

## 🔧 DevOps 改进

- Dockerfile: `node:20-alpine` → `python:3.12-slim`，multi-stage 构建
- Redis: 启用 AOF 持久化 + 256MB 内存限制 + LRU 淘汰
- PostgreSQL: 升级到 16-alpine，start_period 健康检查
- gunicorn: 添加 `--timeout 120 --max-requests 1000 --max-requests-jitter 50`
- 新增 `.env.example` 清晰标注所有配置项
- 后端容器也加 healthcheck
