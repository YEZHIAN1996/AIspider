.PHONY: dev prod build logs clean migrate frontend test stop restart help

# 开发环境
dev:
	docker compose up -d

# 生产环境
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 构建所有镜像
build:
	docker compose build

# 停止所有服务
stop:
	docker compose down

# 重启所有服务
restart:
	docker compose restart

# 查看日志
logs:
	docker compose logs -f --tail=100

# 数据库迁移
migrate:
	docker compose exec api alembic upgrade head

# 运行测试
test:
	pytest --cov=src --cov-report=term-missing

# 前端开发
frontend:
	cd frontend && npm run dev

# 前端构建
frontend-build:
	cd frontend && npm run build

# 清理容器和数据卷
clean:
	docker compose down -v

# 热更新 spider worker
update-spider:
	git pull origin main
	docker compose up -d --no-deps --build spider-worker

# 帮助信息
help:
	@echo "AIspider Makefile 命令:"
	@echo "  make dev              - 启动开发环境"
	@echo "  make prod             - 启动生产环境"
	@echo "  make stop             - 停止所有服务"
	@echo "  make restart          - 重启所有服务"
	@echo "  make logs             - 查看日志"
	@echo "  make test             - 运行测试"
	@echo "  make migrate          - 数据库迁移"
	@echo "  make clean            - 清理容器和数据卷"
	@echo "  make build            - 构建所有镜像"
	@echo "  make frontend         - 启动前端开发服务器"
	@echo "  make update-spider    - 热更新爬虫 Worker"
