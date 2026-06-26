.PHONY: install dev run-api test lint clean

# 安装依赖
install:
	pip install -e .

# 安装开发依赖
dev:
	pip install -e ".[dev]"

# 启动 API 服务
run-api:
	uvicorn apps.api.app.main:app --reload --port 8000

# 运行测试
test:
	pytest

# 代码检查
lint:
	ruff check .
	ruff format .

# 清理缓存
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .ruff_cache
