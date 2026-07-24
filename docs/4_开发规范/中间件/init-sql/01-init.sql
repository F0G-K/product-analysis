-- ============================================================
-- PostgreSQL 初始化脚本
-- 数据库: product_analysis
-- 创建: 扩展 + 基础 schema
-- ============================================================

-- 启用 UUID 生成
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 启用全文搜索 (可选, 用于混合检索)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建应用 schema
CREATE SCHEMA IF NOT EXISTS pa;

-- 设置默认搜索路径
ALTER DATABASE product_analysis SET search_path TO pa, public;

SELECT 'PostgreSQL initialized successfully.' AS status;
