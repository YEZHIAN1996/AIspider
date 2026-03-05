.PHONY: dev prod build logs clean migrate frontend

# 开发环境
dev:
	docker compose up -d

# 生产环境
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 构建所有镜像
build:
	docker compose build

# 查看日志
logs:
	docker compose logs -f --tail=100

# 数据库迁移
migrate:
	docker compose exec api alembic upgrade head

# 前端开发
frontend:
	cd frontend && npm run dev

# 前端构建
frontend-build:
	cd frontend && npm run build

# 清理
clean:
	docker compose down -v

# 热更新 spider worker
update-spider:
	git pull origin main
	docker compose up -d --no-deps --build spider-worker
